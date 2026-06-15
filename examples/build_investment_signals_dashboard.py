"""Собирает HTML-витрину по dbt-мартам investment-signals.

Скрипт не требует Python-зависимостей: данные забираются через psql внутри
контейнера Postgres из соседнего репозитория investment-signals.
"""

from __future__ import annotations

import argparse
import html
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVESTMENT_REPO = ROOT.parent / "investment-signals"
WATCHLIST_TABLE = (
    'investment_signals_analytics."svc_investment_signals_live.mart_live_trading_watchlist"'
)
QUALITY_TABLE = (
    'investment_signals_analytics."svc_investment_signals_live.mart_signal_type_quality"'
)


def _run_json_query(repo: Path, query: str) -> list[dict[str, Any]]:
    wrapped = f"select coalesce(json_agg(row_to_json(q)), '[]'::json) from ({query}) q;"
    cmd = [
        "docker",
        "compose",
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        "signal_engine",
        "-d",
        "signal_engine",
        "-t",
        "-A",
        "-c",
        wrapped,
    ]
    result = subprocess.run(
        cmd,
        cwd=repo,
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout.strip() or "[]")


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _num(value: Any, digits: int = 0) -> str:
    if value is None:
        return "0"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _esc(value)
    if digits == 0:
        return f"{number:,.0f}".replace(",", " ")
    return f"{number:,.{digits}f}".replace(",", " ")


def _bar(width: float, class_name: str = "") -> str:
    bounded = max(0.0, min(100.0, width))
    return f'<span class="bar {class_name}"><i style="width:{bounded:.1f}%"></i></span>'


def _decision_label(value: str) -> str:
    labels = {
        "кандидат": "Кандидат",
        "наблюдать": "Наблюдать",
        "заблокировать_политикой": "Ограничено правилом",
        "пропустить": "Пропустить",
    }
    return labels.get(value, value)


def _signal_type_label(value: str) -> str:
    labels = {
        "price_jump": "Скачок цены",
        "volume_spike": "Всплеск объема",
        "trend_break": "Пробой тренда",
        "minor_move": "Слабое движение",
        "trading_status_changed": "Смена торгового статуса",
    }
    return labels.get(value, value.replace("_", " "))


def _status_label(value: str) -> str:
    labels = {
        "delivered": "Доставлен",
        "suppressed": "Подавлен",
        "unknown": "Неизвестно",
    }
    return labels.get(value, value)


def _reason_label(value: Any) -> str:
    text = "" if value is None else str(value)
    labels = {
        "high_quality_realtime_signal": "сильный сигнал отправлен сразу",
        "risk_rule_cooldown": "ограничение по частоте уведомлений",
        "manual_review_required": "нужна ручная проверка",
        "low_quality": "низкое качество",
        "status_or_access_change": "изменился режим торгов или доступ",
    }
    return labels.get(text, text.replace("_", " "))


def _status_text(value: Any) -> str:
    return ("" if value is None else str(value)).replace("_", " ")


def _watchlist_rows(rows: list[dict[str, Any]]) -> str:
    rendered: list[str] = []
    for row in rows:
        decision = str(row.get("trading_decision") or "")
        delivery = str(row.get("delivery_status") or "")
        decision_cls = {
            "кандидат": "good",
            "наблюдать": "watch",
            "заблокировать_политикой": "blocked",
            "пропустить": "muted",
        }.get(decision, "muted")
        delivery_cls = "good" if delivery == "delivered" else "blocked"
        rendered.append(
            "<tr>"
            f"<td><strong>{_esc(row.get('ticker'))}</strong><span>{_esc(_signal_type_label(str(row.get('signal_type') or '')))}</span></td>"
            f"<td><b class='pill {decision_cls}'>{_esc(_decision_label(decision))}</b></td>"
            f"<td>{_bar(float(row.get('decision_score') or 0), decision_cls)}<small>{_num(row.get('decision_score'), 1)}</small></td>"
            f"<td>{_bar(float(row.get('quality_score') or 0), 'quality')}<small>{_num(row.get('quality_score'))}</small></td>"
            f"<td><b class='pill {delivery_cls}'>{_esc(_status_label(delivery))}</b><span>{_esc(_reason_label(row.get('delivery_reason')))}</span></td>"
            f"<td>{_esc(row.get('decision_reason'))}</td>"
            "</tr>"
        )
    return "\n".join(rendered)


def _quality_rows(rows: list[dict[str, Any]]) -> str:
    rendered: list[str] = []
    for row in rows:
        delivered_ratio = float(row.get("delivered_ratio") or 0) * 100
        rendered.append(
            "<tr>"
            f"<td><strong>{_esc(row.get('ticker'))}</strong><span>{_esc(_signal_type_label(str(row.get('signal_type') or '')))}</span></td>"
            f"<td>{_num(row.get('signal_count'))}</td>"
            f"<td>{_num(row.get('delivered_count'))}</td>"
            f"<td>{_bar(delivered_ratio, 'good')}<small>{_num(delivered_ratio, 0)}%</small></td>"
            f"<td>{_num(row.get('avg_quality_score'), 1)}</td>"
            f"<td>{_esc(_status_text(row.get('quality_status')))}</td>"
            "</tr>"
        )
    return "\n".join(rendered)


def _decision_bars(counter: Counter[str]) -> str:
    total = max(1, sum(counter.values()))
    order = ["кандидат", "наблюдать", "заблокировать_политикой", "пропустить"]
    parts: list[str] = []
    for key in order:
        value = counter.get(key, 0)
        if value == 0:
            continue
        parts.append(
            "<div class='decision-line'>"
            f"<span>{_esc(_decision_label(key))}</span>"
            f"{_bar(value / total * 100)}"
            f"<b>{value}</b>"
            "</div>"
        )
    return "\n".join(parts)


def build_html(watchlist: list[dict[str, Any]], quality: list[dict[str, Any]]) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    decisions = Counter(str(row.get("trading_decision") or "") for row in watchlist)
    delivered = sum(1 for row in watchlist if row.get("delivery_status") == "delivered")
    avg_quality = (
        sum(float(row.get("quality_score") or 0) for row in watchlist) / len(watchlist)
        if watchlist
        else 0
    )
    candidate_count = decisions.get("кандидат", 0)
    blocked_count = decisions.get("заблокировать_политикой", 0)

    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Витрина сигналов T-Invest</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f4f6f8;
      --surface: #ffffff;
      --ink: #17202a;
      --muted: #667085;
      --line: #d9e0e8;
      --blue: #2563eb;
      --green: #168a4a;
      --amber: #b7791f;
      --red: #b42318;
      --violet: #6d5bd0;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: min(1180px, calc(100vw - 32px));
      margin: 28px auto 48px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 24px;
      align-items: flex-end;
      margin-bottom: 20px;
    }}
    h1, h2, p {{ margin: 0; }}
    h1 {{ font-size: clamp(28px, 4vw, 44px); line-height: 1.05; letter-spacing: 0; }}
    h2 {{ font-size: 18px; margin-bottom: 12px; }}
    .sub {{ color: var(--muted); max-width: 760px; margin-top: 10px; font-size: 15px; }}
    .stamp {{ color: var(--muted); text-align: right; min-width: 190px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin: 18px 0;
    }}
    .metric, section {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }}
    .metric {{ padding: 16px; }}
    .metric span {{ color: var(--muted); display: block; }}
    .metric strong {{ display: block; font-size: 30px; line-height: 1.1; margin-top: 8px; }}
    section {{ padding: 18px; margin-top: 12px; }}
    .two {{
      display: grid;
      grid-template-columns: minmax(260px, 0.85fr) minmax(0, 1.15fr);
      gap: 12px;
    }}
    .decision-line {{
      display: grid;
      grid-template-columns: 150px 1fr 28px;
      align-items: center;
      gap: 10px;
      margin: 12px 0;
    }}
    .bar {{
      display: block;
      height: 8px;
      background: #e9edf3;
      border-radius: 999px;
      overflow: hidden;
      min-width: 72px;
    }}
    .bar i {{ display: block; height: 100%; background: var(--blue); }}
    .bar.good i {{ background: var(--green); }}
    .bar.watch i {{ background: var(--amber); }}
    .bar.blocked i {{ background: var(--red); }}
    .bar.quality i {{ background: var(--violet); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th {{
      text-align: left;
      color: var(--muted);
      font-weight: 600;
      border-bottom: 1px solid var(--line);
      padding: 10px 8px;
      white-space: nowrap;
    }}
    td {{
      padding: 12px 8px;
      border-bottom: 1px solid #edf1f5;
      vertical-align: top;
    }}
    td span, td small {{ display: block; color: var(--muted); margin-top: 3px; }}
    .pill {{
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 3px 8px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      background: #edf1f5;
      color: var(--muted);
      white-space: nowrap;
    }}
    .pill.good {{ background: #e8f6ef; color: var(--green); }}
    .pill.watch {{ background: #fff4d6; color: var(--amber); }}
    .pill.blocked {{ background: #ffe8e5; color: var(--red); }}
    .pill.muted {{ background: #eef2f6; color: #58636f; }}
    .scroll {{ overflow-x: auto; }}
    @media (max-width: 820px) {{
      main {{ width: min(100vw - 20px, 720px); margin-top: 18px; }}
      header, .two {{ display: block; }}
      .stamp {{ text-align: left; margin-top: 10px; }}
      .grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .decision-line {{ grid-template-columns: 128px 1fr 24px; }}
      th, td {{ padding: 10px 6px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Витрина сигналов T-Invest</h1>
        <p class="sub">Итоговые таблицы dbt превращают сырые сигналы в список торговых решений: что можно рассматривать, что нужно наблюдать, а что заблокировано правилами доставки или качеством.</p>
      </div>
      <p class="stamp">Обновлено<br><strong>{generated_at}</strong></p>
    </header>

    <div class="grid">
      <div class="metric"><span>Сигналов в витрине</span><strong>{len(watchlist)}</strong></div>
      <div class="metric"><span>Кандидатов к действию</span><strong>{candidate_count}</strong></div>
      <div class="metric"><span>Отправлено в уведомления</span><strong>{delivered}</strong></div>
      <div class="metric"><span>Среднее качество</span><strong>{avg_quality:.0f}</strong></div>
    </div>

    <div class="two">
      <section>
        <h2>Распределение решений</h2>
        {_decision_bars(decisions)}
      </section>
      <section>
        <h2>Короткий вывод</h2>
        <p class="sub">Сейчас витрина отделяет сильные, но ограниченные правилами сигналы от реально доставленных. Это позволяет использовать `investment-signals` как источник событий, а `dbt-af` как слой аналитического контроля качества и принятия решений.</p>
        <p class="sub" style="margin-top:10px">Ограничено правилом: {blocked_count}. Такие сигналы выглядят сильными по метрикам, но не должны уходить в действие без проверки причины ограничения.</p>
      </section>
    </div>

    <section>
      <h2>Итоговый март: список решений</h2>
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th>Инструмент</th>
              <th>Решение</th>
              <th>Оценка решения</th>
              <th>Качество</th>
              <th>Доставка</th>
              <th>Причина</th>
            </tr>
          </thead>
          <tbody>
            {_watchlist_rows(watchlist)}
          </tbody>
        </table>
      </div>
    </section>

    <section>
      <h2>Итоговый март: качество типов сигналов</h2>
      <div class="scroll">
        <table>
          <thead>
            <tr>
              <th>Тип</th>
              <th>Всего</th>
              <th>Доставлено</th>
              <th>Доля доставки</th>
              <th>Среднее качество</th>
              <th>Статус качества</th>
            </tr>
          </thead>
          <tbody>
            {_quality_rows(quality)}
          </tbody>
        </table>
      </div>
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--investment-repo",
        type=Path,
        default=DEFAULT_INVESTMENT_REPO,
        help="Путь к локальному репозиторию investment-signals",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "outputs" / "investment_signals_marts_dashboard.html",
        help="Куда сохранить HTML-витрину",
    )
    args = parser.parse_args()

    watchlist = _run_json_query(
        args.investment_repo,
        f"select * from {WATCHLIST_TABLE} order by decision_score desc, detected_at desc",
    )
    quality = _run_json_query(
        args.investment_repo,
        f"select * from {QUALITY_TABLE} order by signal_count desc, avg_quality_score desc",
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(build_html(watchlist, quality), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
