FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend /app/backend
COPY .env.example /app/.env

# Add backend to PYTHONPATH
ENV PYTHONPATH=/app/backend

WORKDIR /app/backend

# Default entrypoint runs interactive demo
CMD ["python", "-m", "failureforge.cli.main", "demo"]
