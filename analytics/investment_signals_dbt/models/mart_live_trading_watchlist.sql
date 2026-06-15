with signals as (
    select *
    from {{ ref('stg_market_signals') }}
),

scored as (
    select
        signal_id,
        detected_at,
        ticker,
        class_code,
        signal_type,
        severity,
        metric_value,
        baseline_value,
        z_score,
        quality_score,
        delivery_status,
        delivery_channel,
        delivery_reason,
        summary,
        round(
            least(
                100::numeric,
                quality_score
                + severity::numeric * 4
                + least(abs(z_score)::numeric * 2, 10)
                - case
                    when delivery_status = 'suppressed' or delivery_channel in ('admin_only', 'digest') then 15
                    when delivery_status = 'unknown' then 8
                    else 0
                  end
            ),
            2
        ) as decision_score
    from signals
)

select
    *,
    case
        when delivery_status = 'delivered' and quality_score >= 75 and severity >= 2
            then 'кандидат'
        when (delivery_status = 'suppressed' or delivery_channel in ('admin_only', 'digest')) and quality_score >= 70
            then 'заблокировать_политикой'
        when quality_score >= 60 or severity >= 2
            then 'наблюдать'
        else 'пропустить'
    end as trading_decision,
    case
        when delivery_status = 'delivered' and quality_score >= 75 and severity >= 2
            then 'сигнал прошел контроль качества и был доставлен'
        when (delivery_status = 'suppressed' or delivery_channel in ('admin_only', 'digest')) and quality_score >= 70
            then 'сигнал сильный, но его нельзя использовать без проверки правила доставки'
        when quality_score >= 60 or severity >= 2
            then 'есть рыночное отклонение, но нужна дополнительная проверка'
        else 'качество сигнала недостаточно для действия'
    end as decision_reason
from scored
order by detected_at desc, decision_score desc

