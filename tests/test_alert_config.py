from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_alert_rules_have_three_actionable_slack_routes() -> None:
    config = yaml.safe_load(
        (REPO_ROOT / "config" / "alert_rules.yaml").read_text(encoding="utf-8")
    )
    alerts = config["alerts"]

    assert len(alerts) == 3
    assert len({alert["name"] for alert in alerts}) == 3
    for index, alert in enumerate(alerts, start=1):
        assert alert["severity"] in {"warning", "critical"}
        assert alert["condition"]
        assert alert["duration"]
        assert alert["type"] == "symptom-based"
        assert alert["channel"] == "#k4-l3b-alerts"
        assert alert["owner"] == "student-2A202602528"
        assert (REPO_ROOT / alert["runbook"].split("#", 1)[0]).exists()
        assert alert["runbook"].endswith(f"#alert-{index}")
