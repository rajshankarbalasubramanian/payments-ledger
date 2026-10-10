.PHONY: ci-run migrate seed docker-up docker-down test

docker-up:
    docker compose up -d --build

docker-down:
    docker compose down --volumes --remove-orphans

migrate:
    python3 api/src/migrate_sqlite.py

seed:
    python3 seed/seed_sqlite.py --small

test:
    pytest -q

ci-run: docker-up migrate seed test docker-down
