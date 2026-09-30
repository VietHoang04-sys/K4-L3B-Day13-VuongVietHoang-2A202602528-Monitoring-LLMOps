from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from app.dashboard import render_dashboard


def test_dashboard_renders_six_panels_from_recent_logs(tmp_path: Path) -> None:
    now = datetime(2026, 9, 30, 12, 0, tzinfo=timezone.utc)
    common = {
        "ts": now.isoformat(),
        "correlation_id": "req-a1b2c3d4",
        "service": "api",
    }
    records = [
        {**common, "event": "request_received"},
        {
            **common,
            "event": "response_sent",
            "latency_ms": 1250,
            "ttft_ms": 90,
            "cost_usd": 0.001,
            "tokens_in": 100,
            "tokens_out": 50,
            "quality_score": 0.8,
            "tool_name": "retrieval",
            "tool_success": True,
        },
    ]
    log_path = tmp_path / "logs.jsonl"
    log_path.write_text(
        "\n".join(json.dumps(record) for record in records), encoding="utf-8"
    )

    page = render_dashboard(log_path, now=now)

    for panel_id in ("latency", "traffic", "errors", "cost", "tokens", "quality"):
        assert f'id="{panel_id}"' in page
    assert "P95 1,250.0 ms" in page
    assert "Retrieval success 100.0%" in page
    assert "Last 60 minutes" in page
    assert "Threshold:" in page
