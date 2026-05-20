# syntax=docker/dockerfile:1.7

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    libglib2.0-0 \
    libgl1 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip install --upgrade pip uv

# Install CPU-only PyTorch wheels before project dependencies. Without this,
# Linux builds can pull multi-GB CUDA packages from PyPI.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system \
    --index-url https://download.pytorch.org/whl/cpu \
    torch torchvision

# Copy dependency files FIRST (for caching)
COPY pyproject.toml .
COPY uv.lock ./

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system .

# Copy rest of the code
COPY . .

EXPOSE 8000
EXPOSE 8501
