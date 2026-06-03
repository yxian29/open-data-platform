import uuid
import json
import os
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException

from shared.db.postgres import get_connection
from shared.models.pipeline import PipelineCreate, PipelineResponse, PipelineRunResponse

DAGSTER_URL = os.getenv("DAGSTER_URL", "http://dagster-webserver:3100")
_LAUNCH_MUTATION = """
mutation LaunchRun($params: ExecutionParams!) {
  launchRun(executionParams: $params) {
    __typename
    ... on LaunchRunSuccess { run { runId } }
    ... on PythonError { message }
  }
}
"""
_STATUS_QUERY = """
query RunStatus($runId: ID!) {
  runOrError(runId: $runId) {
    ... on Run { runId status }
  }
}
"""

router = APIRouter()


@router.post("", response_model=PipelineResponse)
async def create_pipeline(body: PipelineCreate):
    pipeline_id = uuid.uuid4()
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO pipeline_definitions (id, name, description, pipeline_type, config, schedule)
            VALUES ($1, $2, $3, $4, $5::jsonb, $6)
            RETURNING *
            """,
            pipeline_id, body.name, body.description, body.pipeline_type,
            json.dumps(body.config), body.schedule,
        )
    return _pipeline_row_to_response(row)


@router.get("", response_model=list[PipelineResponse])
async def list_pipelines():
    async with get_connection() as conn:
        rows = await conn.fetch("SELECT * FROM pipeline_definitions ORDER BY created_at DESC")
    return [_pipeline_row_to_response(r) for r in rows]


@router.get("/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(pipeline_id: str):
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM pipeline_definitions WHERE id = $1",
            uuid.UUID(pipeline_id),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return _pipeline_row_to_response(row)


@router.post("/{pipeline_id}/run", response_model=PipelineRunResponse)
async def trigger_pipeline(pipeline_id: str, background_tasks: BackgroundTasks):
    async with get_connection() as conn:
        pipeline = await conn.fetchrow(
            "SELECT * FROM pipeline_definitions WHERE id = $1",
            uuid.UUID(pipeline_id),
        )
        if not pipeline:
            raise HTTPException(status_code=404, detail="Pipeline not found")

        run_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        row = await conn.fetchrow(
            """
            INSERT INTO pipeline_runs (id, pipeline_id, status, started_at)
            VALUES ($1, $2, 'running', $3)
            RETURNING *
            """,
            run_id, uuid.UUID(pipeline_id), now,
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{DAGSTER_URL}/graphql",
                json={
                    "query": _LAUNCH_MUTATION,
                    "variables": {
                        "params": {
                            "selector": {
                                "repositoryLocationName": "definitions.py",
                                "repositoryName": "__repository__",
                                "jobName": "sample_pipeline",
                            },
                            "runConfigData": {},
                        }
                    },
                },
            )
        result = resp.json()
        launch = result["data"]["launchRun"]
        if launch["__typename"] != "LaunchRunSuccess":
            raise RuntimeError(launch.get("message", "Dagster launch failed"))
        dagster_run_id = launch["run"]["runId"]
    except Exception as exc:
        async with get_connection() as conn:
            row = await conn.fetchrow(
                """
                UPDATE pipeline_runs SET status = 'failed', completed_at = $2, error = $3
                WHERE id = $1 RETURNING *
                """,
                run_id, datetime.now(timezone.utc), str(exc),
            )
        return _run_row_to_response(row)

    background_tasks.add_task(_poll_dagster_run, run_id, dagster_run_id)
    return _run_row_to_response(row)


async def _poll_dagster_run(run_id: uuid.UUID, dagster_run_id: str) -> None:
    import asyncio
    terminal = {"SUCCESS", "FAILURE", "CANCELED"}
    for _ in range(120):
        await asyncio.sleep(5)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{DAGSTER_URL}/graphql",
                    json={"query": _STATUS_QUERY, "variables": {"runId": dagster_run_id}},
                )
            dagster_status = resp.json()["data"]["runOrError"]["status"]
        except Exception:
            continue

        if dagster_status in terminal:
            status = "completed" if dagster_status == "SUCCESS" else "failed"
            async with get_connection() as conn:
                await conn.execute(
                    """
                    UPDATE pipeline_runs SET status = $2, completed_at = $3,
                    logs = $4
                    WHERE id = $1
                    """,
                    run_id, status, datetime.now(timezone.utc),
                    f"Dagster run {dagster_run_id} finished with status {dagster_status}",
                )
            return


@router.get("/{pipeline_id}/runs", response_model=list[PipelineRunResponse])
async def list_runs(pipeline_id: str):
    async with get_connection() as conn:
        rows = await conn.fetch(
            "SELECT * FROM pipeline_runs WHERE pipeline_id = $1 ORDER BY created_at DESC",
            uuid.UUID(pipeline_id),
        )
    return [_run_row_to_response(r) for r in rows]


@router.get("/{pipeline_id}/runs/{run_id}", response_model=PipelineRunResponse)
async def get_run(pipeline_id: str, run_id: str):
    async with get_connection() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM pipeline_runs WHERE id = $1 AND pipeline_id = $2",
            uuid.UUID(run_id), uuid.UUID(pipeline_id),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_row_to_response(row)


@router.delete("/{pipeline_id}")
async def delete_pipeline(pipeline_id: str):
    async with get_connection() as conn:
        await conn.execute(
            "DELETE FROM pipeline_definitions WHERE id = $1",
            uuid.UUID(pipeline_id),
        )
    return {"status": "deleted", "id": pipeline_id}


def _pipeline_row_to_response(row) -> PipelineResponse:
    config = row["config"]
    if isinstance(config, str):
        config = json.loads(config)
    return PipelineResponse(
        id=row["id"],
        name=row["name"],
        description=row["description"],
        pipeline_type=row["pipeline_type"],
        config=config,
        schedule=row["schedule"],
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _run_row_to_response(row) -> PipelineRunResponse:
    return PipelineRunResponse(
        id=row["id"],
        pipeline_id=row["pipeline_id"],
        status=row["status"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        logs=row["logs"],
        error=row["error"],
        created_at=row["created_at"],
    )
