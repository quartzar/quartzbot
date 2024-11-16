FROM python:3.12-slim

WORKDIR /app

# Install system dependencies and uv
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    # Required for voice support
    ffmpeg \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

# Create and activate virtual environment
ENV VIRTUAL_ENV=/app/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Copy requirements first for better caching
COPY requirements/base.txt requirements/base.txt

# Install dependencies using uv
RUN uv pip install --no-cache -r requirements/base.txt

# Copy source code
COPY src/ src/

# Set Python path
ENV PYTHONPATH=/app