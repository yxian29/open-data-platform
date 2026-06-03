#!/usr/bin/env python3
"""Seed script: uploads sample data to the Open Data Platform."""

import os
import sys
import requests

API_URL = os.getenv("API_URL", "http://localhost:8000")
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
    create_sample_pipeline()

    print("\n" + "=" * 50)
    print("Seeding complete!")
    print(f"  UI: http://localhost:3000")
    print(f"  API: {API_URL}/docs")
    print("=" * 50)


if __name__ == "__main__":
    main()
