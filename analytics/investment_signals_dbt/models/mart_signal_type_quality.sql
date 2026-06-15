with signals as (
    select *
    from {{ ref('stg_market_signals') }}
),

aggregated as (
    select
        ticker,
        signal_type,
        count(*) as signal_count,
        count(*) filter (where delivery_status = 'delivered') as delivered_count,
        count(*) filter (
            where delivery_status = 'suppressed'
                or delivery_channel in ('admin_only', 'digest')
        ) as restricted_count,
        count(*) filter (where severity >= 3) as high_severity_count,
        round(avg(quality_score), 2) as avg_quality_score,
        round(avg(abs(z_score))::numeric, 2) as avg_abs_z_score,
        max(detected_at) as last_detected_at
    from signals
    group by 1, 2
)

select
    *,
    round(delivered_count::numeric / nullif(signal_count, 0), 3) as delivered_ratio,
    case
        when avg_quality_score >= 80 and delivered_count::numeric / nullif(signal_count, 0) >= 0.5
            then 'стабильный_кандидат'
        when avg_quality_score >= 70 and restricted_count > delivered_count
            then 'сильный_сигнал_с_ограничением_доставки'
        when avg_quality_score < 60
            then 'много_шума'
        else 'наблюдать'
    end as quality_status
from aggregated

