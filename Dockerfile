# Stage 0: Frontend Builder
FROM node:22-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 1: Build flash-attn wheel (optional but recommended for ~2x TTS speedup)
# This needs nvcc from the devel image.  The wheel is copied into the runtime
# stage below.  Comment out this stage and the COPY --from=flash-builder line
# if your GPU does not support FlashAttention 2 (requires Ampere / sm_80+).
FROM pytorch/pytorch:2.10.0-cuda12.8-cudnn9-devel AS flash-builder
# Allow pip to install into the system Python — this stage is throwaway (only the .whl is kept).
ENV PIP_BREAK_SYSTEM_PACKAGES=1
# flash-attn's setup.py needs git; the 2.10.0 devel image doesn't ship it.
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir packaging ninja
# MAX_JOBS=1 keeps peak RAM under ~4 GB so WSL doesn't OOM.
# Raise to 2 if you have >=16 GB available; avoid 4+ on memory-constrained WSL.
# --no-build-isolation → build against the torch already in the image.
# --no-deps          → don't resolve runtime deps; we only need the compiled .whl.
RUN MAX_JOBS=1 pip wheel --no-cache-dir --no-deps --wheel-dir /wheels flash-attn --no-build-isolation

# Stage 2: Runtime
FROM pytorch/pytorch:2.10.0-cuda12.8-cudnn9-runtime

# Install runtime system dependencies
# build-essential (gcc) is required at runtime by PyTorch's Triton JIT compiler
# (used by sentence-transformers / torch.compile for embedding generation).
# sox is used by Qwen3-TTS for audio processing.
RUN apt-get update && apt-get install -y \
    git \
    nano \
    espeak-ng \
    sox \
    avahi-daemon \
    avahi-utils \
    dbus \
    build-essential \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Configure Avahi to run in container
RUN sed -i 's/#enable-dbus=yes/enable-dbus=yes/' /etc/avahi/avahi-daemon.conf && \
    sed -i 's/rlimit-nproc=3/#rlimit-nproc=3/' /etc/avahi/avahi-daemon.conf

WORKDIR /app

# Persist HuggingFace model cache inside /app so it survives container restarts
# when /app is bind-mounted from the host.
ENV HF_HOME=/app/.cache/huggingface

# Create a venv that inherits PyTorch from the base image
ENV VENV_PATH=/opt/venv
RUN python -m venv --system-site-packages ${VENV_PATH}
ENV PATH="${VENV_PATH}/bin:${PATH}"

COPY requirements.txt .

# Lock torch/CUDA/triton packages from the base image so pip won't re-download
# them. Strip the +cu128 local version tag — pip can't match it against PyPI.
RUN pip freeze | grep -iE '^(torch|nvidia|triton|cuda)' | grep '==' \
    | sed 's/+cu[0-9]*//' > /tmp/base-constraints.txt
RUN pip install --no-cache-dir -c /tmp/base-constraints.txt -r requirements.txt

# Install the pre-built flash-attn wheel from Stage 1.
# Comment out the next two lines if you skipped the flash-builder stage.
COPY --from=flash-builder /wheels /tmp/flash-wheels
RUN pip install --no-cache-dir /tmp/flash-wheels/*.whl && rm -rf /tmp/flash-wheels

# Copy frontend build
COPY --from=frontend-builder /frontend/dist /usr/share/app/static

# Copy app code
COPY . .

# Copy and setup entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Copy mDNS service definition
COPY arthur.service /etc/avahi/services/arthur.service

# Expose mDNS port
EXPOSE 5353/udp

ENTRYPOINT ["/entrypoint.sh"]
