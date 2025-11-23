# Dockerfile for ALFWorld REST API Server
# Uses pre-built vzhong/alfworld as base and adds FastAPI server
FROM vzhong/alfworld:latest

# Install FastAPI and uvicorn
RUN pip install --no-cache-dir fastapi uvicorn[standard]

# Copy API server
COPY alfworld_api.py /app/alfworld_api.py

# Set working directory
WORKDIR /app

EXPOSE 8000

# Run the API server
CMD ["python3", "-m", "uvicorn", "alfworld_api:app", "--host", "0.0.0.0", "--port", "8000"]