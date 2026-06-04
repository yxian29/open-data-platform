.PHONY: up down restart logs ps seed test clean

# Copy .env from example if it doesn't exist
.env:
	cp .env.example .env

up: .env
	docker compose up -d --build

down:
	docker compose down

restart:
	docker compose down && docker compose up -d --build

logs:
	docker compose logs -f

ps:
	docker compose ps

seed:
	@echo "Seeding sample data..."
	python3 examples/seed.py

test:
	@echo "Running API Gateway tests..."
	cd services/api-gateway && python -m pytest tests/ -v
	@echo "Running Ontology Service tests..."
	cd services/ontology && python -m pytest tests/ -v

clean:
	docker compose down -v
	@echo "All volumes removed."

# Individual service logs
logs-api:
	docker compose logs -f api-gateway

logs-ontology:
	docker compose logs -f ontology-service

logs-pipelines:
	docker compose logs -f pipeline-service

logs-dagster:
	docker compose logs -f dagster-webserver dagster-daemon

# Database access shortcuts
psql:
	docker compose exec postgres psql -U odp -d odp

neo4j-shell:
	docker compose exec neo4j cypher-shell -u neo4j -p neo4j_secret

clickhouse-client:
	docker compose exec clickhouse clickhouse-client --password clickhouse_secret

# Phase 2 services
logs-audit:
	docker compose logs -f audit-service

# Phase 3 — AI layer
ai-bridge:
	@echo "Starting Claude CLI bridge on :9999 (keep this terminal open)"
	python3 claude-bridge.py

logs-ai:
	docker compose logs -f ai-service
