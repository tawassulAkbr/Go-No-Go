#!/usr/bin/env bash
set -euo pipefail
namespace=idea-validator
base_url="${SMOKE_BASE_URL:-http://localhost:8080}"
[[ "$(kubectl config current-context)" == "k3d-idea-validator" ]]
count="$(kubectl get pods -n "$namespace" --no-headers | wc -l | tr -d ' ')"
[[ "$count" -ge 17 ]] || { echo "Expected at least 17 pods, found $count" >&2; exit 1; }
kubectl wait pod --all --for=condition=Ready -n "$namespace" --timeout=180s
curl -fsS "${base_url}/api/health" >/dev/null
response="$(curl -fsS -X POST "${base_url}/api/demo/validate" -H 'Content-Type: application/json' -d '{"idea":"A study planner"}')"
if ! printf '%s' "$response" | grep -Eq '"demo"[[:space:]]*:[[:space:]]*true'; then
  echo "Demo flow did not return the marked stub result: $response" >&2
  exit 1
fi
printf '%s\n' 'Phase 2 smoke test passed'
