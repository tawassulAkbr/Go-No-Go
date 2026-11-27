# P11. AgenticOps: **Member 1** (M13)

> **Owner:** Member 1  
> Part of the CS4032 *Idea Generator with Go / No-Go* project. [Rules](../rule.md) · [Checklist](../project_completion.md) · [Project index](../../README.md)


**Goal:** **see** what the agents did, **limit** what they spend, **test** their behaviour, **notice** when they get worse. **[B][G §7]**
**Depends on:** services emitting traces (P4–P9). **Done when:** one run can be traced and replayed, the dashboard shows the six required metrics, a drift report is produced after an ingestion, and the evaluation harness runs as a Job and nightly in Jenkins.

### Windows setup
```powershell
cd C:\dev\idea-validator\services\agentops
py -3.12 -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn[standard] prometheus-client sqlalchemy[asyncio] asyncpg pandas jinja2 pytest
kubectl port-forward svc/agentops 8113:8000 -n idea-validator      # then open http://localhost:8113/dashboard
```
Optional Grafana: `helm repo add prometheus-community https://prometheus-community.github.io/helm-charts` then install `kube-prometheus-stack` into a **separate** namespace (heavy: skip if RAM is tight; a page reading `/metrics` is allowed [G]).

### Build list
1. **Tracing [G]:** `POST /trace` (accepts batches) appends JSON lines to `traces/<run_id>.jsonl` on a PVC, inserts into `traces_index` (`run_id, cost, latency, status`) and prints JSON to stdout; `GET /runs/{id}/trace`. Record format = guide §2.3 (`run_id, step_id, parent_step, agent, kind, tool, input, output, tokens_in/out, cost_usd, latency_ms, retries, model, cache_hit, error, ts`). `libs/tracing` already exists from P2 (stdout only); add the batch sender to `POST /trace` here, used by **every** service; if M13 is down, write to stdout only (fail open).
2. **Replay:** `python -m agentops.replay run_90` re-runs a stored run using **recorded tool results** (the tools client has a replay mode). Show a replay in the report.
3. **Budgets [G]:** `config/budgets.yaml` (tokens, pages, steps, cost per run; per-run and per-day); enforcement in **M3 and M5** (P4/P7); M13 shows spend versus cap and counts "stopped at budget" and "asked user".
4. **Prompt and rubric registry [G]:** list every file in `prompts/` and `rubrics/` with version + hash; each verdict stores the versions used; a CI check fails if a rubric/prompt file changed but its version did not, and a new version requires a new evaluation result in `eval/results/`.
5. **Evaluation harness (`jobs/evaluation/run_eval.py`):** run the system over `eval/labelled/*.jsonl` (labels built in P12; until then use a small fixture set in `eval/fixtures/` so the harness and the Jenkins eval job already work before week 9); compute **agreement**, **confusion matrix**, and **behaviour checks**: tools used, evidence cited on every score, budget kept, **injection resisted** (poisoned fixtures). Writes `eval/results/<timestamp>.json`.
   - **Kubernetes Job** `k8s/eval-job.yaml`; **Jenkins nightly** applies it and `scripts/check_eval.sh` compares with `eval/baseline.json`, exits non-zero if worse than tolerance.
6. **Drift reports [G]:** after each ingestion job → `drift/<date>.json` + dashboard page: **data freshness** (age of newest cards per source), **niche coverage** (cards per niche vs previous run), **shift in verdict distribution** (e.g. total-variation distance vs baseline window).
7. **Dashboard [G]:** cost per verdict · latency per agent · cache hit rate · fallbacks · approvals · blocked injections (from `/metrics` of all services via `prometheus-client`, plus the trace store).
8. **Behaviour tests (recorded responses, no live model) [G]:** invalid JSON from a scorer · tool timeout · empty source · poisoned page. Run in CI.

**Screenshots:** a trace, the dashboard, a drift report. **Decision record #3** (e.g. *All LLM calls go through M5* or *Sensitivity moves the least-confident score*).
