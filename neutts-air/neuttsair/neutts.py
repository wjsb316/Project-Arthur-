from typing import Generator
from pathlib import Path
import librosa
import numpy as np
import torch
import re
import platform
import glob
import warnings
import os
import gc

from neucodec import NeuCodec, DistillNeuCodec
from phonemizer.backend import EspeakBackend
from transformers import AutoTokenizer, AutoModelForCausalLM, TextIteratorStreamer
from threading import Thread


def _configure_espeak_library():
    """Auto-detect and configure espeak library on macOS."""
    if platform.system() != "Darwin":
        return  # Only needed on macOS

    # Common Homebrew installation paths
    search_paths = [
        "/opt/homebrew/Cellar/espeak/*/lib/libespeak.*.dylib",  # Apple Silicon
        "/usr/local/Cellar/espeak/*/lib/libespeak.*.dylib",     # Intel
    ]

    for pattern in search_paths:
        matches = glob.glob(pattern)
        if matches:
            try:
                from phonemizer.backend.espeak.wrapper import EspeakWrapper

                EspeakWrapper.set_library(matches[0])
                return
            except Exception:
                # If this fails, phonemizer will try its default detection
                pass


# Call before using phonemizer
_configure_espeak_library()


# def _linear_overlap_add(frames: list[np.ndarray], stride: int) -> np.ndarray:
#     # original impl --> https://github.com/facebookresearch/encodec/blob/main/encodec/utils.py
#     assert len(frames)
#     dtype = frames[0].dtype
#     shape = frames[0].shape[:-1]

#     total_size = 0
#     for i, frame in enumerate(frames):
#         frame_end = stride * i + frame.shape[-1]
#         total_size = max(total_size, frame_end)

#     sum_weight = np.zeros(total_size, dtype=dtype)
#     out = np.zeros(*shape, total_size, dtype=dtype)

#     offset: int = 0
#     for frame in frames:
#         frame_length = frame.shape[-1]
#         t = np.linspace(0, 1, frame_length + 2, dtype=dtype)[1:-1]
#         weight = np.abs(0.5 - (t - 0.5))

#         out[..., offset : offset + frame_length] += weight * frame
#         sum_weight[offset : offset + frame_length] += weight
#         offset += stride
#     assert sum_weight.min() > 0
#     return out / sum_weight

class IncrementalOverlapAdd:
    """
    Streaming-friendly Overlap-Add.
    Replaces the O(N^2) memory leak with an O(1) shifting buffer.
    """
    def __init__(self, stride: int):
        self.stride = stride
        self.buffer_out = None
        self.buffer_weight = None

    def process_frame(self, frame: np.ndarray, is_last: bool = False) -> np.ndarray:
        # Handle flush command if the stream is empty but we have leftovers
        if frame.size == 0:
            if is_last and self.buffer_out is not None:
                res = np.zeros_like(self.buffer_out)
                valid = self.buffer_weight > 0
                res[..., valid] = self.buffer_out[..., valid] / self.buffer_weight[valid]
                self.buffer_out = None
                return res
            return np.array([], dtype=np.float32)

        frame_length = frame.shape[-1]
        prefix_shape = frame.shape[:-1]
        dtype = frame.dtype

        # Initialize buffers on first frame
        if self.buffer_out is None:
            self.buffer_out = np.zeros((*prefix_shape, 0), dtype=dtype)
            self.buffer_weight = np.zeros(0, dtype=dtype)

        # Apply the exact same triangle weight as your original function
        t = np.linspace(0, 1, frame_length + 2, dtype=dtype)[1:-1]
        weight = np.abs(0.5 - (t - 0.5))
        weighted_frame = frame * weight

        # Pad buffers to accommodate the new frame length if needed
        if self.buffer_out.shape[-1] < frame_length:
            pad_len = frame_length - self.buffer_out.shape[-1]
            pad_width_out = [(0, 0)] * len(prefix_shape) + [(0, pad_len)]
            self.buffer_out = np.pad(self.buffer_out, pad_width_out)
            self.buffer_weight = np.pad(self.buffer_weight, (0, pad_len))

        # Add the weighted frame to the running buffers
        self.buffer_out[..., :frame_length] += weighted_frame
        self.buffer_weight[:frame_length] += weight

        # If it's not the last frame, we can only safely yield the 'stride' amount 
        # (because the right tail will overlap with the next future frame)
        samples_to_yield = self.buffer_out.shape[-1] if is_last else self.stride

        # Extract the completed, overlap-added audio
        finalized_out = self.buffer_out[..., :samples_to_yield]
        finalized_weight = self.buffer_weight[:samples_to_yield]

        res = np.zeros_like(finalized_out)
        valid_mask = finalized_weight > 0
        res[..., valid_mask] = finalized_out[..., valid_mask] / finalized_weight[valid_mask]

        # Shift the buffers left, permanently dropping the yielded audio from memory
        self.buffer_out = self.buffer_out[..., samples_to_yield:]
        self.buffer_weight = self.buffer_weight[samples_to_yield:]

        return res


class NeuTTSAir:

    def __init__(
        self,
        backbone_repo="neuphonic/neutts-air",
        backbone_device=None,
        codec_repo="neuphonic/neucodec",
        codec_device=None,
    ):

        # Auto-detect device if not specified
        if backbone_device is None:
            backbone_device = "gpu" if torch.cuda.is_available() else "cpu"
        
        if codec_device is None:
            if codec_repo == "neuphonic/neucodec-onnx-decoder" or codec_repo.endswith(".onnx"):
                codec_device = "cpu"
            else:
                codec_device = "cuda" if torch.cuda.is_available() else "cpu"

        # Consts
        self.sample_rate = 24_000
        self.max_context = 2048
        self.hop_length = 480
        self.streaming_overlap_frames = 3
        self.streaming_frames_per_chunk = 50
        self.streaming_lookforward = 100
        self.streaming_lookback = 75
        self.streaming_stride_samples = self.streaming_frames_per_chunk * self.hop_length

        # ggml & onnx flags
        self._is_quantized_model = False
        self._is_onnx_codec = False

        # HF tokenizer
        self.tokenizer = None

        # Load phonemizer
        print("Loading phonemizer...")
        self.phonemizer = EspeakBackend(
            language="en-us", preserve_punctuation=True, with_stress=True
        )

        # Load models
        self._load_backbone(backbone_repo, backbone_device)
        self._load_codec(codec_repo, codec_device)

        # Load watermarker (optional)
        try:
            import perth
            self.watermarker = perth.PerthImplicitWatermarker()
        except (ImportError, AttributeError) as e:
            warnings.warn(
                f"Perth watermarking unavailable: {e}. "
                "Audio will not be watermarked. "
                "Install with: pip install perth>=0.2.0"
            )
            self.watermarker = None

    def _load_backbone(self, backbone_repo, backbone_device):
        print(f"Loading backbone from: {backbone_repo} on {backbone_device} ...")

        is_gpu = str(backbone_device).lower() in ["gpu", "cuda"] or str(backbone_device).startswith("cuda:")

        if backbone_repo.endswith("gguf"):
            try:
                from llama_cpp import Llama
            except ImportError as e:
                raise ImportError(
                    "Failed to import `llama_cpp`. Please install it with: pip install llama-cpp-python"
                ) from e

            if os.path.isfile(backbone_repo):
                # Ensure correct chat format is set if available
                self.backbone = Llama(
                    model_path=backbone_repo,
                    verbose=True,
                    n_gpu_layers=-1 if is_gpu else 0,
                    n_ctx=self.max_context,
                    # mlock=True,
                    flash_attn=True if is_gpu else False,
                    chat_format="chatml", # Often GGUF models default to this or similar
                    # use_mmap=False,  # <--- SET THIS TO FALSE
                    # use_mlock=True  # <--- OPTIONAL: Keeps the model from being swapped out
                    n_threads=4
                )
            else:
                self.backbone = Llama.from_pretrained(
                    repo_id=backbone_repo,
                    filename="*.gguf",
                    verbose=False,
                    n_gpu_layers=-1 if is_gpu else 0,
                    n_ctx=self.max_context,
                    # mlock=True,
                    flash_attn=True if is_gpu else False,
                    chat_format="chatml",
                    # use_mmap=False,  # <--- SET THIS TO FALSE
                    # use_mlock=True  # <--- OPTIONAL: Keeps the model from being swapped out
                    n_threads=4
                )

            self._is_quantized_model = True

        else:
            if backbone_device == "gpu":
                backbone_device = "cuda"
            
            self.tokenizer = AutoTokenizer.from_pretrained(backbone_repo)
            self.backbone = AutoModelForCausalLM.from_pretrained(backbone_repo).to(
                torch.device(backbone_device)
            )

    def _load_codec(self, codec_repo, codec_device):

        print(f"Loading codec from: {codec_repo} on {codec_device} ...")

        # Map "gpu" to "cuda" for torch compatibility
        if codec_device == "gpu":
            codec_device = "cuda"

        # 1) Local ONNX path (offline, recommended for embedded)
        if codec_repo.endswith(".onnx") and os.path.isfile(codec_repo):
            try:
                from neucodec import NeuCodecOnnxDecoder
            except ImportError as e:
                raise ImportError(
                    "Failed to import NeuCodecOnnxDecoder. "
                    "Make sure `neucodec` and `onnxruntime` are installed."
                ) from e

            self.codec = NeuCodecOnnxDecoder(codec_repo)
            self._is_onnx_codec = True

        # 2) Original HF-based behavior (use only if you really want remote download)
        match codec_repo:
            case "neuphonic/neucodec":
                self.codec = NeuCodec.from_pretrained(codec_repo)
                self.codec.eval().to(codec_device)
            case "neuphonic/distill-neucodec":
                self.codec = DistillNeuCodec.from_pretrained(codec_repo)
                self.codec.eval().to(codec_device)
            case "neuphonic/neucodec-onnx-decoder":

                if codec_device != "cpu":
                    raise ValueError("Onnx decoder only currently runs on CPU.")

                try:
                    from neucodec import NeuCodecOnnxDecoder
                except ImportError as e:
                    raise ImportError(
                        "Failed to import the onnx decoder."
                        " Ensure you have onnxruntime installed as well as neucodec >= 0.0.4."
                    ) from e

                self.codec = NeuCodecOnnxDecoder.from_pretrained(codec_repo)
                self._is_onnx_codec = True

            case _:
                raise ValueError(
                    "Invalid codec repo! Must be one of:"
                    " 'neuphonic/neucodec', 'neuphonic/distill-neucodec',"
                    " 'neuphonic/neucodec-onnx-decoder'."
                )

    def infer(self, text: str, ref_codes: np.ndarray | torch.Tensor, ref_text: str) -> np.ndarray:
        """
        Perform inference to generate speech from text using the TTS model and reference audio.

        Args:
            text (str): Input text to be converted to speech.
            ref_codes (np.ndarray | torch.tensor): Encoded reference.
            ref_text (str): Reference text for reference audio. Defaults to None.
        Returns:
            np.ndarray: Generated speech waveform.
        """

        if isinstance(ref_codes, torch.Tensor):
            ref_codes = ref_codes.tolist()
        elif isinstance(ref_codes, np.ndarray):
            ref_codes = ref_codes.tolist()

        # Generate tokens
        if self._is_quantized_model:
            output_str = self._infer_ggml(ref_codes, ref_text, text)
        else:
            prompt_ids = self._apply_chat_template(ref_codes, ref_text, text)
            output_str = self._infer_torch(prompt_ids)

        # Decode
        wav = self._decode(output_str)
        watermarked_wav = (
            wav
            if self.watermarker is None
            else self.watermarker.apply_watermark(wav, sample_rate=24_000)
        )

        return watermarked_wav

    def infer_stream(self, text: str, ref_codes: np.ndarray | torch.Tensor, ref_text: str) -> Generator[np.ndarray, None, None]:
        """
        Perform streaming inference to generate speech from text using the TTS model and reference audio.

        Args:
            text (str): Input text to be converted to speech.
            ref_codes (np.ndarray | torch.tensor): Encoded reference.
            ref_text (str): Reference text for reference audio. Defaults to None.
        Yields:
            np.ndarray: Generated speech waveform.
        """

        if isinstance(ref_codes, torch.Tensor):
            ref_codes = ref_codes.tolist()
        elif isinstance(ref_codes, np.ndarray):
            ref_codes = ref_codes.tolist()

        if self._is_quantized_model:
            return self._infer_stream_ggml(ref_codes, ref_text, text)

        else:
            raise NotImplementedError("Streaming is not implemented for the torch backend!")

    def encode_reference(self, ref_audio_path: str | Path):
        wav, _ = librosa.load(ref_audio_path, sr=16000, mono=True)
        wav_tensor = torch.from_numpy(wav).float().unsqueeze(0).unsqueeze(0)  # [1, 1, T]
        with torch.no_grad():
            ref_codes = self.codec.encode_code(audio_or_path=wav_tensor).squeeze(0).squeeze(0)
        return ref_codes

    def _decode(self, codes: str):

        # Extract speech token IDs using regex
        speech_ids = [int(num) for num in re.findall(r"<\|speech_(\d+)\|>", codes)]

        if len(speech_ids) > 0:

            # Onnx decode
            if self._is_onnx_codec:
                codes = np.array(speech_ids, dtype=np.int32)[np.newaxis, np.newaxis, :]
                recon = self.codec.decode_code(codes)

            # Torch decode
            else:
                with torch.no_grad():
                    codes = torch.tensor(speech_ids, dtype=torch.long)[None, None, :].to(
                        self.codec.device
                    )
                    recon = self.codec.decode_code(codes).cpu().numpy()

            return recon[0, 0, :]
        else:
            # Fallback for silent chunks if no speech tokens found (yet)
            # Or raise error if strict validation is desired
            # But during streaming, sometimes chunks might be pure text or silence tokens?
            # Actually, `codes` comes from `token_cache` which accumulates.
            # If regex finds nothing, it means the model output so far (or this slice) has no speech tokens.
            raise ValueError(f"No valid speech tokens found in the output. Codes content preview: {codes[:100]}...")

    def _to_phones(self, text: str) -> str:
        phones = self.phonemizer.phonemize([text])
        phones = phones[0].split()
        phones = " ".join(phones)
        return phones

    def _apply_chat_template(
        self, ref_codes: list[int], ref_text: str, input_text: str
    ) -> list[int]:

        input_text = self._to_phones(ref_text) + " " + self._to_phones(input_text)
        speech_replace = self.tokenizer.convert_tokens_to_ids("<|SPEECH_REPLACE|>")
        speech_gen_start = self.tokenizer.convert_tokens_to_ids("<|SPEECH_GENERATION_START|>")
        text_replace = self.tokenizer.convert_tokens_to_ids("<|TEXT_REPLACE|>")
        text_prompt_start = self.tokenizer.convert_tokens_to_ids("<|TEXT_PROMPT_START|>")
        text_prompt_end = self.tokenizer.convert_tokens_to_ids("<|TEXT_PROMPT_END|>")

        input_ids = self.tokenizer.encode(input_text, add_special_tokens=False)
        chat = """user: Convert the text to speech:<|TEXT_REPLACE|>\nassistant:<|SPEECH_REPLACE|>"""
        ids = self.tokenizer.encode(chat)

        text_replace_idx = ids.index(text_replace)
        ids = (
            ids[:text_replace_idx]
            + [text_prompt_start]
            + input_ids
            + [text_prompt_end]
            + ids[text_replace_idx + 1 :]  # noqa
        )

        speech_replace_idx = ids.index(speech_replace)
        codes_str = "".join([f"<|speech_{i}|>" for i in ref_codes])
        codes = self.tokenizer.encode(codes_str, add_special_tokens=False)
        ids = ids[:speech_replace_idx] + [speech_gen_start] + list(codes)

        return ids

    def _infer_torch(self, prompt_ids: list[int]) -> str:
        prompt_tensor = torch.tensor(prompt_ids).unsqueeze(0).to(self.backbone.device)
        speech_end_id = self.tokenizer.convert_tokens_to_ids("<|SPEECH_GENERATION_END|>")
        with torch.no_grad():
            output_tokens = self.backbone.generate(
                prompt_tensor,
                max_length=self.max_context,
                eos_token_id=speech_end_id,
                do_sample=True,
                temperature=1.0,
                top_k=50,
                use_cache=True,
                min_new_tokens=50,
            )
        input_length = prompt_tensor.shape[-1]
        output_str = self.tokenizer.decode(
            output_tokens[0, input_length:].cpu().numpy().tolist(), add_special_tokens=False
        )
        return output_str

    def _infer_ggml(self, ref_codes: list[int], ref_text: str, input_text: str) -> str:
        ref_text = self._to_phones(ref_text)
        input_text = self._to_phones(input_text)

        codes_str = "".join([f"<|speech_{idx}|>" for idx in ref_codes])
        prompt = (
            f"user: Convert the text to speech:<|TEXT_PROMPT_START|>{ref_text} {input_text}"
            f"<|TEXT_PROMPT_END|>\nassistant:<|SPEECH_GENERATION_START|>{codes_str}"
        )
        
        # Tokenize with special=True to ensure special tokens are parsed correctly
        prompt_tokens = self.backbone.tokenize(prompt.encode("utf-8"), special=True)
        
        output = self.backbone(
            prompt_tokens,
            max_tokens=self.max_context,
            temperature=1.0,
            top_k=50,
            stop=["<|SPEECH_GENERATION_END|>"],
        )
        output_str = output["choices"][0]["text"]
        return output_str

    def _infer_stream_ggml(self, ref_codes: torch.Tensor, ref_text: str, input_text: str) -> Generator[np.ndarray, None, None]:
            ref_text = self._to_phones(ref_text)
            input_text = self._to_phones(input_text)

            codes_str = "".join([f"<|speech_{idx}|>" for idx in ref_codes])
            prompt = (
                f"user: Convert the text to speech:<|TEXT_PROMPT_START|>{ref_text} {input_text}"
                f"<|TEXT_PROMPT_END|>\nassistant:<|SPEECH_GENERATION_START|>{codes_str}"
            )

            prompt_tokens = self.backbone.tokenize(prompt.encode("utf-8"), special=True)

            # NEW: Initialize the streaming overlap-add buffer
            ola = IncrementalOverlapAdd(stride=self.streaming_stride_samples)

            token_cache: list[str] = [f"<|speech_{idx}|>" for idx in ref_codes]
            n_decoded_tokens: int = len(ref_codes)

            try:
                for item in self.backbone(
                    prompt_tokens,
                    max_tokens=self.max_context,
                    temperature=1.0,
                    top_k=50,
                    stop=["<|SPEECH_GENERATION_END|>"],
                    stream=True
                ):
                    output_str = item["choices"][0]["text"]
                    token_cache.append(output_str)

                    if len(token_cache[n_decoded_tokens:]) >= self.streaming_frames_per_chunk + self.streaming_lookforward:
                        tokens_start = max(
                            n_decoded_tokens
                            - self.streaming_lookback
                            - self.streaming_overlap_frames,
                            0
                        )
                        tokens_end = (
                            n_decoded_tokens
                            + self.streaming_frames_per_chunk
                            + self.streaming_lookforward
                            + self.streaming_overlap_frames
                        )
                        sample_start = (n_decoded_tokens - tokens_start) * self.hop_length
                        sample_end = sample_start + (self.streaming_frames_per_chunk + 2 * self.streaming_overlap_frames) * self.hop_length
                        
                        curr_codes = token_cache[tokens_start:tokens_end]
                        recon = self._decode("".join(curr_codes))
                        
                        if recon.shape[-1] < sample_end:
                            pad_len = sample_end - recon.shape[-1]
                            recon = np.pad(recon, (0, pad_len))

                        recon = recon if self.watermarker is None else self.watermarker.apply_watermark(recon, sample_rate=24_000)
                        recon = recon[sample_start:sample_end]
                        
                        # NEW: Process through the O1 buffer and yield immediately
                        processed_recon = ola.process_frame(recon, is_last=False)
                        if processed_recon.size > 0:
                            yield processed_recon

                        n_decoded_tokens += self.streaming_frames_per_chunk

                # Final decoding chunk
                remaining_tokens = len(token_cache) - n_decoded_tokens
                if len(token_cache) > n_decoded_tokens:
                    tokens_start = max(
                        len(token_cache)
                        - (self.streaming_lookback + self.streaming_overlap_frames + remaining_tokens),
                        0
                    )
                    sample_start = (
                        len(token_cache)
                        - tokens_start
                        - remaining_tokens
                        - self.streaming_overlap_frames
                    ) * self.hop_length
                    
                    curr_codes = token_cache[tokens_start:]
                    recon = self._decode("".join(curr_codes))
                    recon = recon if self.watermarker is None else self.watermarker.apply_watermark(recon, sample_rate=24_000)
                    recon = recon[sample_start:]

                    # NEW: Process final chunk and flush the buffer
                    processed_recon = ola.process_frame(recon, is_last=True)
                    if processed_recon.size > 0:
                        yield processed_recon
                else:
                    # NEW: Flush the OLA buffer in case there's leftover audio tail
                    processed_recon = ola.process_frame(np.array([], dtype=np.float32), is_last=True)
                    if processed_recon.size > 0:
                        yield processed_recon
            finally:
                # EXPLICIT MEMORY CLEANUP
                # This runs no matter what, even if the user disconnects and aborts the generator
                del ola
                del token_cache
                # Clear large local variables to ensure reference counts hit 0
                curr_codes = None 
                recon = None
                processed_recon = None
                
                # Force the garbage collector to reclaim the Numpy arrays immediately
                gc.collect()
