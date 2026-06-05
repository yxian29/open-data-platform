FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY services/ontology/pyproject.toml /app/
RUN pip install --no-cache-dir .

COPY shared /app/shared
COPY services/ontology/src /app/src

ENV PYTHONPATH=/app

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
