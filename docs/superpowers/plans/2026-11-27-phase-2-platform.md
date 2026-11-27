# Phase 2 Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put all Phase 2 module stubs behind one Kubernetes ingress, with a fixed UI → gateway → orchestrator → verdict demonstration and automated checks.

**Architecture:** Each module has its own image and Kubernetes Deployment/Service. Python stubs share a small app factory but have independent entry points. The UI is a small React/TypeScript app that P5 will extend. Docker Compose is development-only; Kustomize deploys the cluster.

**Tech Stack:** FastAPI, Pydantic, HTTPX, React, Vite, Vitest, Docker, Kubernetes/Kustomize, GitHub Actions, Jenkins.

**Spec:** `docs/Phases/P02_platform_skeleton.md` and `docs/rule.md`.

## Global Constraints

- Keep all runtime configuration in environment variables or ConfigMaps.
- Use separate non-root, multi-stage images tagged by commit SHA.
- Only M1 is exposed by the ingress. P2 demo data must be visibly labeled.
- Do not commit secrets. Do not claim Kubernetes or CI success without observing it.

## Review Focus

- The demo request must traverse the gateway, orchestrator, and verdict service; a gateway-local fake would not prove service routing.
- Empty or oversized idea text must fail validation before reaching downstream stubs.
- Downstream failures must be visible as errors, not reported as successful verdicts.
- Cluster images must use the registry address visible from k3d and a SHA tag.
- Smoke checks must fail when a required pod is unready.

---

### Task 1: Python service stubs and demo route

**Files:** `libs/platform_stub/`, `services/{gateway,profile,orchestrator,scouts,tools,kb,analyst,ideation,validators,scorer,verdict,critic,agentops}/`, `requirements-dev.txt`.

**Interfaces:** Gateway `POST /demo/validate` → orchestrator `POST /demo/validate` → verdict `POST /demo/verdict`; all services `GET /health`, `/ready`, `/metrics`.

- [ ] Write and run failing tests for health/readiness, request validation, the three-service demo flow, and downstream failure.
- [ ] Add the shared app factory, module entry points, pinned requirements, and per-module Dockerfiles.
- [ ] Run the Python suite and compile/check all Python files.

### Task 2: Minimal UI

**Files:** `services/ui/`.

**Interfaces:** Browser calls only relative `/api/demo/validate`; result displays `demo: true` and the verdict reason.

- [ ] Write and run a failing UI interaction test.
- [ ] Add the React/Vite page, test/lint scripts, lockfile, runtime config, and non-root multi-stage image.
- [ ] Run `npm ci`, UI tests, lint, and build.

### Task 3: Local and Kubernetes platform

**Files:** `docker-compose.yml`, `k8s/base/`, `k8s/overlays/local/`, `scripts/build_push.ps1`, `scripts/build_all.sh`, `scripts/push_images.sh`, `scripts/deploy.sh`, `scripts/smoke_test.sh`.

- [ ] Add pinned development databases and volumes.
- [ ] Add all service Deployments/Services, database StatefulSets/PVCs, a namespace, ConfigMap, and ingress.
- [ ] Add SHA-tag build, push, deploy, and smoke scripts.
- [ ] Run static Kustomize and script validation; run cluster checks if Docker/k3d are available.

### Task 4: CI, Jenkins, and handoff

**Files:** `.github/workflows/pr-checks.yml`, `Jenkinsfile`, `docs/ai-usage-log.md`, `docs/Phases/P02_platform_skeleton.md`.

- [ ] Add PR jobs for Python, UI, image build/scan, manifests, and secrets.
- [ ] Add initial Jenkins checkout/build/push/deploy/smoke pipeline with credential handling.
- [ ] Record AI work and exact manual setup and sign-off steps.
- [ ] Run all available local checks and inspect the branch diff.
