# Stage 0: Frontend Builder
FROM node:22-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 1: Runtime
FROM pytorch/pytorch:2.10.0-cuda12.8-cudnn9-runtime

# Install runtime system dependencies
# build-essential (gcc) is required at runtime by PyTorch's Triton JIT compiler
# (used by sentence-transformers / torch.compile for embedding generation).
RUN apt-get update && apt-get install -y \
    git \
    nano \
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
