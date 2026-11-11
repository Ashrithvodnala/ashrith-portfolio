from copilot.agent import Investigation
from copilot.alerts import Alert
from copilot.report import build_incident, slack_text


def test_incident_and_slack_text():
    alert = Alert("DemoPodCrashLooping", "firing", "critical", "demo", {"pod": "p"}, {}, "", "fp1")
    inv = Investigation("## Summary\nx", [{"tool": "get_pod_logs", "args": {}, "ok": True}], 2, 100, 20, 3.5)
    inc = build_incident(alert, inv, "bedrock")
    assert inc["id"].startswith("fp1-") and inc["tokens"] == 120 and inc["tools_used"] == ["get_pod_logs"]
    text = slack_text(inc)
    assert "*DemoPodCrashLooping*" in text and "`demo`" in text and "bedrock" in text
