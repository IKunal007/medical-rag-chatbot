FROM python:3.11-slim

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    poppler-utils \
    libgl1 \
    curl \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip install --upgrade pip uv

# Copy dependency files FIRST (for caching)
COPY pyproject.toml .
COPY uv.lock ./

# Install dependencies
RUN uv pip install --system .

# Copy rest of the code
COPY . .

EXPOSE 8000
EXPOSE 8501
