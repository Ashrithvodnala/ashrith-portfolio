from copilot.alerts import build_investigation_prompt, parse_alertmanager

PAYLOAD = {
    "status": "firing",
    "alerts": [
        {"status": "firing", "fingerprint": "abc123",
         "labels": {"alertname": "DemoPodCrashLooping", "namespace": "demo", "pod": "crashy-1", "severity": "critical",
                    "prometheus": "monitoring/kube-prom"},
         "annotations": {"summary": "Pod demo/crashy-1 is crash looping"}, "startsAt": "2026-11-11T14:00:00Z"},
        {"status": "resolved", "labels": {"alertname": "Old"}},
    ],
}


def test_parses_only_firing_alerts():
    alerts = parse_alertmanager(PAYLOAD)
    assert len(alerts) == 1
    a = alerts[0]
    assert (a.name, a.namespace, a.severity, a.fingerprint) == ("DemoPodCrashLooping", "demo", "critical", "abc123")


def test_fingerprint_generated_when_missing():
    a = parse_alertmanager({"alerts": [{"status": "firing", "labels": {"alertname": "X", "pod": "p"}}]})[0]
    b = parse_alertmanager({"alerts": [{"status": "firing", "labels": {"pod": "p", "alertname": "X"}}]})[0]
    assert a.fingerprint == b.fingerprint and len(a.fingerprint) == 16


def test_prompt_contains_alert_context_but_not_noise_labels():
    prompt = build_investigation_prompt(parse_alertmanager(PAYLOAD)[0])
    assert "DemoPodCrashLooping" in prompt and "pod=crashy-1" in prompt and "namespace=demo" in prompt
    assert "prometheus=" not in prompt
    assert "Pod demo/crashy-1 is crash looping" in prompt
