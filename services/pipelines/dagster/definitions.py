import os
import io
import pandas as pd
from dagster import (
    Definitions, asset, AssetExecutionContext,
    define_asset_job, ScheduleDefinition,
)
from minio import Minio


def get_minio_client() -> Minio:
    return Minio(
        os.getenv("MINIO_ENDPOINT", "minio:9000"),
        access_key=os.getenv("MINIO_ROOT_USER", "minioadmin"),
        secret_key=os.getenv("MINIO_ROOT_PASSWORD", "minioadmin_secret"),
        secure=False,
    )


@asset(description="Load raw CSV datasets from MinIO object storage")
def raw_datasets(context: AssetExecutionContext) -> dict:
    client = get_minio_client()
    bucket = os.getenv("MINIO_BUCKET", "odp-data")

    objects = client.list_objects(bucket, prefix="datasets/", recursive=True)
    datasets = {}

    for obj in objects:
        if obj.object_name.endswith(".csv"):
            response = client.get_object(bucket, obj.object_name)
            content = response.read()
            response.close()
            response.release_conn()

            df = pd.read_csv(io.BytesIO(content))
            name = obj.object_name.split("/")[-1].replace(".csv", "")
            datasets[name] = df
            context.log.info(f"Loaded dataset '{name}' with {len(df)} rows")

    context.log.info(f"Total datasets loaded: {len(datasets)}")
    return datasets


@asset(description="Clean and transform raw datasets", deps=[raw_datasets])
def transformed_datasets(context: AssetExecutionContext, raw_datasets: dict) -> dict:
    transformed = {}

    for name, df in raw_datasets.items():
        clean_df = df.dropna(how="all")
        clean_df.columns = [c.strip().lower().replace(" ", "_") for c in clean_df.columns]

        for col in clean_df.select_dtypes(include=["object"]).columns:
            clean_df[col] = clean_df[col].str.strip()

        transformed[name] = clean_df
        context.log.info(f"Transformed '{name}': {len(df)} -> {len(clean_df)} rows")

    return transformed


@asset(description="Load transformed data into ClickHouse analytics tables", deps=[transformed_datasets])
def analytics_tables(context: AssetExecutionContext, transformed_datasets: dict) -> list[str]:
    import httpx

    ch_host = os.getenv("CLICKHOUSE_HOST", "clickhouse")
    ch_port = os.getenv("CLICKHOUSE_PORT", "8123")
    ch_db = os.getenv("CLICKHOUSE_DB", "odp")
    ch_user = os.getenv("CLICKHOUSE_USER", "default")
    ch_password = os.getenv("CLICKHOUSE_PASSWORD", "clickhouse_secret")

    tables_created = []

    for name, df in transformed_datasets.items():
        table_name = f"analytics_{name}"
        columns = []
        for col, dtype in df.dtypes.items():
            if "int" in str(dtype):
                ch_type = "Int64"
            elif "float" in str(dtype):
                ch_type = "Float64"
            else:
                ch_type = "String"
            columns.append(f"`{col}` {ch_type}")

        create_sql = f"""
            CREATE TABLE IF NOT EXISTS {ch_db}.{table_name} (
                {', '.join(columns)}
            ) ENGINE = MergeTree()
            ORDER BY tuple()
        """

        url = f"http://{ch_host}:{ch_port}"
        params = {"database": ch_db, "user": ch_user, "password": ch_password}

        with httpx.Client() as client:
            r = client.post(url, params=params, content=create_sql)
            if not r.is_success:
                raise RuntimeError(f"ClickHouse CREATE failed: {r.text}")

            csv_data = df.to_csv(index=False)
            insert_sql = f"INSERT INTO {ch_db}.{table_name} FORMAT CSVWithNames"
            r = client.post(url, params=params, content=f"{insert_sql}\n{csv_data}")
            if not r.is_success:
                raise RuntimeError(f"ClickHouse INSERT failed: {r.text}")

        tables_created.append(table_name)
        context.log.info(f"Loaded {len(df)} rows into {table_name}")

    return tables_created


sample_pipeline_job = define_asset_job(
    name="sample_pipeline",
    selection=[raw_datasets, transformed_datasets, analytics_tables],
    description="End-to-end pipeline: MinIO -> Transform -> ClickHouse",
)

sample_schedule = ScheduleDefinition(
    job=sample_pipeline_job,
    cron_schedule="0 */6 * * *",
    description="Run sample pipeline every 6 hours",
)

defs = Definitions(
    assets=[raw_datasets, transformed_datasets, analytics_tables],
    jobs=[sample_pipeline_job],
    schedules=[sample_schedule],
)
