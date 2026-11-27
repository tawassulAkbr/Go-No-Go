#!/usr/bin/env bash
set -euo pipefail
tag="${1:?usage: push_images.sh COMMIT_SHA}"
[[ "$tag" =~ ^[0-9a-f]{7,40}$ ]] || { echo 'Tag must be a commit SHA' >&2; exit 1; }
services=(gateway ui profile orchestrator scouts tools kb analyst ideation validators scorer verdict critic agentops)
for service in "${services[@]}"; do
  docker push "localhost:5001/${service}:${tag}"
done
