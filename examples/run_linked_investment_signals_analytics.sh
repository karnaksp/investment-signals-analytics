#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INVESTMENT_SIGNALS_REPO="${INVESTMENT_SIGNALS_REPO:-${REPO_ROOT}/../investment-signals}"

INVESTMENT_SIGNALS_POSTGRES_HOST="${INVESTMENT_SIGNALS_POSTGRES_HOST:-host.docker.internal}"
INVESTMENT_SIGNALS_POSTGRES_PORT="${INVESTMENT_SIGNALS_POSTGRES_PORT:-35432}"
INVESTMENT_SIGNALS_POSTGRES_DB="${INVESTMENT_SIGNALS_POSTGRES_DB:-signal_engine}"
INVESTMENT_SIGNALS_POSTGRES_USER="${INVESTMENT_SIGNALS_POSTGRES_USER:-signal_engine}"
INVESTMENT_SIGNALS_POSTGRES_PASSWORD="${INVESTMENT_SIGNALS_POSTGRES_PASSWORD:-signal_engine}"
INVESTMENT_SIGNALS_POSTGRES_SCHEMA="${INVESTMENT_SIGNALS_POSTGRES_SCHEMA:-investment_signals_analytics}"

DBT_AF_POSTGRES_HOST_PORT="${DBT_AF_POSTGRES_HOST_PORT:-15432}"
DBT_AF_AIRFLOW_WEBSERVER_HOST_PORT="${DBT_AF_AIRFLOW_WEBSERVER_HOST_PORT:-18080}"

if [[ ! -f "${INVESTMENT_SIGNALS_REPO}/docker-compose.yml" ]]; then
  echo "Не найден docker-compose.yml investment-signals: ${INVESTMENT_SIGNALS_REPO}" >&2
  exit 1
fi

if [[ ! -f "${INVESTMENT_SIGNALS_REPO}/.env" && -f "${INVESTMENT_SIGNALS_REPO}/.env.example" ]]; then
  cp "${INVESTMENT_SIGNALS_REPO}/.env.example" "${INVESTMENT_SIGNALS_REPO}/.env"
  echo "Создан ${INVESTMENT_SIGNALS_REPO}/.env из .env.example для docker compose."
fi

echo "1/6 Поднимаю Postgres из investment-signals..."
docker compose -f "${INVESTMENT_SIGNALS_REPO}/docker-compose.yml" up -d postgres

echo "2/6 Жду готовности signal_engine..."
for attempt in {1..60}; do
  if docker compose -f "${INVESTMENT_SIGNALS_REPO}/docker-compose.yml" exec -T postgres \
    pg_isready -U "${INVESTMENT_SIGNALS_POSTGRES_USER}" -d "${INVESTMENT_SIGNALS_POSTGRES_DB}" >/dev/null 2>&1; then
    break
  fi
  if [[ "${attempt}" == "60" ]]; then
    echo "Postgres investment-signals не стал готовым за 60 попыток." >&2
    exit 1
  fi
  sleep 2
done

echo "3/6 Добавляю контрольные сигналы в live-таблицу..."
docker compose -f "${INVESTMENT_SIGNALS_REPO}/docker-compose.yml" exec -T postgres \
  psql -v ON_ERROR_STOP=1 \
  -U "${INVESTMENT_SIGNALS_POSTGRES_USER}" \
  -d "${INVESTMENT_SIGNALS_POSTGRES_DB}" <<'SQL'
insert into market_signals (
    signal_id,
    detected_at,
    instrument_id,
    ticker,
    class_code,
    alias,
    source_event_type,
    signal_type,
    severity,
    metric_value,
    baseline_value,
    z_score,
    window_seconds,
    summary,
    payload_json
) values
(
    '11111111-1111-1111-1111-111111111111',
    now() - interval '4 minutes',
    'TQBR:SBER',
    'SBER',
    'TQBR',
    'SBER',
    'last_price',
    'price_jump',
    3,
    285.40,
    277.10,
    8.50,
    300,
    'SBER резко отклонился от краткосрочного базового уровня.',
    '{"quality_score": 92, "delivery_status": "delivered", "delivery_reason": "high_quality_realtime_signal", "delivery_rule": "realtime", "delivery_channel": "telegram"}'::jsonb
),
(
    '22222222-2222-2222-2222-222222222222',
    now() - interval '9 minutes',
    'TQBR:GAZP',
    'GAZP',
    'TQBR',
    'GAZP',
    'last_price',
    'volume_spike',
    3,
    184.20,
    176.50,
    7.20,
    300,
    'GAZP дал сильный всплеск объема, но правило доставки ограничило сигнал.',
    '{"quality_score": 88, "delivery_status": "suppressed", "delivery_reason": "risk_rule_cooldown", "delivery_rule": "cooldown", "delivery_channel": "none"}'::jsonb
),
(
    '33333333-3333-3333-3333-333333333333',
    now() - interval '16 minutes',
    'TQBR:LKOH',
    'LKOH',
    'TQBR',
    'LKOH',
    'last_price',
    'trend_break',
    2,
    7210.00,
    7145.00,
    4.40,
    600,
    'LKOH вышел за границу внутридневного тренда.',
    '{"quality_score": 71, "delivery_status": "suppressed", "delivery_reason": "manual_review_required", "delivery_rule": "manual_review", "delivery_channel": "admin_only"}'::jsonb
),
(
    '44444444-4444-4444-4444-444444444444',
    now() - interval '24 minutes',
    'TQBR:MOEX',
    'MOEX',
    'TQBR',
    'MOEX',
    'last_price',
    'minor_move',
    1,
    219.10,
    218.90,
    1.10,
    300,
    'MOEX дал слабое отклонение без торгового смысла.',
    '{"quality_score": 42, "delivery_status": "suppressed", "delivery_reason": "low_quality", "delivery_rule": "quality_gate", "delivery_channel": "none"}'::jsonb
)
on conflict (signal_id) do update set
    detected_at = excluded.detected_at,
    metric_value = excluded.metric_value,
    baseline_value = excluded.baseline_value,
    z_score = excluded.z_score,
    summary = excluded.summary,
    payload_json = excluded.payload_json;
SQL

echo "4/6 Запускаю dbt-af против Postgres из investment-signals..."
POSTGRES_HOST_PORT="${DBT_AF_POSTGRES_HOST_PORT}" \
AIRFLOW_WEBSERVER_HOST_PORT="${DBT_AF_AIRFLOW_WEBSERVER_HOST_PORT}" \
docker compose -f "${SCRIPT_DIR}/docker-compose.yaml" up -d postgres redis

POSTGRES_HOST_PORT="${DBT_AF_POSTGRES_HOST_PORT}" \
AIRFLOW_WEBSERVER_HOST_PORT="${DBT_AF_AIRFLOW_WEBSERVER_HOST_PORT}" \
docker compose -f "${SCRIPT_DIR}/docker-compose.yaml" run --rm \
  -e INVESTMENT_SIGNALS_POSTGRES_HOST="${INVESTMENT_SIGNALS_POSTGRES_HOST}" \
  -e INVESTMENT_SIGNALS_POSTGRES_PORT="${INVESTMENT_SIGNALS_POSTGRES_PORT}" \
  -e INVESTMENT_SIGNALS_POSTGRES_DB="${INVESTMENT_SIGNALS_POSTGRES_DB}" \
  -e INVESTMENT_SIGNALS_POSTGRES_USER="${INVESTMENT_SIGNALS_POSTGRES_USER}" \
  -e INVESTMENT_SIGNALS_POSTGRES_PASSWORD="${INVESTMENT_SIGNALS_POSTGRES_PASSWORD}" \
  -e INVESTMENT_SIGNALS_POSTGRES_SCHEMA="${INVESTMENT_SIGNALS_POSTGRES_SCHEMA}" \
  airflow-cli bash -lc "
    cd /opt/airflow/dags
    dbt build \
      --no-partial-parse \
      --project-dir /opt/airflow/dags \
      --profiles-dir /opt/airflow/dags \
      --target investment_signals \
      --select svc_investment_signals_live+
  "

echo "5/6 Проверяю итоговую витрину в базе investment-signals..."
docker compose -f "${INVESTMENT_SIGNALS_REPO}/docker-compose.yml" exec -T postgres \
  psql -v ON_ERROR_STOP=1 \
  -U "${INVESTMENT_SIGNALS_POSTGRES_USER}" \
  -d "${INVESTMENT_SIGNALS_POSTGRES_DB}" \
  -c "select ticker, signal_type, trading_decision, decision_score, quality_score, delivery_status, decision_reason from ${INVESTMENT_SIGNALS_POSTGRES_SCHEMA}.\"svc_investment_signals_live.mart_live_trading_watchlist\" order by decision_score desc, detected_at desc;"

echo "6/6 Собираю HTML-витрину итоговых мартов..."
python "${SCRIPT_DIR}/build_investment_signals_dashboard.py" \
  --investment-repo "${INVESTMENT_SIGNALS_REPO}" \
  --output "${REPO_ROOT}/outputs/investment_signals_marts_dashboard.html"

echo "Связка investment-signals -> dbt-af работает."
echo "HTML-витрина: ${REPO_ROOT}/outputs/investment_signals_marts_dashboard.html"
