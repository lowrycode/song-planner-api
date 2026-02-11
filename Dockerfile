FROM python:3.12-slim

WORKDIR /src

# Keep Python from generating .pyc files and ensure logs are flush immediately
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD exec gunicorn \
    --bind :${PORT:-8080} \
    --workers 1 \
    --worker-class uvicorn.workers.UvicornWorker \
    --threads 4 \
    --timeout 0 \
    app.main:app
