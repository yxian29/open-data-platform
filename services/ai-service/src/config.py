from pydantic_settings import BaseSettings


class AISettings(BaseSettings):
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "postgres"
    postgres_user: str = "postgres"
    postgres_password: str = "P0stG&e$"

    clickhouse_host: str = "localhost"
    clickhouse_port: int = 9000
    clickhouse_db: str = "odp"
    clickhouse_user: str = "default"
    clickhouse_password: str = "clickhouse_secret"

    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_secret"

    claude_bridge_url: str = "http://host.docker.internal:9999"
    chroma_path: str = "/app/chroma_data"
    embedding_model: str = "all-MiniLM-L6-v2"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = AISettings()
