
from qwen_tts import Qwen3TTSModel
import inspect

print("Checking Qwen3TTSModel methods...")
methods = [m for m in dir(Qwen3TTSModel) if "stream" in m]
print("Streaming methods:", methods)

try:
    if "stream_generate_custom_voice" in methods:
        print("\nSignature of stream_generate_custom_voice:")
        print(inspect.signature(Qwen3TTSModel.stream_generate_custom_voice))
except Exception as e:
    print(e)
