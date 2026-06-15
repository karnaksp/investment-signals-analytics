# Lightdash для investment-signals

Актуальный Lightdash-контур запускается из корня репозитория через `docker-compose.yml`.
Эта директория оставлена для совместимости со старыми Airflow-примерами; для рабочего продукта используйте
конфигурацию в `analytics/investment_signals_dbt/lightdash`.

## Основной запуск

```bash
cp .env.example .env
docker compose run --rm dbt
docker compose --profile lightdash up -d lightdash
```

Открыть Lightdash:

```text
http://localhost:18083
```

## Deploy dashboard-as-code

После создания пользователя в Lightdash создайте Personal Access Token и заполните:

```dotenv
LIGHTDASH_API_KEY=...
LIGHTDASH_PROJECT=...
```

Затем выполните:

```bash
docker compose --profile lightdash --profile deploy run --rm lightdash-deploy
```

Команда загрузит:

- space `Investment Signals Analytics`;
- dashboard `Операционный обзор сигналов`;
- ключевые показатели и диагностические SQL-чарты;
- detail-таблицы для ручной проверки сигналов.

## Где лежит код дашборда

```text
analytics/investment_signals_dbt/lightdash
├── .space.yml
├── charts
└── dashboards
```

Все SQL-чарты используют технические имена колонок в SQL и русские подписи в `config.columns`.
Это важно для Lightdash: неполный table config приводит к пустым таблицам или ошибкам отрисовки.

## Как добавлять новые панели

1. Добавить или изменить dbt-модель в `analytics/investment_signals_dbt/models`.
2. Описать модель, тесты и метрики в `schema.yml`.
3. Добавить SQL chart в `analytics/investment_signals_dbt/lightdash/charts`.
4. Добавить tile в `analytics/investment_signals_dbt/lightdash/dashboards/investment-signals-operations.yml`.
5. Выполнить `docker compose --profile lightdash --profile deploy run --rm lightdash-deploy`.
