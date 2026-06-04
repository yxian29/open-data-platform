FROM artprod.dev.bloomberg.com/python3:3.12-rhel8

WORKDIR /app

RUN yum install -y curl && yum clean all

COPY services/ai-service/pyproject.toml /app/
RUN pip install --no-cache-dir .

COPY shared /app/shared
COPY services/ai-service/src /app/src

ENV PYTHONPATH=/app

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8004", "--reload"]
