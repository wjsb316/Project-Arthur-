FROM pytorch/pytorch:2.9.1-cuda13.0-cudnn9-runtime

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    nano \
    ffmpeg \
    espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy requirements file to the image
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# The code will be mounted at runtime via the volume
