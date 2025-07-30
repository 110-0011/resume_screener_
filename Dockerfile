FROM python:3.12-slim

# Install system packages and Rust
RUN apt-get update && apt-get install -y \
    curl build-essential pkg-config libssl-dev && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable && \
    . "$HOME/.cargo/env"

WORKDIR /app

COPY requirements.txt .

# Upgrade pip and install torch first
RUN pip install --upgrade pip setuptools wheel && \
    pip install torch==2.7.1 -f https://download.pytorch.org/whl/cpu/torch_stable.html && \
    pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]
