"""Parse dbt SQL models to extract column-level lineage."""

import os
import re
from pathlib import Path

REF_PATTERN = re.compile(r"\{\{\s*ref\(\s*'(\w+)'\s*\)\s*\}\}")
SOURCE_PATTERN = re.compile(r"\{\{\s*source\(\s*'(\w+)'\s*,\s*'(\w+)'\s*\)\s*\}\}")
SELECT_COL_PATTERN = re.compile(
    r"(?:(\w+)\.)?(\w+)\s+AS\s+(\w+)|(?:(\w+)\.)?(\w+)\s*(?:,|$)",
    re.IGNORECASE,
)
AGG_PATTERN = re.compile(r"(count|sum|avg|min|max)\(([^)]+)\)", re.IGNORECASE)


def parse_dbt_models(dbt_dir: str) -> dict:
    """Returns {model_name: {sources: [...], columns: [...]}}"""
    models_dir = Path(dbt_dir) / "models"
    results = {}

    for sql_file in models_dir.rglob("*.sql"):
        model_name = sql_file.stem
        content = sql_file.read_text()
        results[model_name] = _parse_model(model_name, content)

    return results


def _parse_model(model_name: str, sql: str) -> dict:
    refs = REF_PATTERN.findall(sql)
    sources = SOURCE_PATTERN.findall(sql)

    clean_sql = REF_PATTERN.sub("__ref__", sql)
    clean_sql = SOURCE_PATTERN.sub("__source__", clean_sql)

    upstream_tables = []
    for ref in refs:
        upstream_tables.append({"type": "ref", "name": ref})
    for schema, table in sources:
        upstream_tables.append({"type": "source", "schema": schema, "name": table})

    columns = _extract_columns(sql)

    return {
        "model_name": model_name,
        "upstream": upstream_tables,
        "columns": columns,
    }


def _extract_columns(sql: str) -> list[dict]:
    """Extract output columns from a SELECT statement."""
    columns = []
    select_match = re.search(r"SELECT\s+(.*?)\s+FROM", sql, re.DOTALL | re.IGNORECASE)
    if not select_match:
        return columns

    select_body = select_match.group(1)

    for line in select_body.split(","):
        line = line.strip()
        if not line:
            continue

        agg = AGG_PATTERN.search(line)
        as_match = re.search(r"\bAS\s+(\w+)", line, re.IGNORECASE)
        output_name = as_match.group(1) if as_match else None

        if agg:
            func = agg.group(1).lower()
            inner = agg.group(2).strip()
            source_col_match = re.search(r"(\w+)\.(\w+)", inner)
            if source_col_match:
                source_alias = source_col_match.group(1)
                source_col = source_col_match.group(2)
            else:
                source_alias = None
                source_col = inner
            columns.append({
                "name": output_name or f"{func}_{source_col}",
                "source_alias": source_alias,
                "source_column": source_col,
                "transform": func,
            })
        else:
            col_match = re.match(r"(?:(\w+)\.)?(\w+)(?:\s+AS\s+(\w+))?", line, re.IGNORECASE)
            if col_match:
                alias = col_match.group(1)
                col = col_match.group(2)
                out = col_match.group(3) or col
                columns.append({
                    "name": out,
                    "source_alias": alias,
                    "source_column": col,
                    "transform": None,
                })

    return columns


def build_lineage_graph(dbt_dir: str) -> dict:
    """Build a full lineage graph from dbt models."""
    models = parse_dbt_models(dbt_dir)

    nodes = []
    edges = []
    node_index = {}

    def get_or_create_node(node_type, table_name, column_name=None, transform_name=None):
        key = (node_type, table_name, column_name, transform_name)
        if key in node_index:
            return node_index[key]
        node = {
            "node_type": node_type,
            "table_name": table_name,
            "column_name": column_name,
            "transform_name": transform_name,
        }
        node_index[key] = len(nodes)
        nodes.append(node)
        return len(nodes) - 1

    for model_name, info in models.items():
        for col in info["columns"]:
            target_idx = get_or_create_node("target_column", model_name, col["name"])

            if col["transform"]:
                transform_idx = get_or_create_node(
                    "transform", model_name, transform_name=f"{col['transform']}({col['source_column']})"
                )
                edges.append({"source": transform_idx, "target": target_idx, "edge_type": "produces"})

                for upstream in info["upstream"]:
                    src_table = upstream["name"]
                    src_idx = get_or_create_node("source_column", src_table, col["source_column"])
                    edges.append({"source": src_idx, "target": transform_idx, "edge_type": "feeds_into"})
            else:
                for upstream in info["upstream"]:
                    src_table = upstream["name"]
                    src_idx = get_or_create_node("source_column", src_table, col["source_column"])
                    edges.append({"source": src_idx, "target": target_idx, "edge_type": "derives_from"})

    return {"nodes": nodes, "edges": edges}
