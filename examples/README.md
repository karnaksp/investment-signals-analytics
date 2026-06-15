# dbt-af Tutorial

## Quick Start
### Prerequisites
1. Running instance of Airflow. There are a few ways to get this. The easiest is to use the Docker Compose to get a local instance running. See [docs](using_docker_compose.md) for more information.
2. Install `dbt-af` if you are not using the Docker Compose method.
    - via pip: `pip install dbt-af[tests,examples]`
3. Build dbt manifest. You can use the provided [script](./dags/build_manifest.sh) to build the manifest.
    ```bash
    cd examples/dags
    ./build_manifest.sh
    ```
4. Add `dbt_dev` and `dbt_sensor_pool` [pools](https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/pools.html) to Airflow.
   The Docker Compose demo creates both pools automatically in `airflow-init`.

    - By using Airflow UI ![Airflow Pools](../docs/static/add_new_af_pool.png)
    - By using Airflow CLI:
      `airflow pools set dbt_dev 4 "dev"` and `airflow pools set dbt_sensor_pool 4 "sensor"`

    Start with some small numbers of open slots in pools. 
    If you are using your local machine, a large number of tasks can overflow your machine's resources.

5. To run the local orchestration smoke, use [Running Airflow with Docker](using_docker_compose.md).

## List of Examples
1. [Basic Project](basic_project.md): a single domain, small tests, and a single target.
2. [Advanced Project](advanced_project.md): several domains, medium and large tests, and different targets.
3. [Dependencies management](dependencies_management.md): how to manage dependencies between models in different domains.
4. [Manual scheduling](manual_scheduling.md): domains with manual scheduling.
5. [Maintenance and source freshness](maintenance_and_source_freshness.md): how to manage maintenance tasks and source freshness.
6. [Python Venv Tasks](python_venv_tasks.md): how to run custom dbt models in Python Virtual Environments.
7. [Kubernetes tasks](kubernetes_tasks.md): how to run dbt models in Kubernetes.
8. [Integration with other tools](integration_with_other_tools.md): how to integrate dbt-af with other tools.
9. [\[Preview\] Extras and scripts](extras_and_scripts.md): available extras and scripts.
10. [investment-signals analytics](dags/investment_signals_analytics/README.md): локальный стенд для анализа качества и пользы рыночных сигналов. Поддерживает автономный запуск на seed-данных и связанный запуск поверх Postgres из `investment-signals`.

## Аналитический контур investment-signals

Рабочий dbt/Dagster/Lightdash контур вынесен в корень репозитория:

- `../analytics/investment_signals_dbt` - dbt-модели и Lightdash dashboard-as-code;
- `../analytics/dagster` - Dagster job и schedule;
- `../docker-compose.yml` - локальный запуск dbt, Dagster, Lightdash, MinIO и Lightdash Postgres.

Основной запуск описан в [корневом README](../README.md). Директория `examples` остается для Airflow-сценариев и
smoke-проверок orchestration path.

### Как добавить новую аналитику

1. Добавить dbt-модель в `../analytics/investment_signals_dbt/models`.
2. Описать модель, колонки, тесты и метрики в `../analytics/investment_signals_dbt/models/schema.yml`.
3. Добавить SQL chart в `../analytics/investment_signals_dbt/lightdash/charts`.
4. Добавить tile в `../analytics/investment_signals_dbt/lightdash/dashboards/investment-signals-operations.yml`.
5. Выполнить deploy из корня репозитория:

```bash
docker compose --profile lightdash --profile deploy run --rm lightdash-deploy
```

### Сигналы T-Invest

Связанный запуск с `investment-signals` обновляет итоговые dbt-таблицы в Postgres
репозитория `investment-signals`, в схеме `investment_signals_analytics`.

```bash
cd ../dbt-af
./examples/run_linked_investment_signals_analytics.sh
```

После этого данные доступны в Lightdash после обновления проекта.

Статический HTML-снапшот можно собрать отдельно:

```bash
python examples/build_investment_signals_dashboard.py
```

По умолчанию файл появится здесь:

```text
outputs/investment_signals_marts_dashboard.html
```

Для просмотра через браузер:

```bash
cd outputs
python -m http.server 18082 --bind 127.0.0.1
```

Открыть:

```text
http://127.0.0.1:18082/investment_signals_marts_dashboard.html
```

Отдельного постоянно работающего контейнера `dbt` в этом сценарии нет. dbt запускается
одноразовой командой внутри compose-образа Airflow, обновляет модели и завершается.
Постоянно работают контейнеры Airflow, Postgres и Redis; Airflow UI доступен на
`http://localhost:18080`.
