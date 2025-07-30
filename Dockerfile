FROM python:3.12-slim AS builder

# Install system deps needed for building some Python packages + rust (if needed)
RUN apt-get update && apt-get install -y \
    curl build-essential pkg-config libssl-dev && \
    # Install Rust toolchain silently
    curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR /app

# Copy only requirements first for caching
COPY requirements.txt .

# Upgrade pip/setuptools/wheel and install all deps in one shot
RUN pip install --upgrade pip setuptools wheel && \
    # Install CPU-only torch separately first to avoid conflicts if needed
    pip install torch==2.7.1+cpu --find-links https://download.pytorch.org/whl/cpu/torch_stable.html && \
    pip install -r requirements.txt

# Final slim runtime image
FROM python:3.12-slim

WORKDIR /app

# Copy installed python packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

EXPOSE 8000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]
