#!/usr/bin/env bash
set -euo pipefail
tag="${1:?usage: deploy.sh COMMIT_SHA}"
[[ "$tag" =~ ^[0-9a-f]{7,40}$ ]] || { echo 'Tag must be a commit SHA' >&2; exit 1; }
if [[ "$(kubectl config current-context)" != "k3d-idea-validator" ]]; then
  echo 'Refusing deployment outside k3d-idea-validator' >&2
  exit 1
fi
if ! kubectl get secret platform-secrets -n idea-validator >/dev/null 2>&1; then
  echo 'Create platform-secrets with POSTGRES_PASSWORD before deployment' >&2
  exit 1
fi
kubectl kustomize k8s/overlays/local | sed "s/:0000000$/:${tag}/" | kubectl apply -f -
services=(gateway ui profile orchestrator scouts tools kb analyst ideation validators scorer verdict critic agentops)
for service in "${services[@]}"; do
  kubectl rollout status "deployment/${service}" -n idea-validator --timeout=180s
done
for database in postgres redis qdrant; do
  kubectl rollout status "statefulset/${database}" -n idea-validator --timeout=180s
done
