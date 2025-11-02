# Dockerfile.m1 for Apple Silicon / ARM Macs
FROM ubuntu:22.04

# Set up environment
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-dev git cmake clang make \
    libgl1-mesa-glx libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3 /usr/bin/python

# Set clang as default compiler
ENV CC=clang
ENV CXX=clang++

# Install ALFWorld
WORKDIR /app
RUN git clone https://github.com/alfworld/alfworld.git
WORKDIR /app/alfworld
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir  -e .[full]

COPY start_agents.py /app/alfworld/start_agents.py

EXPOSE 8000 9000 9001 9002

CMD ["python3", "start_agents.py"]
