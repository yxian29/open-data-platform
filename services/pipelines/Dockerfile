FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl git && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY services/pipelines/pyproject.toml /app/
RUN pip install --no-cache-dir .

COPY shared /app/shared
COPY services/pipelines/src /app/src
COPY services/pipelines/dagster /app/dagster
COPY services/pipelines/dbt /app/dbt

ENV PYTHONPATH=/app
ENV DAGSTER_HOME=/app/dagster

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002", "--reload"]
