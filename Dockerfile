# Stage 1: Builder (with CUDA compiler)
# We use the 'devel' tag which includes nvcc (needed to compile llama-cpp-python with GPU support)
FROM pytorch/pytorch:2.9.1-cuda12.8-cudnn9-devel AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    cmake \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements to build wheels
COPY requirements.txt .

# Build llama-cpp-python wheel with CUDA support enabled
# -DGGML_CUDA=on enables CUDA kernels
RUN CMAKE_ARGS="-DGGML_CUDA=on" pip wheel --no-cache-dir --wheel-dir /build/wheels llama-cpp-python==0.3.16


# Stage 2: Runtime (Slim final image)
FROM pytorch/pytorch:2.9.1-cuda12.8-cudnn9-runtime

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    git \
    nano \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy built wheels from the builder stage
COPY --from=builder /build/wheels /wheels

# Copy requirements file
COPY requirements.txt .

# Install dependencies
# 1. Install llama-cpp-python specifically from our built wheels (force no PyPI lookup for this package)
# 2. Install the rest from requirements.txt
RUN pip install --no-cache-dir --no-index --find-links=/wheels llama-cpp-python==0.3.16 && \
    pip install --no-cache-dir -r requirements.txt

# The code will be mounted at runtime via the volume
