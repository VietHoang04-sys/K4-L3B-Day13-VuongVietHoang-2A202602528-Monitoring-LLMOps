from __future__ import annotations

import html
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG_PATH = REPO_ROOT / "data" / "logs.jsonl"
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "dashboard.yaml"
BUCKET_COUNT = 12


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def load_dashboard_data(
    log_path: Path = DEFAULT_LOG_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    *,
    now: datetime | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], int]:
    config_payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    dashboard = config_payload["dashboard"]
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    cutoff = current_time - timedelta(minutes=dashboard["time_range_minutes"])

    records: list[dict[str, Any]] = []
    invalid_lines = 0
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            invalid_lines += 1
            continue
        if not isinstance(record, dict):
            invalid_lines += 1
            continue
        timestamp = _parse_timestamp(record.get("ts"))
        if timestamp is not None and cutoff <= timestamp <= current_time:
            record["_timestamp"] = timestamp
            records.append(record)
    return dashboard, records, invalid_lines


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(percentile / 100 * len(ordered)) - 1)
    return ordered[index]


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _number(value: float | None, suffix: str = "", decimals: int = 1) -> str:
    return "No data" if value is None else f"{value:,.{decimals}f}{suffix}"


def _bucket_index(record: dict[str, Any], cutoff: datetime) -> int:
    elapsed = (record["_timestamp"] - cutoff).total_seconds()
    return min(BUCKET_COUNT - 1, max(0, int(elapsed // 300)))


def _svg_bars(values: list[float], *, color: str, maximum: float | None = None) -> str:
    peak = maximum if maximum and maximum > 0 else max(values, default=0.0)
    peak = peak or 1.0
    bars = []
    for index, value in enumerate(values):
        height = max(2.0, (value / peak) * 70) if value > 0 else 1.0
        x = 4 + index * 24
        y = 80 - height
        bars.append(
            f'<rect x="{x}" y="{y:.1f}" width="15" height="{height:.1f}" '
            f'rx="2" fill="{color}"><title>{value:.2f}</title></rect>'
        )
    return (
        '<svg class="chart" viewBox="0 0 300 88" role="img" '
        'aria-label="12 five-minute buckets">'
        '<path d="M0 80H300" stroke="#334155"/>'
        + "".join(bars)
        + "</svg>"
    )


def _panel(
    panel_config: dict[str, Any],
    summary: str,
    chart: str,
) -> str:
    threshold = panel_config["threshold"]
    threshold_text = (
        f'{threshold["aggregation"]} {threshold["operator"]} '
        f'{threshold["value"]:g} {panel_config["unit"]}'
    )
    return (
        f'<section class="panel" id="{html.escape(panel_config["id"])}">'
        f'<h2>{html.escape(panel_config["title"])}</h2>'
        f'<p class="summary">{summary}</p>'
        f'<p class="unit">Unit: {html.escape(panel_config["unit"])}</p>'
        f'<p class="threshold">Threshold: {html.escape(threshold_text)}</p>'
        f"{chart}</section>"
    )


def render_dashboard(
    log_path: Path = DEFAULT_LOG_PATH,
    config_path: Path = DEFAULT_CONFIG_PATH,
    *,
    now: datetime | None = None,
) -> str:
    dashboard, records, invalid_lines = load_dashboard_data(
        log_path, config_path, now=now
    )
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)
    cutoff = current_time - timedelta(minutes=dashboard["time_range_minutes"])

    received = [record for record in records if record.get("event") == "request_received"]
    completed = [record for record in records if record.get("event") == "response_sent"]
    failed = [record for record in records if record.get("event") == "request_failed"]
    retrieval_records = [
        record for record in records if record.get("tool_success") is not None
    ]
    retrieval_successes = sum(
        record.get("tool_success") is True for record in retrieval_records
    )
    retrieval_success_rate = (
        retrieval_successes / len(retrieval_records) * 100
        if retrieval_records
        else None
    )
    latencies = [
        float(record["latency_ms"])
        for record in completed
        if isinstance(record.get("latency_ms"), (int, float))
    ]
    ttfts = [
        float(record["ttft_ms"])
        for record in completed
        if isinstance(record.get("ttft_ms"), (int, float))
    ]
    costs = [
        float(record["cost_usd"])
        for record in completed
        if isinstance(record.get("cost_usd"), (int, float))
    ]
    input_tokens = sum(
        record.get("tokens_in", 0)
        for record in completed
        if isinstance(record.get("tokens_in"), (int, float))
    )
    output_tokens = sum(
        record.get("tokens_out", 0)
        for record in completed
        if isinstance(record.get("tokens_out"), (int, float))
    )
    quality = [
        float(record["quality_score"])
        for record in completed
        if isinstance(record.get("quality_score"), (int, float))
    ]
    error_rate = len(failed) / len(received) * 100 if received else None

    buckets = [[] for _ in range(BUCKET_COUNT)]
    for record in records:
        buckets[_bucket_index(record, cutoff)].append(record)
    latency_buckets = [
        _mean(
            [
                float(item["latency_ms"])
                for item in bucket
                if item.get("event") == "response_sent"
                and isinstance(item.get("latency_ms"), (int, float))
            ]
        )
        or 0.0
        for bucket in buckets
    ]
    traffic_buckets = [
        sum(item.get("event") == "request_received" for item in bucket)
        for bucket in buckets
    ]
    error_buckets = [
        sum(item.get("event") == "request_failed" for item in bucket)
        for bucket in buckets
    ]
    cost_buckets = [
        sum(
            float(item.get("cost_usd", 0))
            for item in bucket
            if item.get("event") == "response_sent"
            and isinstance(item.get("cost_usd", 0), (int, float))
        )
        for bucket in buckets
    ]
    token_buckets = [
        sum(
            float(item.get("tokens_in", 0)) + float(item.get("tokens_out", 0))
            for item in bucket
            if item.get("event") == "response_sent"
            and isinstance(item.get("tokens_in", 0), (int, float))
            and isinstance(item.get("tokens_out", 0), (int, float))
        )
        for bucket in buckets
    ]
    quality_buckets = [
        _mean(
            [
                float(item["quality_score"])
                for item in bucket
                if item.get("event") == "response_sent"
                and isinstance(item.get("quality_score"), (int, float))
            ]
        )
        or 0.0
        for bucket in buckets
    ]

    panel_values = {
        "latency": (
            " · ".join(
                (
                    f'P50 {_number(_percentile(latencies, 50), " ms")}',
                    f'P95 {_number(_percentile(latencies, 95), " ms")}',
                    f'P99 {_number(_percentile(latencies, 99), " ms")}',
                    f'TTFT P95 {_number(_percentile(ttfts, 95), " ms")}',
                )
            ),
            _svg_bars(latency_buckets, color="#38bdf8"),
        ),
        "traffic": (
            f"{len(received)} requests · "
            f'{len(received) / dashboard["time_range_minutes"]:.2f} requests/min',
            _svg_bars(traffic_buckets, color="#a78bfa"),
        ),
        "errors": (
            f'Error rate {_number(error_rate, "%")} · '
            f'Retrieval success {_number(retrieval_success_rate, "%")}',
            _svg_bars(error_buckets, color="#fb7185"),
        ),
        "cost": (
            f'Total {_number(sum(costs), " USD", 6)} · '
            f'Average/request {_number(_mean(costs), " USD", 6)}',
            _svg_bars(cost_buckets, color="#fbbf24"),
        ),
        "tokens": (
            f"Input {input_tokens:,.0f} · Output {output_tokens:,.0f}",
            _svg_bars(token_buckets, color="#34d399"),
        ),
        "quality": (
            f'Mean quality {_number(_mean(quality), " / 1.0", 2)}',
            _svg_bars(quality_buckets, color="#c084fc", maximum=1.0),
        ),
    }
    panels = "".join(
        _panel(
            panel,
            panel_values[panel["id"]][0],
            panel_values[panel["id"]][1],
        )
        for panel in dashboard["panels"]
    )
    warning = (
        f'<p class="warning">{invalid_lines} malformed log line(s) skipped.</p>'
        if invalid_lines
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="{dashboard['refresh_seconds']}">
  <title>{html.escape(dashboard['title'])}</title>
  <style>
    :root {{ color-scheme: dark; font-family: Segoe UI, sans-serif; background: #0f172a; color: #e2e8f0; }}
    body {{ margin: 0 auto; max-width: 1280px; padding: 24px; }}
    header {{ display: flex; justify-content: space-between; align-items: end; gap: 16px; flex-wrap: wrap; }}
    h1 {{ margin: 0; font-size: 1.7rem; }} .meta {{ color: #94a3b8; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-top: 20px; }}
    .panel {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 18px; min-width: 0; }}
    h2 {{ margin: 0 0 12px; font-size: 1rem; }} .summary {{ font-size: 1.25rem; font-weight: 650; min-height: 2.8em; }}
    .unit, .threshold {{ color: #94a3b8; font-size: .85rem; margin: 6px 0; }}
    .chart {{ display: block; width: 100%; height: 90px; margin-top: 10px; }}
    .warning {{ color: #fda4af; }} footer {{ margin-top: 18px; color: #94a3b8; font-size: .85rem; }}
    @media (max-width: 760px) {{ .grid {{ grid-template-columns: 1fr; }} body {{ padding: 14px; }} }}
  </style>
</head>
<body>
  <header><h1>{html.escape(dashboard['title'])}</h1>
    <div class="meta">Last {dashboard['time_range_minutes']} minutes · refreshed every {dashboard['refresh_seconds']}s<br>
    Updated {current_time.astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")}</div>
  </header>
  {warning}
  <main class="grid">{panels}</main>
  <footer>Source: data/logs.jsonl · 5-minute buckets · Values are computed from the configured log events.</footer>
</body>
</html>"""
