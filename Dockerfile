FROM python:3.12-slim

# Install build tools, Rust (for tokenizers, etc.)
RUN apt-get update && apt-get install -y \
    curl build-essential pkg-config libssl-dev && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable && \
    . $HOME/.cargo/env

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install pip dependencies in two steps: torch separately
RUN pip install --upgrade pip setuptools wheel && \
    pip install torch==2.7.1+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html && \
    grep -v '^torch==2.7.1+cpu' requirements.txt > temp_requirements.txt && \
    pip install -r temp_requirements.txt && \
    rm temp_requirements.txt

# Copy the rest of the code
COPY . .

EXPOSE 8000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]
