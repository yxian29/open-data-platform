#!/usr/bin/env python3
"""Seed script: uploads sample data to the Open Data Platform."""

import os
import sys
import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")
CH_URL = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")
CH_USER = os.getenv("CLICKHOUSE_USER", "default")
CH_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "clickhouse_secret")
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample-data")


def upload_file(filepath: str):
    name = os.path.basename(filepath).replace(".csv", "").replace(".json", "")
    print(f"  Uploading {name}...")
    with open(filepath, "rb") as f:
        resp = requests.post(
            f"{API_URL}/api/v1/datasets/upload",
            files={"file": (os.path.basename(filepath), f)},
            data={"name": name, "description": f"Sample {name} data"},
        )
    if resp.status_code == 200:
        data = resp.json()
        print(f"    -> {data['name']}: {data['row_count']} rows, {data['file_size_bytes']} bytes")
        return data
    else:
        print(f"    -> FAILED: {resp.status_code} {resp.text}")
        return None


def create_ontology_types():
    print("\nCreating ontology types...")
    types_config = [
        {"name": "Customer", "description": "A customer in the system"},
        {"name": "Order", "description": "A purchase order"},
        {"name": "Product", "description": "A product available for sale"},
    ]

    created = {}
    for t in types_config:
        resp = requests.post(f"{API_URL}/api/v1/ontology/types", json=t)
        if resp.status_code == 200:
            data = resp.json()
            created[t["name"]] = data["id"]
            print(f"  Created type: {t['name']} ({data['id']})")
        else:
            print(f"  FAILED: {t['name']}: {resp.text}")

    if "Customer" in created:
        props = [
            {"name": "name", "data_type": "string", "required": True},
            {"name": "email", "data_type": "string", "required": True},
            {"name": "country", "data_type": "string"},
        ]
        for p in props:
            requests.post(f"{API_URL}/api/v1/ontology/types/{created['Customer']}/properties", json=p)
        print("  Added properties to Customer")

    if "Order" in created:
        props = [
            {"name": "quantity", "data_type": "integer", "required": True},
            {"name": "total_amount", "data_type": "float", "required": True},
            {"name": "status", "data_type": "string"},
            {"name": "order_date", "data_type": "date"},
        ]
        for p in props:
            requests.post(f"{API_URL}/api/v1/ontology/types/{created['Order']}/properties", json=p)
        print("  Added properties to Order")

    if "Product" in created:
        props = [
            {"name": "name", "data_type": "string", "required": True},
            {"name": "category", "data_type": "string"},
            {"name": "price", "data_type": "float", "required": True},
            {"name": "stock", "data_type": "integer"},
        ]
        for p in props:
            requests.post(f"{API_URL}/api/v1/ontology/types/{created['Product']}/properties", json=p)
        print("  Added properties to Product")

    if "Customer" in created and "Order" in created:
        requests.post(f"{API_URL}/api/v1/ontology/types/{created['Customer']}/links", json={
            "name": "placed_order", "target_type_id": created["Order"], "cardinality": "one-to-many",
        })
        print("  Linked Customer -> Order")

    if "Order" in created and "Product" in created:
        requests.post(f"{API_URL}/api/v1/ontology/types/{created['Order']}/links", json={
            "name": "contains_product", "target_type_id": created["Product"], "cardinality": "many-to-one",
        })
        print("  Linked Order -> Product")

    return created


def ch_exec(sql: str):
    resp = requests.post(
        CH_URL,
        params={"user": CH_USER, "password": CH_PASSWORD},
        data=sql,
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(resp.text.strip())


def seed_clickhouse():
    print("\nLoading sample data into ClickHouse...")
    try:
        ch_exec("SELECT 1")
    except Exception as e:
        print(f"  SKIPPED: cannot reach ClickHouse ({e})")
        return

    tables = [
        (
            "customers",
            """CREATE TABLE IF NOT EXISTS odp.customers (
                id       UInt32,
                name     String,
                email    String,
                country  String,
                created_at Date
            ) ENGINE = MergeTree() ORDER BY id""",
            [
                (1, 'Alice Johnson',  'alice@example.com',   'USA',       '2024-01-15'),
                (2, 'Bob Smith',      'bob@example.com',     'UK',        '2024-02-20'),
                (3, 'Charlie Brown',  'charlie@example.com', 'Canada',    '2024-03-10'),
                (4, 'Diana Prince',   'diana@example.com',   'USA',       '2024-04-05'),
                (5, 'Eve Wilson',     'eve@example.com',     'Germany',   '2024-05-12'),
                (6, 'Frank Castle',   'frank@example.com',   'USA',       '2024-06-01'),
                (7, 'Grace Lee',      'grace@example.com',   'Japan',     '2024-06-15'),
                (8, 'Hank Pym',       'hank@example.com',    'UK',        '2024-07-22'),
                (9, 'Iris West',      'iris@example.com',    'Canada',    '2024-08-30'),
                (10,'Jack Reacher',   'jack@example.com',    'Australia', '2024-09-14'),
            ],
        ),
        (
            "products",
            """CREATE TABLE IF NOT EXISTS odp.products (
                id        UInt32,
                name      String,
                category  String,
                price     Float64,
                stock     UInt32,
                created_at Date
            ) ENGINE = MergeTree() ORDER BY id""",
            [
                (1, 'Widget Pro',  'Electronics', 29.99,  150, '2024-01-01'),
                (2, 'Gadget Plus', 'Electronics', 29.99,  200, '2024-01-15'),
                (3, 'SuperTool X', 'Tools',       149.99,  75, '2024-02-01'),
                (4, 'MegaDevice',  'Electronics', 199.99,  50, '2024-03-01'),
                (5, 'UltraGear',   'Premium',     399.99,  25, '2024-04-01'),
            ],
        ),
        (
            "orders",
            """CREATE TABLE IF NOT EXISTS odp.orders (
                id           UInt32,
                customer_id  UInt32,
                product_id   UInt32,
                quantity     UInt32,
                total_amount Float64,
                status       String,
                order_date   Date
            ) ENGINE = MergeTree() ORDER BY id""",
            [
                (1,  1, 1, 2,  59.98,  'completed',  '2024-03-01'),
                (2,  1, 3, 1,  149.99, 'completed',  '2024-04-15'),
                (3,  2, 2, 1,  29.99,  'completed',  '2024-03-20'),
                (4,  3, 1, 3,  89.97,  'completed',  '2024-05-10'),
                (5,  4, 4, 1,  199.99, 'shipped',    '2024-06-01'),
                (6,  5, 2, 2,  59.98,  'completed',  '2024-06-20'),
                (7,  6, 3, 1,  149.99, 'processing', '2024-07-05'),
                (8,  7, 5, 1,  399.99, 'completed',  '2024-07-18'),
                (9,  8, 1, 1,  29.99,  'shipped',    '2024-08-01'),
                (10, 9, 4, 2,  399.98, 'completed',  '2024-08-15'),
                (11,10, 2, 3,  89.97,  'completed',  '2024-09-01'),
                (12, 1, 5, 1,  399.99, 'processing', '2024-09-20'),
                (13, 3, 3, 2,  299.98, 'completed',  '2024-10-05'),
                (14, 5, 1, 4,  119.96, 'shipped',    '2024-10-25'),
                (15, 7, 4, 1,  199.99, 'completed',  '2024-11-10'),
            ],
        ),
    ]

    for table_name, create_sql, rows in tables:
        try:
            ch_exec(create_sql)
            # Only insert if table is empty (idempotent)
            result = requests.post(
                CH_URL,
                params={"user": CH_USER, "password": CH_PASSWORD,
                        "query": f"SELECT count() FROM odp.{table_name}"},
                timeout=5,
            )
            if result.ok and result.text.strip() != "0":
                print(f"  {table_name}: already has data, skipping insert")
                continue
            vals = ", ".join(str(r) for r in rows)
            ch_exec(f"INSERT INTO odp.{table_name} VALUES {vals}")
            print(f"  {table_name}: {len(rows)} rows loaded into ClickHouse")
        except Exception as e:
            print(f"  {table_name}: FAILED ({e})")


def create_sample_pipeline():
    print("\nCreating sample pipeline...")
    resp = requests.post(f"{API_URL}/api/v1/pipelines", json={
        "name": "Sample ETL Pipeline",
        "description": "Load CSV data, transform, and output to ClickHouse",
        "pipeline_type": "dbt",
    })
    if resp.status_code == 200:
        data = resp.json()
        print(f"  Created pipeline: {data['name']} ({data['id']})")
        return data
    else:
        print(f"  FAILED: {resp.text}")
        return None


def main():
    print("=" * 50)
    print("ODP - Data Seeder")
    print("=" * 50)

    try:
        health = requests.get(f"{API_URL}/health", timeout=5)
        print(f"\nAPI Status: {health.json()['status']}")
    except Exception as e:
        print(f"\nERROR: Cannot reach API at {API_URL}")
        print(f"  {e}")
        print("  Make sure the platform is running: make up")
        sys.exit(1)

    print("\nUploading sample datasets...")
    for filename in sorted(os.listdir(SAMPLE_DIR)):
        if filename.endswith((".csv", ".json")):
            upload_file(os.path.join(SAMPLE_DIR, filename))

    create_ontology_types()
    seed_clickhouse()
    create_sample_pipeline()

    print("\n" + "=" * 50)
    print("Seeding complete!")
    print(f"  UI: http://localhost:3000")
    print(f"  API: {API_URL}/docs")
    print("=" * 50)


if __name__ == "__main__":
    main()
