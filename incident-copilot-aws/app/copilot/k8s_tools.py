"""Read-only Kubernetes and Prometheus tools used by the agent (exposed through the MCP server).

Set K8S_MODE=fake to use built-in sample data (no cluster needed) for demos and tests.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

MAX_LOG_LINES = 80


def _allowed(namespace: str) -> None:
    allowed = [n.strip() for n in os.getenv("ALLOWED_NAMESPACES", "").split(",") if n.strip()]
    if allowed and namespace not in allowed:
        raise PermissionError(f"namespace '{namespace}' is not in ALLOWED_NAMESPACES")


def _fake() -> bool:
    return os.getenv("K8S_MODE", "") == "fake"


_clients: dict = {}


def _core():
    if "core" not in _clients:
        from kubernetes import client, config

        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        _clients["core"], _clients["apps"] = client.CoreV1Api(), client.AppsV1Api()
    return _clients["core"]


def _apps():
    _core()
    return _clients["apps"]


def _age(ts) -> str:
    if not ts:
        return "?"
    seconds = int((datetime.now(timezone.utc) - ts).total_seconds())
    return f"{seconds // 3600}h" if seconds >= 3600 else f"{seconds // 60}m"


# ---------------- tools ----------------

def list_unhealthy_pods(namespace: str) -> str:
    _allowed(namespace)
    if _fake():
        return FAKE["pods"]
    rows = []
    for pod in _core().list_namespaced_pod(namespace).items:
        for cs in pod.status.container_statuses or []:
            waiting = cs.state.waiting.reason if cs.state and cs.state.waiting else ""
            last = cs.last_state.terminated if cs.last_state else None
            if waiting or not cs.ready or cs.restart_count > 0:
                rows.append(
                    f"{pod.metadata.name} container={cs.name} ready={cs.ready} restarts={cs.restart_count} "
                    f"waiting={waiting or '-'} last_exit={last.exit_code if last else '-'} "
                    f"last_reason={last.reason if last else '-'} age={_age(pod.metadata.creation_timestamp)}"
                )
    return "\n".join(rows) or f"All pods in {namespace} are healthy."


def get_pod_logs(namespace: str, pod: str, container: str = "", previous: bool = True) -> str:
    _allowed(namespace)
    if _fake():
        return FAKE["logs"]
    kwargs = {"tail_lines": MAX_LOG_LINES, "previous": previous}
    if container:
        kwargs["container"] = container
    try:
        return _core().read_namespaced_pod_log(pod, namespace, **kwargs) or "(no log output)"
    except Exception as exc:
        if previous:  # no previous container yet -> fall back to current logs
            kwargs["previous"] = False
            return _core().read_namespaced_pod_log(pod, namespace, **kwargs) or "(no log output)"
        raise exc


def get_events(namespace: str, object_name: str = "") -> str:
    _allowed(namespace)
    if _fake():
        return FAKE["events"]
    selector = f"involvedObject.name={object_name}" if object_name else None
    events = _core().list_namespaced_event(namespace, field_selector=selector).items
    events = sorted(events, key=lambda e: e.last_timestamp or e.event_time or e.metadata.creation_timestamp)[-25:]
    return "\n".join(
        f"{e.type} {e.reason} {e.involved_object.kind}/{e.involved_object.name} x{e.count or 1}: {e.message}"
        for e in events
    ) or "No events."


def describe_deployment(namespace: str, name: str) -> str:
    _allowed(namespace)
    if _fake():
        return FAKE["deployment"]
    d = _apps().read_namespaced_deployment(name, namespace)
    c = d.spec.template.spec.containers
    lines = [
        f"deployment {name}: desired={d.spec.replicas} ready={d.status.ready_replicas or 0} "
        f"updated={d.status.updated_replicas or 0} available={d.status.available_replicas or 0}",
        "images: " + ", ".join(f"{x.name}={x.image}" for x in c),
        "limits: " + ", ".join(f"{x.name}={(x.resources.limits or {}) if x.resources else {}}" for x in c),
        "env var names: " + ", ".join(sorted({e.name for x in c for e in (x.env or [])})) or "none",
    ]
    for cond in d.status.conditions or []:
        lines.append(f"condition {cond.type}={cond.status} reason={cond.reason}: {cond.message}")
    return "\n".join(lines)


def query_prometheus(promql: str) -> str:
    if _fake():
        return FAKE["prometheus"]
    import httpx

    url = os.getenv("PROMETHEUS_URL", "http://monitoring-kube-prometheus-prometheus.monitoring:9090")
    resp = httpx.get(f"{url}/api/v1/query", params={"query": promql}, timeout=15)
    resp.raise_for_status()
    results = resp.json()["data"]["result"][:20]
    return "\n".join(f"{r['metric']} = {r['value'][1]}" for r in results) or "No data."


FAKE = {
    "pods": "payments-api-7d9f8c6b5-x2kqp container=api ready=False restarts=6 waiting=CrashLoopBackOff "
            "last_exit=1 last_reason=Error age=14m",
    "logs": "2026-11-11T14:02:11Z INFO starting payments-api v2.4.0\n"
            "2026-11-11T14:02:11Z INFO connecting to database host=payments-db.prod.svc password=hunter2\n"
            "2026-11-11T14:02:12Z ERROR KeyError: 'PAYMENTS_DB_URL' environment variable is not set\n"
            "2026-11-11T14:02:12Z FATAL startup failed, exiting with code 1",
    "events": "Normal ScalingReplicaSet Deployment/payments-api x1: Scaled up replica set payments-api-7d9f8c6b5 to 1\n"
              "Normal Pulled Pod/payments-api-7d9f8c6b5-x2kqp x6: Container image "
              "\"123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api:2.4.0\" already present\n"
              "Warning BackOff Pod/payments-api-7d9f8c6b5-x2kqp x41: Back-off restarting failed container api",
    "deployment": "deployment payments-api: desired=3 ready=2 updated=1 available=2\n"
                  "images: api=123456789012.dkr.ecr.us-east-1.amazonaws.com/payments-api:2.4.0\n"
                  "limits: api={'memory': '512Mi'}\n"
                  "env var names: DB_URL, LOG_LEVEL\n"
                  "condition Progressing=True reason=ReplicaSetUpdated: rollout of 2.4.0 in progress",
    "prometheus": "{'pod': 'payments-api-7d9f8c6b5-x2kqp'} = 6",
}
