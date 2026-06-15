from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


REQUIRED_CHART_KEYS = {'contentType', 'name', 'sql', 'chartKind', 'config', 'slug', 'spaceSlug'}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding='utf-8') as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError(f'{path}: ожидался YAML object')
    return data


def validate_table_config(path: Path, chart: dict[str, Any]) -> None:
    if chart.get('chartKind') != 'table':
        return

    config = chart.get('config')
    if not isinstance(config, dict):
        raise ValueError(f'{path}: config должен быть object')
    if config.get('type') != 'table':
        raise ValueError(f'{path}: для chartKind=table нужен config.type=table')

    columns = config.get('columns')
    if not isinstance(columns, dict) or not columns:
        raise ValueError(f'{path}: table chart должен описывать config.columns')

    for column_name, column_config in columns.items():
        if not isinstance(column_config, dict):
            raise ValueError(f'{path}: config.columns.{column_name} должен быть object')
        for key in ('visible', 'reference', 'label', 'frozen', 'order'):
            if key not in column_config:
                raise ValueError(f'{path}: config.columns.{column_name} без обязательного поля {key}')
        if column_config['reference'] != column_name:
            raise ValueError(f'{path}: reference для {column_name} должен совпадать с именем колонки')


def validate_assets(root: Path) -> None:
    chart_dir = root / 'charts'
    dashboard_dir = root / 'dashboards'
    if not chart_dir.is_dir():
        raise ValueError(f'Не найдена директория чартов: {chart_dir}')
    if not dashboard_dir.is_dir():
        raise ValueError(f'Не найдена директория дашбордов: {dashboard_dir}')

    chart_slugs: set[str] = set()
    for chart_path in sorted(chart_dir.glob('*.yml')):
        chart = load_yaml(chart_path)
        missing = REQUIRED_CHART_KEYS - set(chart)
        if missing:
            raise ValueError(f'{chart_path}: не хватает полей {sorted(missing)}')
        if chart.get('contentType') != 'sql_chart':
            raise ValueError(f'{chart_path}: поддерживается только contentType=sql_chart')
        slug = chart.get('slug')
        if not isinstance(slug, str) or not slug:
            raise ValueError(f'{chart_path}: slug должен быть непустой строкой')
        if slug in chart_slugs:
            raise ValueError(f'{chart_path}: повторяющийся slug {slug}')
        chart_slugs.add(slug)
        validate_table_config(chart_path, chart)

    for dashboard_path in sorted(dashboard_dir.glob('*.yml')):
        dashboard = load_yaml(dashboard_path)
        tiles = dashboard.get('tiles')
        if not isinstance(tiles, list) or not tiles:
            raise ValueError(f'{dashboard_path}: dashboard должен содержать tiles')
        for index, tile in enumerate(tiles):
            if not isinstance(tile, dict):
                raise ValueError(f'{dashboard_path}: tile #{index} должен быть object')
            if tile.get('type') != 'sql_chart':
                continue
            properties = tile.get('properties')
            if not isinstance(properties, dict):
                raise ValueError(f'{dashboard_path}: sql tile #{index} без properties')
            chart_slug = properties.get('chartSlug')
            if chart_slug not in chart_slugs:
                raise ValueError(f'{dashboard_path}: tile #{index} ссылается на неизвестный chartSlug={chart_slug}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Проверяет Lightdash dashboard-as-code.')
    parser.add_argument(
        'root',
        nargs='?',
        default='analytics/investment_signals_dbt/lightdash',
        type=Path,
        help='Директория Lightdash assets.',
    )
    args = parser.parse_args()
    validate_assets(args.root)


if __name__ == '__main__':
    main()
