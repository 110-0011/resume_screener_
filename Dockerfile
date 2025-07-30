# === Stage 1: Build Stage (with Rust and build tools) ===
FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    curl build-essential pkg-config libssl-dev git && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable && \
    . "$HOME/.cargo/env"

WORKDIR /app

COPY requirements.txt .

# Upgrade pip and install torch separately (CPU only)
RUN pip install --upgrade pip setuptools wheel && \
    pip install torch==2.7.1 -f https://download.pytorch.org/whl/cpu/torch_stable.html

# Install remaining Python dependencies
RUN pip install -r requirements.txt

# Install spacy English model
RUN pip install "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"

# === Stage 2: Runtime Stage (minimal, no Rust) ===
FROM python:3.12-slim

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Ensure upload directory exists
RUN mkdir -p uploads

EXPOSE 8000

# Run using gunicorn; Render requires dynamic port
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT", "--workers", "4"]
