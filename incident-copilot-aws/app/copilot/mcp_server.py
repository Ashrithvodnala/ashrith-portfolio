"""MCP server exposing the read-only investigation tools.

Run standalone with:  python -m copilot.mcp_server   (stdio transport)
Any MCP client (this agent, Claude Desktop, an IDE) can use these tools.
"""

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import k8s_tools


def _run(fn, *args):
    """Report tool failures (e.g. namespace not allowed, pod not found) back to the agent with their message."""
    try:
        return fn(*args)
    except Exception as exc:
        raise ToolError(f"{type(exc).__name__}: {exc}") from exc

server = MCPServer("incident-copilot-k8s", instructions="Read-only Kubernetes and Prometheus tools for incident triage.")


@server.tool()
def list_unhealthy_pods(namespace: str) -> str:
    """List pods in a namespace that are not ready, waiting (e.g. CrashLoopBackOff, ImagePullBackOff) or restarting,
    with restart counts and the last exit code and reason."""
    return _run(k8s_tools.list_unhealthy_pods, namespace)


@server.tool()
def get_pod_logs(namespace: str, pod: str, container: str = "", previous: bool = True) -> str:
    """Get the last 80 log lines of a pod. previous=true reads the crashed (previous) container, which is usually
    where the error is for CrashLoopBackOff."""
    return _run(k8s_tools.get_pod_logs, namespace, pod, container, previous)


@server.tool()
def get_events(namespace: str, object_name: str = "") -> str:
    """Get recent Kubernetes events in a namespace, optionally only for one object (pod or deployment name)."""
    return _run(k8s_tools.get_events, namespace, object_name)


@server.tool()
def describe_deployment(namespace: str, name: str) -> str:
    """Show a deployment's replica status, container images, memory/CPU limits, env var names and rollout conditions."""
    return _run(k8s_tools.describe_deployment, namespace, name)


@server.tool()
def query_prometheus(promql: str) -> str:
    """Run an instant PromQL query, e.g. increase(kube_pod_container_status_restarts_total{namespace="demo"}[15m])."""
    return _run(k8s_tools.query_prometheus, promql)


if __name__ == "__main__":
    server.run("stdio")
