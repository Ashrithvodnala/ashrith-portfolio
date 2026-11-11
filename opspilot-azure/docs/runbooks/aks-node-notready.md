# Runbook: AKS node NotReady

## Symptoms
`kubectl get nodes` shows a node as `NotReady`. Pods on that node may be stuck in `Terminating` or rescheduled elsewhere.

## First checks
1. Describe the node: `kubectl describe node <node>`. Check `Conditions` for `MemoryPressure`, `DiskPressure` or `PIDPressure`.
2. Check the node in Azure: `az aks nodepool show -g <rg> --cluster-name <cluster> -n <pool>` and the VM scale set instance health.
3. Review Container Insights in Azure Monitor for kubelet errors on that node.

## Remediation
- Disk pressure: clean up unused images or increase the OS disk size of the node pool.
- Unresponsive node: cordon and drain it with `kubectl cordon <node>` and `kubectl drain <node> --ignore-daemonsets --delete-emptydir-data`, then reimage the instance with `az vmss reimage`.
- If several nodes are affected, check for an Azure service health incident in the region before making changes.

## Prevention
Enable the cluster autoscaler, set resource requests on every workload and keep node images updated with `az aks nodepool upgrade --node-image-only`.
