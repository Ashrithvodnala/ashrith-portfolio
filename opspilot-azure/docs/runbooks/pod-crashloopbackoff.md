# Runbook: Pod in CrashLoopBackOff

## Symptoms
A pod restarts repeatedly and `kubectl get pods` shows `CrashLoopBackOff`. The Kubernetes back-off delay grows up to five minutes between restarts.

## First checks
1. Find the pod and restart count: `kubectl get pods -n <namespace>`.
2. Read the logs of the crashed container, not the new one: `kubectl logs <pod> -n <namespace> --previous`.
3. Check events and the last state: `kubectl describe pod <pod> -n <namespace>`. Look at `Last State`, `Reason` and `Exit Code`.

## Common causes by exit code
- Exit code 1: the application failed at startup. Usually a missing environment variable, bad config or failed database connection. Compare the ConfigMap and Secret with the previous release.
- Exit code 137: the container was killed, usually OOMKilled. Check `kubectl describe pod` for `OOMKilled` and raise `resources.limits.memory` or fix the memory leak.
- Exit code 143: the container received SIGTERM, often because the liveness probe failed. Check probe path, port and `initialDelaySeconds`.

## Fix and roll back
- If the crash started with a new release, roll back: `kubectl rollout undo deployment/<name> -n <namespace>` or revert the Git commit so Argo CD syncs the previous version.
- Confirm recovery with `kubectl rollout status deployment/<name> -n <namespace>`.

## Escalate
Escalate to the application team if logs show an application exception after config has been verified.
