try:
    from gpt4all import GPT4All
    print("GPT4All imported successfully")
    # GPT4All.list_gpus() is the method to list available devices
    gpus = GPT4All.list_gpus()
    print(f"Available GPUs: {gpus}")
except ImportError:
    print("gpt4all not installed")
except Exception as e:
    print(f"Error checking GPUs: {e}")
