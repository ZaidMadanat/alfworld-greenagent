# Dockerfile for ALFWorld REST API Server
# Build with: docker buildx build --platform=linux/amd64 -t green-agent .
FROM ubuntu:22.04

# Set up environment
ENV DEBIAN_FRONTEND=noninteractive

RUN printf 'Acquire::http::Pipeline-Depth "0";\nAcquire::http::No-Cache "true";\nAcquire::BrokenProxy "true";\n' > /etc/apt/apt.conf.d/99fixbadproxy

RUN apt-get update && \
    apt-get install -y --fix-missing \
    python3 python3-pip python3-dev git cmake clang make \
    libgl1-mesa-glx libglib2.0-0 curl \
    || (apt-get update && apt-get install -y --fix-missing \
        python3 python3-pip python3-dev git cmake clang make \
        libgl1-mesa-glx libglib2.0-0 curl) && \
    rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python

# Set clang as default compiler
ENV CC=clang
ENV CXX=clang++

# Install ALFWorld
WORKDIR /app
RUN git clone https://github.com/alfworld/alfworld.git
WORKDIR /app/alfworld
RUN pip install --upgrade pip setuptools wheel
# Install ALFWorld with full extras (works on linux/amd64)
RUN pip install --no-cache-dir -e .[full]

# Download ALFWorld data files
# Set ALFWORLD_DATA to store data in the alfworld directory
ENV ALFWORLD_DATA=/app/alfworld/data
# Download basic data
RUN alfworld-download || echo "Note: Basic data download may have issues"
# Download extra data including eval tasks (if available)
RUN alfworld-download --extra || echo "Note: Extra data download may have issues"
# Also try to ensure eval data directory exists
RUN mkdir -p /app/alfworld/data/base_config/eval_out_of_distribution || true

# Install FastAPI dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard]

# Copy application files
COPY start_agents.py /app/alfworld/start_agents.py
COPY alfworld_api.py /app/alfworld/alfworld_api.py

EXPOSE 8000 9000 9001 9002

# Run the API server by default (can override with docker run)
# Use --reload for development (auto-reload on file changes when using volume mounts)
CMD ["python3", "-m", "uvicorn", "alfworld_api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]