FROM python:3.12-slim

WORKDIR /app

ENV PYTHONPATH=/app
ENV VIRTUAL_ENV=/app/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential python3-dev locales libffi-dev ffmpeg libopus-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set locale
RUN sed -i -e 's/# en_GB UTF-8/en_GB UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

ENV LANG=en_GB.UTF-8
ENV LC_ALL=en_GB.UTF-8

# Create and activate virtual environment
RUN python -m venv $VIRTUAL_ENV

# Copy requirements first for better caching
COPY requirements/base.txt requirements/base.txt

# Install dependencies using uv
RUN pip install uv \
    && uv pip install --no-cache -r requirements/base.txt

# Copy source code
COPY src/ src/