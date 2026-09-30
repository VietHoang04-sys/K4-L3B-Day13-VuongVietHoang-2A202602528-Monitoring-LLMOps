from __future__ import annotations

import json
import asyncio
from pathlib import Path

import httpx

from app import logging_config
from app.main import app


def test_chat_response_log_exposes_quality_for_dashboard(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                json={
                    "user_id": "student-01",
                    "session_id": "session-01",
                    "feature": "qa",
                    "message": "Explain observability",
                },
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    assert response.headers["x-request-id"] == response.json()["correlation_id"]
    assert response.headers["x-request-id"].startswith("req-")
    assert "x-response-time-ms" in response.headers
    events = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    response_event = next(event for event in events if event["event"] == "response_sent")
    assert response_event["quality_score"] == response.json()["quality_score"]
    assert response_event["ttft_ms"] == response.json()["ttft_ms"]
    assert response_event["tool_name"] == "retrieval"
    assert response_event["tool_success"] is True
    assert response_event["user_id_hash"]
    assert response_event["session_id"] == "session-01"
    assert response_event["feature"] == "qa"
    assert response_event["model"]
    assert response_event["env"]


def test_request_id_is_validated_and_context_is_scrubbed(
    monkeypatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "logs.jsonl"
    monkeypatch.setattr(logging_config, "LOG_PATH", log_path)

    async def send_request(request_id: str) -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            return await client.post(
                "/chat",
                headers={"x-request-id": request_id},
                json={
                    "user_id": "student-02",
                    "session_id": "session-02",
                    "feature": "qa",
                    "message": "Contact test@example.com",
                },
            )

    accepted = asyncio.run(send_request("req-a1b2c3d4"))
    rejected = asyncio.run(send_request("customer@example.com"))

    assert accepted.headers["x-request-id"] == "req-a1b2c3d4"
    assert rejected.headers["x-request-id"].startswith("req-")
    logs = log_path.read_text(encoding="utf-8")
    assert "test@example.com" not in logs
    assert "customer@example.com" not in logs
    assert "REDACTED_EMAIL" in logs
