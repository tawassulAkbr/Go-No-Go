#!/usr/bin/env bash
set -euo pipefail
tag="${1:?usage: build_all.sh COMMIT_SHA}"
[[ "$tag" =~ ^[0-9a-f]{7,40}$ ]] || { echo 'Tag must be a commit SHA' >&2; exit 1; }
services=(gateway ui profile orchestrator scouts tools kb analyst ideation validators scorer verdict critic agentops)
for service in "${services[@]}"; do
  docker build -f "services/${service}/Dockerfile" -t "localhost:5001/${service}:${tag}" .
done
