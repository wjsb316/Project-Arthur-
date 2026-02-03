import os
import torch
import numpy as np
from neuttsair.neutts import NeuTTSAir
import wave
import argparse

def main(input_text, ref_codes_path, ref_text, backbone, output_path):
    assert backbone in ["neuphonic/neutts-air-q4-gguf", "neuphonic/neutts-air-q8-gguf"], "Must be a GGUF ckpt as streaming is only currently supported by llama-cpp."
    
    # Initialize NeuTTSAir with the desired model and codec
    tts = NeuTTSAir(
        backbone_repo=backbone,
        backbone_device="cpu",
        codec_repo="neuphonic/neucodec-onnx-decoder",
        codec_device="cpu"
    )

    # Check if ref_text is a path if it is read it if not just return string
    if ref_text and os.path.exists(ref_text):
        with open(ref_text, "r") as f:
            ref_text = f.read().strip()

    if ref_codes_path and os.path.exists(ref_codes_path):
        # Load weights_only=False because the .pt likely contains a full tensor structure, not just weights
        # If running on CPU but file saved on GPU, map_location might be needed, but usually torch handles it.
        ref_codes = torch.load(ref_codes_path, weights_only=False)
        if isinstance(ref_codes, torch.Tensor):
            ref_codes = ref_codes.tolist()
    else:
        print(f"Error: Reference codes file not found at {ref_codes_path}")
        return

    print(f"Generating audio for input text: {input_text}")
    
    # Prepare WAV file
    all_pcm_data = bytearray()

    # chunk_count = 0
    # for chunk in self._model.infer_stream(text, self.ref_codes, self.ref_text):
    #     if chunk is None or chunk.size == 0:
    #         continue
    #     chunk_count += 1
    #     audio_data = (chunk * 32767).astype(np.int16)
    #     all_pcm_data.extend(audio_data.tobytes())
    
    print("Streaming generation...")
    chunk_count = 0
    try:
        for chunk in tts.infer_stream(input_text, ref_codes, ref_text):
            if chunk is None or chunk.size == 0:
                continue
            
            chunk_count += 1
            # Convert float32 to int16
            audio_int16 = (chunk * 32767).astype(np.int16)
            all_pcm_data.extend(audio_int16.tobytes())
            
            # Print progress dot
            print(".", end="", flush=True)
            
    except Exception as e:
        print(f"\nError during generation: {e}")

    print(f"\nGenerated {chunk_count} chunks.")
    
    if len(all_pcm_data) > 0:
        with wave.open(output_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2) # 16-bit
            wf.setframerate(24000)
            wf.writeframes(all_pcm_data)
        print(f"Saved audio to {output_path}")
    else:
        print("No audio data generated.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NeuTTSAir Streaming to File Example")
    parser.add_argument(
        "--input_text", 
        type=str, 
        required=True, 
        help="Input text to be converted to speech"
    )
    parser.add_argument(
        "--ref_codes", 
        type=str, 
        default="./samples/dave.pt", 
        help="Path to pre-encoded reference audio"
    )
    parser.add_argument(
        "--ref_text",
        type=str,
        default="./samples/dave.txt", 
        help="Reference text corresponding to the reference audio",
    )
    parser.add_argument(
        "--output_path", 
        type=str, 
        default="output.wav", 
        help="Path to save the output audio"
    )
    parser.add_argument(
        "--backbone", 
        type=str, 
        default="neuphonic/neutts-air-q8-gguf", 
        help="Huggingface repo containing the backbone checkpoint. Must be GGUF."
    )
    args = parser.parse_args()
    main(
        input_text=args.input_text,
        ref_codes_path=args.ref_codes,
        ref_text=args.ref_text,
        backbone=args.backbone,
        output_path=args.output_path,
    )
