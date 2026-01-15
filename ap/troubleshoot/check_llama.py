try:
    from llama_cpp import Llama
    print("llama_cpp imported successfully")
    # Check if compiled with CUDA
    # usually indicated in build info or by trying to load a model with n_gpu_layers
    # but we can check if the library file has cuda symbols or just try to init with gpu
    import os
    # Create a dummy model or check build options if exposed
    print("Checking if CUDA is enabled in llama-cpp-python...")
    # There isn't a direct "is_cuda_available" but we can try to load a dummy model or check __file__
    print(f"File: {Llama.__file__}")
except ImportError:
    print("llama_cpp not installed")
except Exception as e:
    print(f"Error checking llama_cpp: {e}")
