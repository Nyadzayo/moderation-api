# Multi-stage Dockerfile for production

# Stage 1: Base dependencies
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Download model
FROM base as model-download

# Create models cache directory
RUN mkdir -p /app/models_cache

# Copy download script
COPY download_model.py .

# Set environment variables for download
ENV DEFAULT_MODEL=unitary/toxic-bert
ENV MODEL_CACHE_DIR=/app/models_cache

# Pre-download the model (baked into image)
RUN python download_model.py

# Stage 3: Production
FROM base as production

# Copy application code
COPY app/ /app/app/

# Copy pre-downloaded model from previous stage
COPY --from=model-download /app/models_cache /app/models_cache

# Set model cache directory
ENV MODEL_CACHE_DIR=/app/models_cache

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/v1/health')"

# Run with uvicorn (reduce workers to 2 for memory efficiency)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]