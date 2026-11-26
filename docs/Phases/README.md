# Build Phases: Index (one file per phase)

**Project:** CS4032 *Idea Generator with Go / No-Go* · **Companions:** `project_completion.md` (plan and checklist) · `rule.md` (rules and limits)
**Tags:** **[B]** = project description · **[G]** = guide · **[T]** = our suggestion (change it if you have a reason, and record the reason).

All commands are for **Windows 10 22H2 / Windows 11** in **PowerShell** unless a block says *Git Bash / WSL* or *inside container*. Where I give versions or package IDs, check them (`winget search <name>`, the tool's release page) because they move.

---

## 0. How the work is split

| | **Member 1: Data & Platform** | **Member 2: Product & Intelligence** |
|---|---|---|
| Modules | **M2**, **M4**, **M5**, **M6**, **M6i**, **M7**, **M13**, **M14** | **M1**, **M3**, **M8**, **M9**, **M10**, **M10t**, **M11**, **M12** |
| Phases owned | **P2**, **P4**, **P6**, **P10**, **P11** | **P3**, **P5**, **P7**, **P8**, **P9** |
| Theme | Everything that collects, stores, retrieves, ships and watches | Everything the user sees, and everything that scores, argues and decides |
| Shared phases | **P0** (each on own PC), **P1** (repo/CI vs contracts), **P12**, **P13** | same |

**Cross-review rule [B]:** every PR is reviewed by the *other* member, so each owner is also the reviewer for the other's phases. Reviewing means actually running it.

| Phase | Name | Owner | Modules | Week [T] |
|---|---|---|---|---|
| P0 | Windows workstation setup | **Both** | tooling | 1 |
| P1 | Repository, git workflow, shared contracts | **Both** (M1: repo; M2: contracts) | M14 (part), schemas | 1 |
| P2 | Platform skeleton: Docker, compose, k3d, CI, **thin slice on Kubernetes** | **Member 1** | M14 | 2 |
| P3 | Verdict Engine and rubrics | **Member 2** | M11 | 2 |
| P4 | Data foundation: DB/cache, tool layer, scouts, ingestion | **Member 1** | M2, M5, M4, M6i | 3–4 |
| P5 | Gateway and Web UI | **Member 2** | M1 | 3–4 |
| P6 | Knowledge base (RAG) and niche analyst | **Member 1** | M6, M7 | 5–6 |
| P7 | Orchestrator, Validate workflow, guardrails | **Member 2** | M3, M9, M12 | 5–6 |
| P8 | Fine-tuning and scoring-model service | **Member 2** | M10t, M10 | 7 |
| P9 | Discover workflow, challenge, what-if, compare | **Member 2** | M8 (+ M3, M1) | 8 |
| P10 | Delivery and hardening: Jenkins, NetworkPolicy, HPA, rollout/rollback | **Member 1** | M14, M5 | 7 |
| P11 | AgenticOps | **Member 1** | M13 | 8 |
| P12 | Labelling, tuning and evaluation | **Both** | M11, M13 | 9 |
| P13 | Report, screenshots, submission | **Both** | docs | 10 |

### Default technology choices [T] (all allowed by the brief: "any library or framework")

| Area | Choice | Why |
|---|---|---|
| Backend | Python 3.12, FastAPI, Pydantic v2, uvicorn | Matches the guide's Dockerfile; schemas = Pydantic |
| DB | PostgreSQL 16, SQLAlchemy 2 + **Alembic** (migrations), psycopg | Brief requires migrations |
| Cache | Redis 7 | [B] |
| Vector store | **Qdrant** (container, PVC) + Postgres full-text for keyword leg | Hybrid = dense + keyword, fused (RRF), then reranked |
| Embeddings / rerank | `fastembed` (ONNX, small images) or `sentence-transformers` (CPU torch) | Runs on CPU in a container |
| UI | React + Vite + TypeScript, Vitest + Testing Library (component tests), served by **nginx** | Brief requires component tests and runtime API address |
| Live progress | Server-Sent Events (SSE) | Simplest for "watch agents live" |
| Orchestration | Hand-written async state machines (LangGraph optional) | Needs explicit retries/timeouts/budget, easy unit tests |
| Hosted LLM | Any provider with a free/cheap tier, behind our own `LLMClient` wrapper | Needed for labels, fallback, agents |
| Scoring model | 1B–3B open model (e.g. Llama-3.2-1B/3B, Qwen2.5-1.5B/3B, Gemma-2-2B), LoRA/QLoRA, served as GGUF on CPU | [B][G] |
| Local Kubernetes | **k3d** (k3s in Docker) | Enforces NetworkPolicy out of the box; has Traefik ingress + metrics-server |
| Registry | k3d local registry (`localhost:5001`) | Free, fast |
| CI/CD | GitHub Actions + Jenkins (in a container) | [B] |
| Dashboard | Small page reading M13 + `/metrics`; Prometheus + Grafana optional | Lighter than a full monitoring stack on a laptop |

### Conventions used in every phase [T]
- Namespace `idea-validator`. Service port **8000**. Labels `app=<module>`; **M5 pods carry `egress=internet`**.
- Image name = module folder name. Tag = short git SHA. Registry host from the laptop: `localhost:5001`; from inside the cluster: `k3d-idea-registry:5001`.
- Each service: `services/<name>/{Dockerfile,requirements.txt,src/,tests/}`.
- Every PR updates `docs/ai-usage-log.md` if AI wrote code in it.

---

## Phase files

| Phase | File | Owner |
|---|---|---|
| P0 | [Windows workstation setup: **Both members, each on their own PC**](shared/P00_windows_setup.md) | Both members (each on their own PC) |
| P1 | [Repository, git workflow, shared contracts: **Both** (split below)](shared/P01_repo_git_contracts.md) | Both: Member 1 = repo/protection, Member 2 = contracts |
| P2 | [Platform skeleton: **Member 1** (M14, part 1)](member1_data_platform/P02_platform_skeleton.md) | Member 1 |
| P3 | [Verdict Engine and rubrics: **Member 2** (M11)](member2_product_intelligence/P03_verdict_engine.md) | Member 2 |
| P4 | [Data foundation: DB/cache, tool layer, scouts, ingestion: **Member 1** (M2, M5, M4, M6i)](member1_data_platform/P04_data_foundation.md) | Member 1 |
| P5 | [Gateway and Web UI: **Member 2** (M1)](member2_product_intelligence/P05_gateway_and_ui.md) | Member 2 |
| P6 | [Knowledge base (RAG) and niche analyst: **Member 1** (M6, M7)](member1_data_platform/P06_knowledge_base_and_analyst.md) | Member 1 |
| P7 | [Orchestrator, Validate workflow, guardrails: **Member 2** (M3, M9, M12)](member2_product_intelligence/P07_orchestrator_validate_guardrails.md) | Member 2 |
| P8 | [Fine-tuning and the scoring-model service: **Member 2** (M10t, M10)](member2_product_intelligence/P08_finetuning_and_scorer.md) | Member 2 |
| P9 | [Discover workflow, challenge, what-if, compare: **Member 2** (M8 + M3, M1 updates)](member2_product_intelligence/P09_discover_challenge_whatif.md) | Member 2 |
| P10 | [Delivery and hardening: **Member 1** (M14 part 2, M5 NetworkPolicy)](member1_data_platform/P10_delivery_and_hardening.md) | Member 1 |
| P11 | [AgenticOps: **Member 1** (M13)](member1_data_platform/P11_agenticops.md) | Member 1 |
| P12 | [Labelling, tuning and evaluation: **Both members**](shared/P12_labelling_and_tuning.md) | Both members |
| P13 | [Report, screenshots, submission: **Both members**](shared/P13_report_and_submission.md) | Both members |
| — | [Appendix: commands and port map](Appendix_commands_and_ports.md) | Both |

Folders: `shared/` (both members) · `member1_data_platform/` · `member2_product_intelligence/`.
