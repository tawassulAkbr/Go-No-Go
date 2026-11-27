# P2. Platform skeleton: **Member 1** (M14, part 1)

> **Owner:** Member 1  
> Part of the CS4032 *Idea Generator with Go / No-Go* project. [Rules](../rule.md) · [Checklist](../project_completion.md) · [Project index](../../README.md)


**Goal:** a **thin version of everything running end to end on Kubernetes** (stubs for all modules, including a minimal UI), plus green PR checks. **[G §12: do not leave K8s to the end]**
**Depends on:** P0, P1. **Done when:** `kubectl get pods -n idea-validator` shows all stub pods Ready, `http://localhost:8080/api/health` answers, the browser can submit one fixed demo idea through the UI → gateway → orchestrator stub → verdict stub and display a fixed result, the first Jenkins delivery pipeline runs, and a PR runs all checks green.

### Steps
1. **Dev stack with Docker Compose** (dev only [G]). `docker-compose.yml`:
   ```yaml
   services:
     postgres:
       image: postgres:16
       environment: { POSTGRES_USER: app, POSTGRES_PASSWORD: "${POSTGRES_PASSWORD:?Set in .env}", POSTGRES_DB: ideas }
       ports: ["5432:5432"]
       volumes: ["pgdata:/var/lib/postgresql/data"]
     redis:
       image: redis:7
       ports: ["6379:6379"]
     qdrant:
       image: qdrant/qdrant:v1.12.4        # pin: check the current stable tag
       ports: ["6333:6333"]
       volumes: ["qdrant:/qdrant/storage"]
   volumes: { pgdata: {}, qdrant: {} }
   ```
   `docker compose up -d` → `docker compose ps`.
2. **Create the cluster and the registry:**
   ```powershell
   k3d registry create idea-registry --port 5001
   k3d cluster create idea-validator --servers 1 --agents 2 `
       --registry-use k3d-idea-registry:5001 `
       -p "8080:80@loadbalancer"
   kubectl config current-context        # must print k3d-idea-validator
   kubectl get nodes                      # 3 nodes Ready
   kubectl create namespace idea-validator
   kubectl config set-context --current --namespace=idea-validator
   ```
   *Why k3d:* k3s ships an embedded NetworkPolicy controller, Traefik (ingress) and metrics-server (for `kubectl top` and the autoscaler). Re-create if needed: `k3d cluster delete idea-validator`.
3. **Service stubs and test dependencies:** create `services/_template/`, then a stub folder for each Python service named in step 6. Each Python stub has `src/main.py` exposing `GET /health`, `GET /ready`, `GET /metrics` (`prometheus-client`), environment-based config, pinned `requirements.txt`, `tests/test_health.py`, and a buildable Dockerfile. Create a root `requirements-dev.txt` with the packages used by the P2 Python CI job, including `pytest`, `ruff`, `mypy`, and `pydantic`, and install `libs/contracts` in that job. The UI is a minimal React/TypeScript Vite project in `services/ui`: commit `package.json`, its lockfile, working `lint` and `test` scripts, a page that can load through the ingress, and a buildable UI image. Add a fixed demo path from that page through the gateway and orchestrator stubs to the verdict stub; mark the displayed result as demo data. P5 develops this same project into the actual product UI. Also create the shared `libs/tracing` stub here (a context manager that prints one JSON trace line to stdout; P11 later adds the batch POST to M13). Trace demo decisions in P2; add traces for each service's real operations when those operations are implemented.
4. **Dockerfile pattern** (guide §4.4, adapted for the repo-root context):
   ```dockerfile
   ARG PYTHON_IMAGE
   FROM ${PYTHON_IMAGE} AS build
   WORKDIR /app
   COPY libs/contracts /contracts
   COPY services/verdict/requirements.txt .
   RUN pip install --no-cache-dir --prefix=/install -r requirements.txt /contracts

   FROM ${PYTHON_IMAGE}
   RUN useradd -m app
   WORKDIR /app
   COPY --from=build /install /usr/local
   COPY services/verdict/src/ ./src/
   USER app
   EXPOSE 8000
   CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```
   Set the `PYTHON_IMAGE` argument default in the Dockerfile to a verified Python 3.12 slim patch tag before the first build. Build: `docker build -f services/verdict/Dockerfile -t localhost:5001/verdict:$sha .`
5. **Build/push script** `scripts/build_push.ps1` for your PC, and for Jenkins the LF shell scripts `scripts/build_all.sh <tag>` and `scripts/push_images.sh <tag>` (the names P10's Jenkinsfile calls): for each deployable service folder (exclude `services/_template`) → `docker build` → tag with `$(git rev-parse --short HEAD)` → `docker push localhost:5001/<name>:<sha>`. **Never tag only `latest` [G].**
6. **Kubernetes base manifests** in `k8s/base/` with a `kustomization.yaml` (deployed with `kubectl apply -k k8s/overlays/local`): one **Deployment + Service per module** (gateway, ui, **profile (M2)**, orchestrator, **scouts (Deployment + Service for on-demand `POST /scout`; the CronJobs are added in P4)**, tools, kb, analyst, ideation, validators, scorer, verdict, critic, agentops) using the guide's §9.2 pattern: `envFrom` ConfigMap, **liveness `/health` + readiness `/ready`**, `resources`, `runAsNonRoot`. Image = `k3d-idea-registry:5001/<name>:<sha>`.
   Postgres / Redis / Qdrant as **StatefulSets with PVCs** (ready for P4/P6).
7. **Ingress** (Traefik, shipped with k3s): `/` → `ui`, `/api` → `gateway`, using a StripPrefix middleware:
   ```yaml
   apiVersion: traefik.io/v1alpha1
   kind: Middleware
   metadata: { name: strip-api, namespace: idea-validator }
   spec: { stripPrefix: { prefixes: ["/api"] } }
   ---
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     name: main
     annotations:
       traefik.ingress.kubernetes.io/router.middlewares: idea-validator-strip-api@kubernetescrd
   spec:
     rules:
     - http:
         paths:
         - { path: /api, pathType: Prefix, backend: { service: { name: gateway, port: { number: 8000 } } } }
         - { path: /,    pathType: Prefix, backend: { service: { name: ui,      port: { number: 80   } } } }
   ```
   If the Middleware API version differs on your k3s (`traefik.containo.us/v1alpha1` on older k3s), run `kubectl api-resources | findstr -i middleware`.
8. **GitHub Actions `pr-checks`** (`.github/workflows/pr-checks.yml`), every PR [G §8.1]: *job names must match the protection contexts*.
   ```yaml
   name: pr-checks
   on: pull_request
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with: { python-version: "3.12" }
         - run: pip install -r requirements-dev.txt
         - run: ruff check libs services && mypy libs/contracts/src libs/platform_stub/src libs/tracing/src
         - run: pytest --import-mode=importlib libs/contracts libs/platform_stub libs/tracing services -q   # P2 stub tests; P3 adds verdict-engine tests here
     ui:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-node@v4
           with: { node-version: 20 }
         - run: cd services/ui && npm ci && npm run lint && npm test -- --run  # P2 stub tests; P5 adds component tests
     docker:
       runs-on: ubuntu-latest
       strategy:
         matrix: { service: [gateway, ui, profile, orchestrator, scouts, tools, kb, analyst, ideation, validators, scorer, verdict, critic, agentops] }   # build and scan every P2 service stub
       steps:
         - uses: actions/checkout@v4
         - run: docker build -f services/${{ matrix.service }}/Dockerfile -t ${{ matrix.service }}:${{ github.sha }} .
         - uses: aquasecurity/trivy-action@v0.36.0
           with: { image-ref: "${{ matrix.service }}:${{ github.sha }}", exit-code: "1", severity: "CRITICAL" }
     manifests:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - run: |
             curl -sSL https://github.com/yannh/kubeconform/releases/download/v0.6.7/kubeconform-linux-amd64.tar.gz | tar xz
             kubectl kustomize k8s/overlays/local | ./kubeconform -strict -ignore-missing-schemas -summary
     secrets:
       runs-on: ubuntu-latest
       permissions:
         contents: read
         pull-requests: read
       steps:
         - uses: actions/checkout@v6
           with: { fetch-depth: 0 }
         - uses: gitleaks/gitleaks-action@v3
           env:
             GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
   ```
   In P3, add the verdict-engine suite to the required `test` job; in P5, add UI component tests; in P6, add the retrieval quality gate with real tests and a baseline. Do not use a missing-test exit code as a passing retrieval gate. Before calling P2 green, confirm every path, package, Dockerfile and manifest referenced by these jobs exists. Keep the Docker matrix and required branch-protection contexts in sync with the deployed services.
   Keep one deliberately failing branch (e.g. a unit test that fails) to capture the **failing run** screenshot; then fix it.
9. **Smoke test** `scripts/smoke_test.sh`: `curl -fsS http://localhost:8080/api/health` and `kubectl get pods -n idea-validator` (no pod not Ready).
10. After the first green run, **apply branch protection** (P1-A step 9).

11. Add the first `Jenkinsfile` and its build, push, deploy and smoke scripts in P2, using the P10 stage outline against the stub services. Create the Jenkins Pipeline job and its required credentials as described in P10, then run it in week 2. P10 hardens delivery and P11 adds the nightly evaluation; do not defer the first pipeline until P10.

### Useful commands
```powershell
kubectl get pods -n idea-validator
kubectl describe pod <name> -n idea-validator
kubectl logs deploy/gateway -n idea-validator
kubectl top pods -n idea-validator
k3d cluster stop idea-validator ; k3d cluster start idea-validator     # pause/resume to save RAM
```
**Screenshots:** all pods running (stub stage), a green + a failing Actions run.
