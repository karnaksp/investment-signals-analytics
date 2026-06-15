import os
import subprocess
from pathlib import Path

from dagster import AssetExecutionContext, Definitions, ScheduleDefinition, asset, define_asset_job


DBT_PROJECT_DIR = Path(os.getenv("DBT_PROJECT_DIR", "/workspace")).resolve()
DBT_PROFILES_DIR = Path(os.getenv("DBT_PROFILES_DIR", str(DBT_PROJECT_DIR))).resolve()
DBT_TARGET = os.getenv("DBT_TARGET", "investment_signals")


def _run(command: list[str], context: AssetExecutionContext) -> None:
    context.log.info("Запускаю: %s", " ".join(command))
    result = subprocess.run(
        command,
        cwd=DBT_PROJECT_DIR,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        context.log.info(result.stdout)
    if result.stderr:
        context.log.warning(result.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"Команда завершилась с кодом {result.returncode}: {' '.join(command)}")


@asset(
    name="investment_signals_dbt_marts",
    description=(
        "Пересчитывает dbt-витрины над live-таблицей investment-signals: "
        "рабочий список сигналов и качество типов сигналов."
    ),
)
def investment_signals_dbt_marts(context: AssetExecutionContext) -> None:
    _run(
        [
            "dbt",
            "build",
            "--project-dir",
            str(DBT_PROJECT_DIR),
            "--profiles-dir",
            str(DBT_PROFILES_DIR),
            "--target",
            DBT_TARGET,
        ],
        context,
    )


investment_signals_refresh_job = define_asset_job(
    name="investment_signals_refresh_job",
    selection=[investment_signals_dbt_marts],
    description="Обновляет аналитические витрины для сигналов из investment-signals.",
)

investment_signals_refresh_schedule = ScheduleDefinition(
    name="investment_signals_refresh_every_15_minutes",
    job=investment_signals_refresh_job,
    cron_schedule="*/15 * * * *",
)

defs = Definitions(
    assets=[investment_signals_dbt_marts],
    jobs=[investment_signals_refresh_job],
    schedules=[investment_signals_refresh_schedule],
)
