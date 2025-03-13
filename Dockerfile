FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    git \
    wget \
    curl \
    p7zip-full \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    libgomp1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a working directory
WORKDIR /workspace

# Install RunPod SDK
RUN pip3 install --no-cache-dir runpod requests

# Download the pre-packaged Forge release
RUN wget -q -O webui_forge.7z https://github.com/lllyasviel/stable-diffusion-webui-forge/releases/download/latest/webui_forge_cu121_torch231.7z \
    && 7z x webui_forge.7z -o/workspace \
    && rm webui_forge.7z

# Create directory for models and download a model
RUN mkdir -p /workspace/webui/models/Stable-diffusion
RUN wget -q -O /workspace/webui/models/Stable-diffusion/MAI_Pony-v1R.safetensors \
    https://huggingface.co/Meowmeow42/NewStart/resolve/main/MAI_Pony-v1R.safetensors

# Copy the handler
COPY handler.py /workspace/handler.py

# Create startup script
RUN echo '#!/bin/bash\n\
echo "Updating WebUI Forge..."\n\
cd /workspace\n\
bash update.bat\n\
\n\
echo "Starting WebUI..."\n\
cd /workspace\n\
bash run.bat --api --xformers --port 3000 --skip-torch-cuda-test &\n\
WEBUI_PID=$!\n\
\n\
# Wait for the WebUI to start\n\
MAX_ATTEMPTS=40\n\
ATTEMPT=0\n\
echo "Waiting for WebUI to start..."\n\
\n\
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do\n\
  if curl -s http://127.0.0.1:3000/sdapi/v1/sd-models > /dev/null; then\n\
    echo "WebUI started successfully"\n\
    break\n\
  fi\n\
  echo "Attempt $((ATTEMPT+1))/$MAX_ATTEMPTS: WebUI not ready yet..."\n\
  ATTEMPT=$((ATTEMPT+1))\n\
  sleep 10\n\
done\n\
\n\
if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then\n\
  echo "ERROR: WebUI failed to start after $MAX_ATTEMPTS attempts"\n\
  exit 1\n\
fi\n\
\n\
# Start the handler\n\
cd /workspace\n\
exec python3 -u handler.py\n\
' > /workspace/start.sh && chmod +x /workspace/start.sh

# Use the startup script as the entrypoint
ENTRYPOINT ["/workspace/start.sh"]
