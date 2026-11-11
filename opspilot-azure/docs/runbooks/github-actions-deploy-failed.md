# Runbook: GitHub Actions deployment failed

## Symptoms
The `ci` workflow fails on the main branch and the new image is not deployed, or Argo CD shows the application as `OutOfSync` or `Degraded`.

## First checks
1. Open the failed run in GitHub Actions and find the first failing step.
2. Authentication errors (`AADSTS70021` or `No matching federated identity record found`): the OIDC federated credential subject must match `repo:<org>/<repo>:ref:refs/heads/main`.
3. Image scan failures: Trivy found HIGH or CRITICAL vulnerabilities. Update the base image or the affected package, then re-run.
4. Push to ACR denied: confirm the GitHub identity has the `AcrPush` role on the registry.

## Argo CD problems
- `OutOfSync` after a successful build: check that the workflow committed the new image tag to `deploy/helm/opspilot/values.yaml`.
- `Degraded`: the new pods are failing. Follow the CrashLoopBackOff runbook, or roll back by reverting the tag commit in Git.

## Prevention
Require the test job to pass before merge with branch protection, and keep workflow templates shared so fixes apply to every repository.
