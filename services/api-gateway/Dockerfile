FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY services/api-gateway/pyproject.toml /app/
RUN pip install --no-cache-dir .

COPY shared /app/shared
COPY services/api-gateway/src /app/src

ENV PYTHONPATH=/app

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
