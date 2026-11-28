# Idea Generator with Go / No-Go

**CS4032 Software Construction and Development — Semester Project** (group of 2)
National University of Computer and Emerging Sciences, Department of Software Engineering

An interactive multi-agent system that helps a student choose a project. It collects startup ideas and products from public sources into a searchable knowledge base, then works in two modes:

- **Discover:** the student gives a profile (skills, hours per week, weeks available, team size, compute, goal: startup / portfolio / course project). Agents debate and propose ideas that fit, including new ideas built from gaps found in the data.
- **Validate:** the student brings an idea. The system returns **GO / PIVOT / NO-GO / INSUFFICIENT EVIDENCE**, with the evidence behind it, what would change it, and how stable the verdict is.

> **The verdict is made by code, not by a language model.** Models produce six evidence-backed scores (0–5). A deterministic, unit-tested engine (M11) applies hard gates, weights, thresholds, confidence and a sensitivity check. This is decision support, not a prediction of success.

The target deployment uses Kubernetes, GitHub Actions and Jenkins. Phase 0 is complete per team confirmation. Phase 1 adds the installable shared contracts and the repository workflow. Phase 2 adds deployable service stubs and a clearly marked demo UI; [workstation and team sign-off](docs/Phases/P02_manual_signoff.md) remains required before claiming a running deployment.

---

## Documentation index

| File | What it is |
|---|---|
| [Project brief](docs/Project.pdf) and [project guide](docs/Project_Guide.pdf) | Course requirements and implementation guidance |
| [Rules](docs/rule.md) | Rules, requirements and limits (tags: **[B]** brief, **[G]** guide, **[T]** our convention). §19 holds our decisions A1–A10 |
| [Completion checklist](docs/project_completion.md) | Master plan: acceptance checklist U1–U10, module checklist M1–M14, submission checklist, timeline |
| [Phase plans P00–P13](docs/Phases/) | What each member builds, in order, with Windows setup |
| [Service interfaces](docs/api.md) | Gateway and internal endpoints used by the modules |
| [Commands and ports](docs/Phases/Appendix_commands_and_ports.md) | Command cheat-sheet and port map |
| `docs/decisions/` | Design decision records (at least 3) |
| `docs/ai-usage-log.md` | Log of what AI tools wrote, what we changed and why |
| `docs/screenshots/` | Report screenshots with captions in `captions.md` |

---

## Table of contents

1. [What the user can do](#what-the-user-can-do)
2. [Architecture](#architecture)
3. [How the verdict is decided](#how-the-verdict-is-decided)
4. [Requirements](#requirements)
5. [Quick start (Windows)](#quick-start-windows)
6. [Step-by-step start](#step-by-step-start)
7. [Using the system](#using-the-system)
8. [Development](#development)
9. [Testing](#testing)
10. [CI/CD](#cicd)
11. [Operating the cluster](#operating-the-cluster)
12. [Repository layout](#repository-layout)
13. [Ports and service names](#ports-and-service-names)
14. [Data collection and ethics](#data-collection-and-ethics)
15. [Troubleshooting](#troubleshooting)
16. [Team](#team)
17. [Known limits](#known-limits)

---

## What the user can do

| # | The user can… |
|---|---|
| U1 | Sign up, log in and save a profile (changes later recommendations) |
| U2 | Ask for ideas in a niche or in general (Discover): a ranked list, each with a verdict and short reason |
| U3 | Watch the agents work live: running agent, tool calls and spend as they happen |
| U4 | Approve or decline an expensive deep search; the system states the cost and waits |
| U5 | Submit their own idea (Validate) and answer only the clarifying questions that change the result |
| U6 | Read a verdict card: verdict, gates, six scores with evidence links, weights, confidence, stability |
| U7 | Ask "what would make this GO?" and apply a change to get **version 2**, computed by the engine |
| U8 | Press **Challenge** on a claim; the critic re-checks it against evidence and defends or removes it |
| U9 | Compare ideas and see history; two ideas compare on all six dimensions |
| U10 | See why a verdict is INSUFFICIENT EVIDENCE: the card says what was missing and does not guess |

The same idea can get different verdicts for different students: a large idea can be GO for a team with 200 free hours and NO-GO for a solo student with 20.

---

## Architecture

Fourteen modules plus two jobs, each in its own container on Kubernetes (namespace `idea-validator`).

| Module | Service folder | Role |
|---|---|---|
| **M1** Web UI + API Gateway | `gateway`, `ui` | Only entrance: login, rate limits, validation, live progress (SSE), verdict card, approval prompt, history |
| **M2** Profile, Session, Cache | `profile` | Postgres (users, profiles, ideas, versions, runs) + Redis (cached verdicts and retrieval); migrations; layered routes → services → repositories |
| **M3** Orchestrator | `orchestrator` | Runs Discover and Validate as testable state machines: parallel agents, retries, timeouts, budget stop, re-run only what changed, full tracing |
| **M4** Scout agents | `scouts` | Bring in new data from ≥ 3 sources; CronJob and on demand |
| **M5** Tool Layer | `tools` | The **single** controlled exit to the internet: allow-list, robots.txt, rate limits, cache, sanitiser, LLM connector |
| **M6** Knowledge Base (RAG) | `kb` | Hybrid search (vector + keyword + RRF) with cross-encoder reranking, filters, citations, freshness and coverage tracking |
| **M6i** Ingestion jobs | `jobs/ingestion` | Raw items → idea cards → dedupe → chunk → embed → index |
| **M7** Niche & Trend Analyst | `analyst` | Named niches, monthly time series, rising / flat / saturated labels, gaps |
| **M8** Idea Generator agents | `ideation` | Ideator, Gap Analyst and Skeptic debate (≤ 3 rounds); defeated ideas are dropped |
| **M9** Validation agents | `validators` | Four scorers in parallel: Demand & Pain, Competition & Differentiation, Feasibility (+ Learning), Risk |
| **M10** Scoring Model | `scorer` | Fine-tuned 1B–3B model (QLoRA, GGUF) with a hosted fallback |
| **M10t** Fine-tuning pipeline | `jobs/finetune` | Offline: data, training, evaluation |
| **M11** Verdict Engine | `verdict` | Plain code, no LLM: gates, weights, thresholds, confidence, sensitivity, what-if |
| **M12** Critic & Guardrails | `critic` | Claim check against evidence, injection defence, input rail, approval above budget |
| **M13** AgenticOps | `agentops` | Traces, budgets, prompt/rubric registry, evaluation harness, drift reports, dashboard |
| **M14** Platform | `.github/`, `Jenkinsfile`, `k8s/` | GitHub protected `main`, GitHub Actions, Jenkins, registry, Kubernetes |

Rules that shape the design:

- Only **M5** can reach the internet (enforced by a Kubernetes NetworkPolicy). Hosted-LLM calls also go through M5, so M5 holds the LLM key.
- The browser talks only to **M1**.
- Every score and claim cites evidence ids, otherwise the scorer abstains.
- Fetched text is data, never instructions.

---

## How the verdict is decided

```
idea + profile + six scored dimensions
 └─ Evidence gate    (≥ 3 sources on ≥ 2 platforms)?   no → INSUFFICIENT EVIDENCE
 └─ Feasibility gate (fits the student's hours)?       no → NO-GO (hours gap stated)
 └─ Risk gate        (no legal/safety blocker)?        no → NO-GO (blocker named)
 └─ Duplicate gate   (no same-user clone, unless Differentiation ≥ 3)? no → NO-GO (product named)
 └─ weighted score 0–100 from the profile's weights
 └─ overall confidence < 0.5 ?                         yes → INSUFFICIENT EVIDENCE
 └─ score ≥ T_go and no first-five score below floor?
        yes → sensitivity check → GO (STABLE) or GO, BORDERLINE (shows what flips it)
        no  → score ≥ T_no ? yes → PIVOT (names weakest dimension) · no → NO-GO
```

- **Six dimensions**, each 0–5 with a confidence and evidence ids: Demand & pain, Competition, Differentiation, Feasibility for this student, Risk, Learning & portfolio value.
- **Weights** come from the goal and sum to 100:

  | Goal | Demand | Compet. | Differ. | Feasib. | Risk | Learn. |
  |---|---|---|---|---|---|---|
  | Startup | 25 | 20 | 20 | 15 | 15 | 5 |
  | Portfolio | 15 | 15 | 15 | 25 | 10 | 20 |
  | Course project | 10 | 10 | 15 | 35 | 10 | 20 |

- **Thresholds** (starting values, tuned on our labelled set): `T_go = 70`, `T_no = 50`, `floor = 1.5` (first five dimensions only; Learning is exempt).
- **Confidence** = 0.7 × mean(dimension confidence) + 0.3 × min(1, sources / 5).
- **Challenge:** each critic-accepted objection lowers the matching score by 0.5 (max 1.0) and its confidence by 0.1.
- **Sensitivity:** 14 runs (6 weights × ±20 % + the least-confident score ±1). Any flip → BORDERLINE.
- **What-if:** the smallest change that gives a stable GO; applying it creates version 2.
- **Worked example** (Portfolio, scores 3.5 / 2.0 / 3.0 / 4.0 / 3.5 / 4.5): 70.5 → GO; with the Feasibility weight 25 → 20 the score is ≈ 69.9 → PIVOT, so the card says **GO, BORDERLINE**; raising Competition to 3.0 gives 73.5 (≈ 73.1 under the same weight change) → stable GO. This is a unit test.

The rules live in `config/verdict.yaml`, deployed as a ConfigMap. Rubrics are versioned files in `rubrics/`.

---

## Requirements

**Machine:** Windows 10 22H2 (build 19045+) or Windows 11, **16 GB RAM recommended** (8 GB is very tight), **≥ 40 GB free disk**, virtualization enabled in BIOS/UEFI.

**Tools** (full instructions in [Phase 0](docs/Phases/P00_windows_setup.md)):

| Tool | Notes |
|---|---|
| WSL 2 + Docker Desktop | WSL 2 backend on. **Do not** enable Docker Desktop's built-in Kubernetes |
| k3d | Local Kubernetes (k3s in Docker). It enforces NetworkPolicy, which this project needs |
| kubectl, Helm | Cluster tooling |
| Git, GitHub CLI | `gh auth login` once |
| Python 3.12, Node.js LTS | For services, tests and the UI |

Cap WSL memory in `%UserProfile%\.wslconfig` (6–8 GB), then `wsl --shutdown`.

Keep the repo on a short path such as `C:\dev\idea-validator` (not OneDrive or Desktop).

**API keys** (put them only in your local `.env`, never commit): GitHub token (public read, no scopes), Product Hunt developer token, a hosted-LLM API key, and optionally Reddit client id/secret if its current API terms allow it. Copy `.env.example` to `.env` and fill the names in.

---

## Quick start (Windows)

The application startup below is planned for P13. For the current workstation setup, follow [Phase 0](docs/Phases/P00_windows_setup.md).

```powershell
git clone https://github.com/<OWNER>/idea-validator.git C:\dev\idea-validator
cd C:\dev\idea-validator
Copy-Item .env.example .env          # then edit .env and fill in your keys
powershell -ExecutionPolicy Bypass -File scripts\bootstrap.ps1
```

`scripts\bootstrap.ps1` does everything in [Step-by-step start](#step-by-step-start): checks tools, starts the dev stack, creates the registry and cluster, builds and pushes every image, creates secrets from `.env`, deploys, waits for pods and prints the URL.

When it finishes, open **http://localhost:8080** and run the smoke test:

```powershell
bash scripts/smoke_test.sh      # Git Bash or WSL; checks /api/health and that no pod is not Ready
```

---

## Step-by-step start

Use this if you prefer to run each step yourself or if `bootstrap.ps1` stops somewhere.

**1. Check your machine**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_env.ps1     # every line must say [OK]
```

**2. Dev stack (Postgres, Redis, Qdrant)**

```powershell
docker compose up -d
docker compose ps
```

**3. Registry and cluster**

```powershell
k3d registry create idea-registry --port 5001
k3d cluster create idea-validator --servers 1 --agents 2 `
    --registry-use k3d-idea-registry:5001 `
    -p "8080:80@loadbalancer"
kubectl config current-context        # must print k3d-idea-validator
kubectl create namespace idea-validator
kubectl config set-context --current --namespace=idea-validator
```

**4. Build and push all images** (tagged by commit SHA, never only `latest`)

```powershell
scripts\build_push.ps1
```

**5. Create secrets** (values come from your `.env`, never from the repo)

```powershell
kubectl create secret generic api-keys -n idea-validator `
  --from-literal=GITHUB_TOKEN=$env:GITHUB_TOKEN `
  --from-literal=PRODUCTHUNT_TOKEN=$env:PRODUCTHUNT_TOKEN `
  --from-literal=LLM_API_KEY=$env:LLM_API_KEY
```

Also create the database password and JWT secret the same way (names are listed in `.env.example`).

**6. Deploy**

```powershell
kubectl apply -k k8s/overlays/local
kubectl get pods -n idea-validator         # wait until every pod is Running/Ready
```

**7. Load the knowledge base without internet** (uses the committed snapshot)

```powershell
python -m ingestion --from-snapshot
```

Alternatively, collect fresh data by triggering a scout manually:

```powershell
kubectl create job --from=cronjob/scout-hn scout-hn-manual -n idea-validator
kubectl logs job/scout-hn-manual -n idea-validator
```

**8. Scoring model (M10)**

The fine-tuned GGUF is a GitHub Release asset (link and SHA-256 in `jobs/finetune/MODEL.md`). Download it, then copy it into the cluster:

```powershell
kubectl apply -f k8s/model-import-pod.yaml
kubectl cp .\model.gguf idea-validator/model-import:/models/model.gguf
kubectl delete pod model-import -n idea-validator
```

If the model is not loaded, M10 falls back to the hosted model and logs each fallback.

**9. Open the app**

Browse to **http://localhost:8080**. The API answers at `http://localhost:8080/api/health`.

**Pause and resume** to save RAM:

```powershell
k3d cluster stop idea-validator
k3d cluster start idea-validator
```

---

## Using the system

1. **Sign up** and log in, then fill in your **profile**: skills, hours per week, weeks available, team size, compute, goal, interests.
2. **Discover:** choose a niche (or general) and start a run. Watch the live panel; approve or decline if the system asks to go over budget.
3. **Validate:** submit your own idea and answer any clarifying question.
4. Read the **verdict card**: verdict, the four gates, six scores with evidence links, weights, confidence and stability.
5. Press **Challenge** on a claim, or ask **"what would make this GO?"** and apply a change to get version 2.
6. Use **History** and **Compare** to see past ideas and two ideas side by side on all six dimensions.
7. Operators: open the AgenticOps dashboard with `kubectl port-forward svc/agentops 8113:8000 -n idea-validator`, then browse to http://localhost:8113/dashboard.

---

## Development

For Phase 1, run these commands from the repository root on each Windows workstation.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e libs/contracts pytest pre-commit
pre-commit install
python -m pytest -q libs/contracts
```

After editing a shared model, regenerate its schemas with `python -m contracts.export libs/contracts/schemas` before running the tests. The service commands below apply once the corresponding services exist.

```powershell
# one service, e.g. the verdict engine
cd services\verdict
py -3.12 -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r ..\..\requirements-dev.txt
pip install -e ..\..\libs\contracts
uvicorn src.main:app --reload --port 8111      # Swagger at http://localhost:8111/docs
```

- Local dev port for module Mn is **8100 + n** (see the port table below). The UI dev server runs on 5173.
- Shared schemas live in `libs/contracts` (Pydantic, one file per record; JSON Schema exported to `libs/contracts/schemas/`). Shared tracing and LLM clients live in `libs/tracing` and `libs/llm`.
- Images are built with the **repo root as build context** so every image can copy `libs/contracts`:
  `docker build -f services/<name>/Dockerfile -t localhost:5001/<name>:$(git rev-parse --short HEAD) .`
- Settings come from environment variables or ConfigMaps. Never hard-code `localhost` or an address in an image.
- Commits follow conventional commits (`feat(verdict): add duplicate gate`). Branches: `feat/<module>-<what>`, `fix/…`, `test/…`, `docs/…`.
- Install the hooks once on each PC: `pre-commit install` (ruff, ruff-format, gitleaks).
- Line endings are LF (`.gitattributes`). Shell scripts must stay LF or they fail inside Linux containers.

---

## Testing

```powershell
pytest services/verdict libs/contracts -q          # Verdict Engine + contracts (includes the worked example)
pytest eval/retrieval -q                            # retrieval quality gate (≥ 20 hand-written queries)
cd services\ui ; npm ci ; npm run lint ; npm test -- --run     # UI component tests
ruff check . ; mypy services libs
```

- **Verdict Engine tests** cover every gate (pass and fail), gate order, each threshold edge (69.99 / 70.00, 49.99 / 50.00, floor 1.5), confidence, the challenge cap, the 14 sensitivity runs, what-if, determinism, abstained-dimension handling and the worked example.
- **Behaviour tests** replay recorded model responses (no live model): invalid JSON from a scorer, a tool timeout, an empty source and a poisoned page.
- **Evaluation harness** (`jobs/evaluation/`) runs the system over `eval/labelled/` and writes agreement, a confusion matrix and behaviour checks to `eval/results/`. It runs as a Kubernetes Job and nightly in Jenkins, compared with `eval/baseline.json`.
- **Leakage guard:** `python scripts\check_leakage.py` fails if any labelled idea appears in the fine-tuning training set.

---

## CI/CD

**GitHub Actions** runs on every pull request and all jobs are required checks on the protected `main` branch: lint and type checks, unit tests (including the Verdict Engine), UI component tests, retrieval quality gate, Docker build and Trivy image scan (fails on CRITICAL), Kubernetes manifest validation, and a secret scan (gitleaks).

**Jenkins** (runs in a Docker container on the developer's PC) delivers after merge: Checkout → Build and tag by commit SHA → Push to the registry → Deploy to the cluster → Smoke test. A nightly run evaluates the deployed system against the stored baseline. A failing stage stops the pipeline and nothing later runs; rollback is `kubectl rollout undo`.

Jenkins reaches the cluster with a kubeconfig stored as a **Jenkins credential**, never in the repository. A GitHub webhook cannot reach a laptop, so Jenkins uses SCM polling every 2 minutes.

`main` is protected: pull requests only, required checks, and one review from the other member.

---

## Operating the cluster

```powershell
kubectl get pods,svc,cronjob,hpa -n idea-validator
kubectl logs deploy/<name> -n idea-validator --tail=100
kubectl describe pod <pod> -n idea-validator
kubectl top pods -n idea-validator

# rollout and rollback
kubectl rollout status deploy/gateway -n idea-validator
kubectl rollout history deploy/gateway -n idea-validator
kubectl rollout undo deploy/gateway -n idea-validator

# NetworkPolicy test: a normal pod must FAIL to reach the internet, M5 must succeed
kubectl run nettest --image=busybox:1.36 --restart=Never --rm -it -n idea-validator -- wget -T 5 -qO- https://example.com
kubectl exec -n idea-validator deploy/tools -- python -c "import urllib.request;print(urllib.request.urlopen('https://example.com',timeout=8).status)"
```

Every workload has liveness and readiness probes, runs as non-root with a pinned image tag, and has CPU and memory requests and limits taken from `kubectl top` measurements. The gateway is autoscaled (HPA) and stateless deployments use a rolling update with `maxUnavailable: 0`.

---

## Repository layout

```
.
├── README.md                     this file
├── services/                     gateway, ui, profile, orchestrator, scouts, tools, kb,
│                                 analyst, ideation, validators, scorer, verdict, critic, agentops
├── jobs/                         ingestion, finetune, evaluation
├── libs/                         contracts, tracing, llm
├── rubrics/                      one versioned file per dimension (e.g. demand_pain@v3.yaml)
├── config/                       verdict.yaml (weights, thresholds), budgets.yaml
├── eval/                         retrieval/, labelled/, results/, baseline.json
├── data/snapshot/                cards.jsonl.gz (offline snapshot of the card data)
├── k8s/                          base/ and overlays/local (Kustomize)
├── jenkins/                      Jenkins image
├── scripts/                      bootstrap, build/push, deploy, smoke test, rollback, tune, leakage check
├── docs/                         brief and guide PDFs, Phases/, rules, checklist, AI log and planned report materials
├── .github/                      workflows/, PR and issue templates
├── Jenkinsfile
├── docker-compose.yml            development only; the target is Kubernetes
└── .env.example                  names only, no secrets
```

---

## Ports and service names

| Module | Service | Local dev port | Cluster Service |
|---|---|---|---|
| M1 | `gateway`, `ui` | 8101, 5173 | `gateway:8000`, `ui:80` |
| M2 | `profile` | 8102 | `profile:8000` |
| M3 | `orchestrator` | 8103 | `orchestrator:8000` |
| M4 | `scouts` | 8104 | `scouts:8000` |
| M5 | `tools` (label `egress=internet`) | 8105 | `tools:8000` |
| M6 | `kb` | 8106 | `kb:8000` |
| M7 | `analyst` | 8107 | `analyst:8000` |
| M8 | `ideation` | 8108 | `ideation:8000` |
| M9 | `validators` | 8109 | `validators:8000` |
| M10 | `scorer` (+ `llama-server` sidecar) | 8110 | `scorer:8000` |
| M11 | `verdict` | 8111 | `verdict:8000` |
| M12 | `critic` | 8112 | `critic:8000` |
| M13 | `agentops` | 8113 | `agentops:8000` |

Infrastructure: Postgres 5432 · Redis 6379 · Qdrant 6333 · Jenkins 8081 · registry 5001 · ingress 8080.

Every service exposes `/health` (alive), `/ready` (can serve now) and `/metrics`.

---

## Data collection and ethics

- The phase-four snapshot contains 2,297 cards from Hacker News, crates.io and RubyGems. GitHub, Product Hunt and Reddit connectors are available subject to source permissions and credentials. See the [phase-four run instructions and verification results](docs/Phases/P04_data_foundation.md#branch-implementation-and-verification-2026-11-28).
- We obey `robots.txt`, apply per-domain rate limits, send a clear `User-Agent`, cache responses and back off on errors.
- No logins and no private data. Each card keeps only a name, public text, public URL and its source; the verdict card links back to the sources.
- Fetched text may contain instructions aimed at models. M5's sanitiser neutralises them, M12 never obeys them, and a poisoned page can never change a score or verdict.
- A snapshot of the card data is committed so the system does not depend on a website being up.
- No keys or passwords are committed. If a secret is ever committed, rotate it first, then clean the history.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `docker: error during connect` | Docker Desktop or WSL is not running |
| `bad interpreter: /bin/sh^M` in a container | CRLF in a `.sh` file: check `.gitattributes`, then `git add --renormalize .` |
| Port already in use (5432, 6379, 8080) | `netstat -ano \| findstr :5432`, stop the process or change the host port |
| `.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| NetworkPolicy test succeeds from a normal pod | You are not on the k3d cluster: `kubectl config current-context` must print `k3d-idea-validator`, and no other pod may carry the `egress: internet` label |
| `/api/health` returns 404 | Traefik middleware API version differs: `kubectl api-resources \| findstr -i middleware` |
| Pods `Pending` or `OOMKilled` | Lower replicas, cap WSL memory, stop unused containers, `docker system df` |
| Rollout stalls | The new image fails readiness: `kubectl rollout undo deploy/<name> -n idea-validator` |
| A pod cannot download a model | Pods have no internet by design: models are baked into images or copied into a PVC |

Never run `kubectl` against a cluster you did not create. Check the context first.

---

## Team

| | Member 1 (Data & Platform) | Member 2 (Product & Intelligence) |
|---|---|---|
| Name / roll no. | _fill in_ | _fill in_ |
| Modules | M2, M4, M5, M6, M6i, M7, M13, M14 | M1, M3, M8, M9, M10, M10t, M11, M12 |

Both members commit code, review each other's pull requests and can explain the whole system. The signed contribution table is in the report and matches `git shortlog -sn --all`.

---

## Known limits

- Decision support only: the verdict is explainable and repeatable, but it is not a prediction of success.
- Weights and thresholds are tuned on our own small labelled set and may not generalise.
- The fine-tuned scorer aims to be cheaper, faster and more consistent than a hosted model, not smarter. See the comparison table and the case where it did not help in the report.
- Jenkins runs as root with the host Docker socket, a lab convenience for a single laptop.
- The system is sized for a development laptop (k3d, CPU-only model serving).
