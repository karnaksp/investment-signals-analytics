# Running Airflow with Docker

Use this path when you want to verify that the example dbt project compiles into Airflow DAGs and that the manual
`dbt_af_project_dbt_run_model` DAG is discoverable.

## One-command smoke

```bash
cd examples
./smoke_orchestration.sh
```

The smoke script runs:

1. `docker compose config --quiet`
2. containerized `dbt clean`, `dbt deps`, and `dbt parse` to build the manifest
3. `docker compose up --force-recreate -d --build`
4. Airflow webserver health check
5. `airflow pools list`
6. `airflow dags list`
7. `airflow tasks list dbt_af_project_dbt_run_model`

If your machine already uses `8080` or `5432`, override only the host ports:

```bash
AIRFLOW_WEBSERVER_HOST_PORT=18080 POSTGRES_HOST_PORT=15432 ./smoke_orchestration.sh
```

## Manual run

If you already have `dbt` installed locally, you can build the manifest directly:

```bash
cd examples/dags
./build_manifest.sh
```

Then start the Airflow stack:

```bash
cd ..
docker compose up --force-recreate -d --build
docker compose ps
docker compose exec airflow-webserver airflow dags list
docker compose exec airflow-webserver airflow tasks list dbt_af_project_dbt_run_model
```

The `airflow-init` service runs database migrations and creates the required `dbt_dev` and `dbt_sensor_pool` pools.

## Stop and clean up

```bash
docker compose down --volumes --remove-orphans
```
