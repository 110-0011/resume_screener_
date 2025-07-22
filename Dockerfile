FROM python:3.12-slim

RUN apt-get update && apt-get install -y curl build-essential pkg-config libssl-dev && \
    curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable && \
    . $HOME/.cargo/env

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]
