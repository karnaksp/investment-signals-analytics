.PHONY: compose-check dbt-build dagster-up lightdash-up lightdash-health lightdash-validate lightdash-deploy stack-status qa

compose-check:
	docker compose config --quiet

dbt-build:
	docker compose run --rm dbt

dagster-up:
	docker compose up -d dagster

lightdash-up:
	docker compose --profile lightdash up -d lightdash

lightdash-health:
	curl -fsS http://localhost:$${LIGHTDASH_HOST_PORT:-18083}/api/v1/health

lightdash-validate:
	docker run --rm -v "$$(pwd)":/repo -w /repo python:3.11-slim sh -lc 'pip install --quiet pyyaml==6.0.2 && python scripts/validate_lightdash_assets.py analytics/investment_signals_dbt/lightdash'

lightdash-deploy:
	docker compose --profile lightdash --profile deploy run --rm lightdash-deploy

stack-status:
	docker compose --profile lightdash ps

qa: compose-check dbt-build lightdash-validate lightdash-health
