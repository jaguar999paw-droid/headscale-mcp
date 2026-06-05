FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt uvicorn[standard]

COPY server.py .

EXPOSE 8000

CMD ["python3", "server.py", "--transport", "streamable_http", "--port", "8000"]
