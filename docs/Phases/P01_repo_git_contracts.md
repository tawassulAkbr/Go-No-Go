# P1. Repository, git workflow, shared contracts: **Both** (split below)

> **Owner:** Both: Member 1 = repo/protection, Member 2 = contracts  
> Part of the CS4032 *Idea Generator with Go / No-Go* project. [Rules](../rule.md) · [Checklist](../project_completion.md) · [Project index](../../README.md)


**Goal:** a protected `main`, an agreed repo layout, and one definition of every JSON schema. **[B][G]**
**Done when:** the other member reviews the first PR before merge and the contracts package imports on both PCs. Enable required checks and branch protection after the first green P2 CI run (P2 step 10).

### P1-A: **Member 1**: repo, protection, hygiene
1. Use the existing project repository. Run `git remote -v` to confirm its GitHub owner and name, then verify both members have push access. Both `tawassulAkbr` and `Ayeshaanjumabbasi3` had push access to `tawassulAkbr/Go-No-Go` on 2026-11-26.
2. **Layout [G]:**
   ```powershell
   $dirs = "libs\contracts","libs\tracing","libs\llm","services","jobs\ingestion","jobs\finetune","jobs\evaluation","rubrics","config","eval","k8s\base","k8s\overlays\local","docs\decisions","scripts",".github\workflows",".github\ISSUE_TEMPLATE"
   $dirs | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }
   ```
   Add a `.gitkeep` to empty folders.
3. **`.gitattributes`** (prevents CRLF disasters):
   ```
   * text=auto eol=lf
   *.ps1 text eol=crlf
   *.png binary
   *.pdf binary
   ```
4. **`.gitignore`**: `.venv/`, `__pycache__/`, `node_modules/`, `.env`, `*.gguf`, `*.safetensors`, `models/`, `data/raw/`, `*.log`, `.pytest_cache/`, `.mypy_cache/`. **`.dockerignore`**: same plus `.git`, `docs/`, `k8s/`.
5. **`.env.example`** with names only: `DATABASE_URL=`, `REDIS_URL=`, `QDRANT_URL=`, `LLM_API_KEY=`, `GITHUB_TOKEN=`, `REDDIT_CLIENT_ID=`, `REDDIT_CLIENT_SECRET=`, `PRODUCTHUNT_TOKEN=`, `JWT_SECRET=`.
6. **Templates:** `.github/pull_request_template.md` (what, why, how tested, AI used? Y/N + log entry, screenshots), issue template (task, acceptance criteria, module, phase).
7. **Pre-commit** (`.pre-commit-config.yaml`) with `ruff`, `ruff-format`, `gitleaks`; run `pre-commit install` on **both** PCs.
8. Maintain the existing rules, phase plans and checklist under `docs/`. Append new AI-assisted changes to [the AI-usage log](../ai-usage-log.md).
9. **Protect `main`: do this AFTER the first CI run** (status check names must exist). Matrix jobs show up as `docker (<service>)`, so copy the **exact** names from the PR's checks list into `contexts` (one entry per matrix service; add an entry whenever you add a service to the matrix). Save as `protection.json`:
   ```json
   {
     "required_status_checks": { "strict": true, "contexts": ["test", "ui", "manifests", "secrets", "docker (gateway)", "docker (verdict)", "docker (tools)", "docker (kb)", "docker (scorer)", "docker (orchestrator)"] },
     "enforce_admins": true,
     "required_pull_request_reviews": { "required_approving_review_count": 1 },
     "restrictions": null
   }
   ```
   ```powershell
   gh api -X PUT repos/<OWNER>/<REPO>/branches/main/protection --input protection.json
   ```
   *If it fails with "upgrade to GitHub Pro", use the Student Developer Pack or make the repo public.*
10. **Create GitHub issues** for every phase task (milestones P0…P13) and assign them (one issue per task [G]).
11. **Screenshot:** protected-`main` settings page + a PR showing required checks.

### P1-B: **Member 2**: shared contracts (JSON schemas) [G §2]
1. Create `libs/contracts` as an installable package (`pyproject.toml`, `src/contracts/`). Pydantic models, **one file per record**: `profile.py`, `card.py`, `evidence.py`, `scores.py` (DimensionScore), `verdict.py`, `trace.py`.
2. Fields: use the guide's JSON examples (§2.1–2.3) as the **minimum**. Key points: `evidence_id` = `<card_id>#c<n>`; `DimensionScore.score` 0–5, `confidence` 0–1, `evidence_ids` list, `features` dict, `rubric_version`, `model`; `Verdict.verdict ∈ {GO,PIVOT,NO-GO,INSUFFICIENT_EVIDENCE}`, `stability ∈ {STABLE,BORDERLINE}`, `gates` (each gate = `{status: pass|fail, reason: str, detail: {...}}` so the card can state the **hours gap**, the **named blocker** and the **named duplicate product**), `missing_evidence: list[str]` (what an INSUFFICIENT_EVIDENCE card shows, U10), `weakest_dimension`, `weights`, `thresholds`, `sensitivity` (`runs`, `flipped`, `flips: [{run, change, verdict}]`), `versions`. An abstained `DimensionScore` has `abstained=true`, `score=0`, `confidence=0`; M11 must never treat it as a real 0 (see P3, A9).
   ```python
   # libs/contracts/src/contracts/scores.py  (sketch)
   from pydantic import BaseModel, Field, model_validator
   from typing import Literal
   Dim = Literal["demand_pain","competition","differentiation","feasibility","risk","learning"]
   class DimensionScore(BaseModel):
       dimension: Dim
       score: float = Field(ge=0, le=5)
       confidence: float = Field(ge=0, le=1)
       evidence_ids: list[str] = []
       features: dict[str, float] = {}
       reason: str = ""
       rubric_version: str
       model: str
       abstained: bool = False
       @model_validator(mode="after")
       def cites_or_abstains(self):
           if not self.abstained and not self.evidence_ids:
               raise ValueError("score must cite evidence ids or abstain")   # [B] rule
           return self
   ```
3. Export JSON Schema: `python -m contracts.export libs/contracts/schemas` from the repository root writes `libs/contracts/schemas/*.json`; commit them.
4. Tests: valid/invalid examples for each model (including the "no evidence → must abstain" rule).
5. Install on your PC: `py -3.12 -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -e libs/contracts pytest; pytest libs/contracts`.
6. Write `docs/api.md`: the endpoint table from Guide §3 (public M1 + internal M5 (`/fetch` **and `/llm`**), M4 `/scout`, M6, M10, M11, M12, M13). This is the contract both members code against.

**Important Docker note [T]:** images are built with the **repo root as build context** (`docker build -f services/x/Dockerfile .`) so every image can `COPY libs/contracts`.
