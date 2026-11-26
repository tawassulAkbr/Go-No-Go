# P3. Verdict Engine and rubrics: **Member 2** (M11)

> **Owner:** Member 2  
> Part of the CS4032 *Idea Generator with Go / No-Go* project. Rules: `../rule.md` · Checklist: `../project_completion.md` · Index: `../README.md`


**Goal:** deterministic, unit-tested decision code: gates → score → confidence → verdict → sensitivity → what-if. **[B §5]**
**Depends on:** P1 contracts. **Done when:** `pytest services/verdict` is green, the **worked example from the brief is a test**, and `POST /verdict` + `/whatif` work in a container.

### Windows setup
```powershell
cd C:\dev\idea-validator\services\verdict
py -3.12 -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r ..\..\requirements-dev.txt ; pip install -e ..\..\libs\contracts
pytest -q
uvicorn src.main:app --reload --port 8111      # local run; Swagger at http://localhost:8111/docs
```

### Steps
1. **Config in a file that becomes a ConfigMap** (`config/verdict.yaml`, mounted at runtime, never hard-coded):
   ```yaml
   version: w2
   weights:                      # each preset sums to 100
     startup:        { demand_pain: 25, competition: 20, differentiation: 20, feasibility: 15, risk: 15, learning: 5 }
     portfolio:      { demand_pain: 15, competition: 15, differentiation: 15, feasibility: 25, risk: 10, learning: 20 }
     course_project: { demand_pain: 10, competition: 10, differentiation: 15, feasibility: 35, risk: 10, learning: 20 }
   thresholds: { T_go: 70, T_no: 50, floor: 1.5, min_confidence: 0.5 }
   gates: { min_sources: 3, min_platforms: 2, duplicate_diff_min: 3 }
   challenge: { penalty: 0.5, max_penalty: 1.0, conf_penalty: 0.1 }
   sensitivity: { weight_delta: 0.20, score_delta: 1.0 }
   ```
2. **Pure functions** (no I/O, no randomness, no LLM) in `src/engine.py`:
   - `check_gates(scores, profile, evidence_stats, feasibility_estimate)` → first failing gate in order **Evidence → Feasibility → Risk → Duplicate**.
   - `weighted_score(scores, weights)` = Σ(w·s) / 5 (weights sum 100).
   - `confidence(scores, n_sources)` = 0.7·mean(conf) + 0.3·min(1, n_sources/5).
   - `decide(...)` implements the flow in the brief (Fig. 4). **Floor check covers the first five dimensions only.**
   - `apply_challenge(scores, accepted_objections)` → −0.5 per accepted objection on the matching dimension (cap −1.0), confidence −0.1.
   - `sensitivity(...)`: for each of 6 weights ×{1.2, 0.8} rescale the *others* proportionally so the total stays 100 (`w_i * (100 − w_new)/(100 − w_old)`), plus the least-confident score ±1 clipped to [0,5] → **14 runs**; if any verdict differs → `BORDERLINE` and record which run flips it.
   - `what_would_make_go(...)`: enumerate candidate single changes (raise one dimension in 0.5 steps up to 5; or reduce the hours gap), keep the **smallest change** that yields GO, and confirm it stays GO under the sensitivity runs; return `change`, `new_score`, `new_verdict`.
3. **Feasibility effort:** decide and record (decision record) how "estimated build effort" is compared with "available hours" (`hours_per_week × weeks_available × team_size` is our proposal, rule.md A2).
4. **Endpoints:** `POST /verdict`, `POST /whatif`, plus `/health`, `/ready` (config loaded), `/metrics`. Reload config on version change, and put the **config version, rubric version and weights version** in the response (`versions`).
5. **Unit tests (required by the brief):** every gate (pass + fail), order of gates, each threshold **edge** (69.99 / 70.00, 49.99 / 50.00, floor 1.5 exactly), confidence formula and the 0.5 abstain edge, Learning exempt from floor, challenge cap, 14 sensitivity runs, BORDERLINE shows what flips, what-if finds the smallest change, **determinism** (same input twice → identical output), and the **worked example**:
   - Portfolio, scores 3.5/2.0/3.0/4.0/3.5/4.5 → **70.5 GO**
   - Feasibility weight 25 → 20 → **≈ 69.9 PIVOT** → card says GO, BORDERLINE
   - Competition 2.0 → 3.0 → **73.5**, ≈ **73.1** under the same weights → stable GO
6. **Rubrics** (`rubrics/<dimension>@vN.yaml`, one per dimension): anchors for each score 0–5, `features`, `output_schema`, at least one worked example per level (guide §10 template). Write all six now; M9/M10 use them in P7/P8.
7. **Dockerfile + k8s:** build image, push, replace the stub's image; mount `config/verdict.yaml` via ConfigMap (Member 1 helps in P2 manifests).

**Done when also:** coverage of `engine.py` ≈ 100 % (this is the module the markers will poke).
