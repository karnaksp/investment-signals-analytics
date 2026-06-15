select
    signal_id::text as signal_id,
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
    coalesce(
        nullif(payload_json ->> 'quality_score', '')::numeric,
        least(100::numeric, greatest(0::numeric, severity::numeric * 25 + least(abs(z_score)::numeric * 5, 25)))
    ) as quality_score,
    coalesce(nullif(payload_json ->> 'delivery_status', ''), 'unknown') as delivery_status,
    coalesce(nullif(payload_json ->> 'delivery_reason', ''), 'unknown') as delivery_reason,
    coalesce(nullif(payload_json ->> 'delivery_rule', ''), 'unknown') as delivery_rule,
    coalesce(nullif(payload_json ->> 'delivery_channel', ''), 'unknown') as delivery_channel,
    payload_json,
    current_timestamp as loaded_at
from {{ source('investment_signals_live', 'market_signals') }}

