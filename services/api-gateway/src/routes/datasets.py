import csv
import io
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from minio import S3Error

from shared.config import settings
from shared.db.postgres import get_connection
from shared.db.minio_client import get_minio_client
from shared.models.dataset import DatasetResponse, ColumnInfo, DatasetSchema

router = APIRouter()


def infer_column_type(values: list[str]) -> str:
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return "string"

    for v in non_empty:
        try:
            int(v)
        except ValueError:
            break
    else:
        return "integer"

    for v in non_empty:
        try:
            float(v)
        except ValueError:
            break
    else:
        return "float"

    lower = [v.lower() for v in non_empty]
    if all(v in ("true", "false", "0", "1", "yes", "no") for v in lower):
        return "boolean"

    return "string"


def infer_schema(content: bytes, source_type: str) -> tuple[DatasetSchema, int]:
    if source_type == "csv":
        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            return DatasetSchema(columns=[]), 0

        columns = []
        for col in reader.fieldnames or []:
            values = [row.get(col, "") for row in rows[:100]]
            col_type = infer_column_type(values)
            has_nulls = any(v.strip() == "" for v in values)
            samples = [v for v in values[:5] if v.strip()]
            columns.append(ColumnInfo(
                name=col,
                data_type=col_type,
                nullable=has_nulls,
                sample_values=samples,
            ))
        return DatasetSchema(columns=columns), len(rows)

    elif source_type == "json":
        data = json.loads(content)
        if isinstance(data, list) and data:
            sample = data[0] if isinstance(data[0], dict) else {}
            columns = [
                ColumnInfo(name=k, data_type=type(v).__name__, nullable=True)
                for k, v in sample.items()
            ]
            return DatasetSchema(columns=columns), len(data)
        return DatasetSchema(columns=[]), 0

    return DatasetSchema(columns=[]), 0


@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(
    file: UploadFile = File(...),
    name: str = Form(""),
    description: str = Form(""),
):
    content = await file.read()
    file_size = len(content)

    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    source_type = {"csv": "csv", "json": "json", "parquet": "parquet"}.get(ext, "binary")

    dataset_name = name or filename.rsplit(".", 1)[0]
    dataset_id = str(uuid.uuid4())
    storage_path = f"datasets/{dataset_id}/{filename}"

    client = get_minio_client()
    client.put_object(
        settings.minio_bucket,
        storage_path,
        io.BytesIO(content),
        length=file_size,
        content_type=file.content_type or "application/octet-stream",
    )

    schema, row_count = infer_schema(content, source_type)

    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO datasets (id, name, description, source_type, storage_path, schema_info, row_count, file_size_bytes)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)
            RETURNING *
            """,
            uuid.UUID(dataset_id), dataset_name, description, source_type,
            storage_path, schema.model_dump_json(), row_count, file_size,
        )

    return _row_to_response(row)


@router.get("", response_model=list[DatasetResponse])
async def list_datasets():
    async with get_connection() as conn:
        rows = await conn.fetch("SELECT * FROM datasets ORDER BY created_at DESC")
    return [_row_to_response(r) for r in rows]


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: str):
    async with get_connection() as conn:
        row = await conn.fetchrow("SELECT * FROM datasets WHERE id = $1", uuid.UUID(dataset_id))
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return _row_to_response(row)


@router.get("/{dataset_id}/preview")
async def preview_dataset(dataset_id: str, limit: int = 50):
    async with get_connection() as conn:
        row = await conn.fetchrow("SELECT * FROM datasets WHERE id = $1", uuid.UUID(dataset_id))
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")

    client = get_minio_client()
    try:
        response = client.get_object(settings.minio_bucket, row["storage_path"])
        content = response.read()
        response.close()
        response.release_conn()
    except S3Error:
        raise HTTPException(status_code=404, detail="File not found in storage")

    source_type = row["source_type"]
    if source_type == "csv":
        text = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for i, r in enumerate(reader):
            if i >= limit:
                break
            rows.append(r)
        return {"columns": reader.fieldnames, "rows": rows, "total": row["row_count"]}

    elif source_type == "json":
        data = json.loads(content)
        if isinstance(data, list):
            return {"rows": data[:limit], "total": len(data)}
        return {"data": data}

    raise HTTPException(status_code=400, detail=f"Preview not supported for {source_type}")


@router.delete("/{dataset_id}")
async def delete_dataset(dataset_id: str):
    async with get_connection() as conn:
        row = await conn.fetchrow("SELECT * FROM datasets WHERE id = $1", uuid.UUID(dataset_id))
    if not row:
        raise HTTPException(status_code=404, detail="Dataset not found")

    client = get_minio_client()
    try:
        client.remove_object(settings.minio_bucket, row["storage_path"])
    except S3Error:
        pass

    async with get_connection() as conn:
        await conn.execute("DELETE FROM datasets WHERE id = $1", uuid.UUID(dataset_id))

    return {"status": "deleted", "id": dataset_id}


def _row_to_response(row) -> DatasetResponse:
    schema_info = row["schema_info"]
    if isinstance(schema_info, str):
        schema_info = json.loads(schema_info)

    return DatasetResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        source_type=row["source_type"],
        storage_path=row["storage_path"],
        schema_info=schema_info,
        row_count=row["row_count"],
        file_size_bytes=row["file_size_bytes"],
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
