# dbt-af Reliability Contribution Case Study

## Status

This repository is a fork of `Toloka/dbt-af`. I use this fork as a focused open-source reliability contribution case,
not as a claim of ownership over the original project.

The current contribution has two parts: it hardens the manual `<dbt_project_name>_dbt_run_model` Airflow DAG so empty
or default Extra Arguments do not break manual dbt runs, and it makes the local Docker Compose example usable as a
reproducible orchestration smoke demo.

## Problem

`dbt-af` can generate a manual DAG named `<dbt_project_name>_dbt_run_model`. Data engineers use it to rerun one model,
backfill a specific interval, or validate a new model without waiting for the regular schedule.

The manual trigger form includes an **Extra Arguments** field for optional dbt CLI flags. In practice, users often leave
this field unchanged, clear it to `{}`, or submit `null` through the Airflow UI/API. That path should behave like
"no extra options", while real custom dbt options should still pass through.

## My Contribution

- Fixed `build_dbt_run_model_bash_extra_options` so `None`, `{}`, and the default placeholder are ignored.
- Preserved custom options such as `{"profiles-dir": "/tmp/profiles", "--option": "custom-value"}`.
- Added regression coverage for empty/default input and custom dbt CLI options.
- Documented the manual DAG behavior in the main configuration docs and the basic project example.
- Fixed the Docker Compose demo bootstrap so Airflow initialization reaches database migration and pool creation.
- Added a local smoke script that builds the dbt manifest, starts Airflow, checks DAG discovery, and verifies the manual
  `dbt_af_project_dbt_run_model` task list.

## Demo Scenario

1. Open the generated `<dbt_project_name>_dbt_run_model` DAG in Airflow.
2. Fill `Model Selector`, `Interval Start Datetime`, and `Interval End Datetime`.
3. Leave **Extra Arguments** unchanged, clear it to `{}`, or submit it as `null`.
4. Trigger the DAG.
5. Expected behavior: the dbt command is built without extra CLI options and does not fail while iterating over empty
   optional arguments.
6. Add custom JSON only when needed:

```json
{
  "profiles-dir": "/tmp/profiles",
  "--option": "custom-value"
}
```

Expected command behavior: both keys are normalized into dbt CLI options, including the missing `--` prefix for
`profiles-dir`.

## Validation

Focused local check:

```bash
poetry run pytest -q tests/test_common_utils.py
```

Docker Compose demo check:

```bash
docker compose -f examples/docker-compose.yaml config --quiet
cd examples && ./smoke_orchestration.sh
```

Full project check used by CI:

```bash
poetry run pytest -q -s -vv --log-cli-level=INFO --cov=dbt_af --cov-report=term --run-airflow-tasks tests
ruff check
```

## Portfolio Role

This repository is now useful as a secondary Data Engineering portfolio case: it shows an open-source reliability fix
plus a reproducible Airflow/dbt orchestration demo. Keep it below production projects, but it no longer needs to be
hidden as a one-off bugfix fork.
