# project_completion.md — Master Plan and Completion Checklist

**Project:** CS4032 Semester Project — *Idea Generator with Go / No-Go* (group of 2)
**Companion files:** `phases.md` (what each member builds, with Windows setup) · `rule.md` (rules and limits)
**Tags:** **[B]** = project description · **[G]** = guide · **[T]** = our own suggestion

> The PDFs give **no deadline**. The timeline below assumes about 10 weeks. Replace the weeks with your real dates.

---

## 1. The project in one page

A student wants to pick a project. Our system:

1. **Collects** startup ideas/products from ≥ 3 public sources into a knowledge base (RAG) of ≥ 1,500 idea cards.
2. **Organises** them into niches, trends and gaps.
3. **Discover mode:** takes a profile (skills, hours, team size, compute, goal) and proposes ideas that fit, including new ideas built from gaps. Ideator, Gap Analyst and Skeptic agents debate (≤ 3 rounds); the Critic keeps only evidence-backed objections; survivors are validated.
4. **Validate mode:** takes an idea and returns **GO / PIVOT / NO-GO / INSUFFICIENT EVIDENCE** with evidence, "what would make this GO", and a stability flag.
5. **The verdict is made by code, not by an LLM.** Four scorer agents give six 0–5 scores with evidence ids; M11 applies hard gates, weights, thresholds, confidence and sensitivity.
6. Runs as **14 modules, one container each, on Kubernetes**, built and shipped by GitHub Actions + Jenkins, watched by AgenticOps (tracing, budgets, evaluation, drift, dashboard).

The same idea can get different verdicts for different students (200 free hours → GO; solo with 20 hours → NO-GO). [B]

---

## 2. What the user can do: acceptance checklist (U1–U10) [B]

| # | The user can… | Done when… | Main modules | ☐ |
|---|---|---|---|---|
| U1 | Sign up, log in, save a profile | Profile stored, editable, and changes later recommendations | M1, M2 | ☐ |
| U2 | Ask for ideas in a niche or in general (Discover) | Ranked list returned, each with verdict and short reason | M3, M7, M8, M9–M11 | ☐ |
| U3 | Watch the agents work live | Screen shows running agent, its tool calls and spend as they happen | M1 (SSE/WebSocket), M3, M13 | ☐ |
| U4 | Approve or decline an expensive deep search | System states the cost and waits before going over budget | M3, M12, M1 | ☐ |
| U5 | Submit own idea (Validate) and answer clarifying questions | Only questions that change the result are asked, then a verdict card | M1, M3 | ☐ |
| U6 | Read a verdict card | Verdict, gates, six scores with evidence links, weights, confidence, stability | M1, M11 | ☐ |
| U7 | Ask "what would make this GO?" | Concrete changes proposed; one can be applied → **version 2** computed by the engine | M11, M3 | ☐ |
| U8 | Press "Challenge" on a claim | Critic re-checks against evidence and defends or removes it | M8, M12 | ☐ |
| U9 | Compare ideas and see history | Past ideas/versions listed; two ideas compare on all six dimensions | M1, M2 | ☐ |
| U10 | See why a verdict is INSUFFICIENT EVIDENCE | Card says what was missing and does not guess | M11, M1 | ☐ |

---

## 3. Module checklist (M1–M14) [B]

Owner: **P1** = Member 1 (Data & Platform), **P2** = Member 2 (Product & Intelligence). Phase numbers refer to `phases.md`.

| Module | What it is | "Must have" from the brief | Owner | Phase | ☐ |
|---|---|---|---|---|---|
| **M1** Web UI + API Gateway | Only entrance: chat, live progress, verdict card, approval prompt, history | API address set at runtime, login, rate limits, input validation, **component tests** | P2 | P5 | ☐ |
| **M2** Profile, Session, Cache | Postgres (users, profiles, ideas, versions, runs) + Redis (cached verdicts/retrieval) | **Migrations**; cache keys include profile + rubric versions; cache hits visible; **layered backend** (routes/services/repositories) | P1 | P4 | ☐ |
| **M3** Orchestrator | Supervisor running Discover and Validate as state machines | Parallel agents, retries/timeouts, **stop at budget and ask**, re-run only what changed, every decision traced | P2 | P7 | ☐ |
| **M4** Scout agents | Bring in new data from ≥ 3 sources | **CronJob** + on demand, per-source rate limits, failure handling, internet only via M5 | P1 | P4 | ☐ |
| **M5** Tool Layer | The single controlled exit to the internet | Connectors, domain allow-list, rate limits, robots.txt, cache, **sanitiser** (strips instructions aimed at models), **NetworkPolicy** | P1 | P4 + P10 | ☐ |
| **M6** Knowledge Base (RAG) | Searchable memory + source of all evidence | **Hybrid search + reranking**, filters (date/source/niche), card ids, freshness + coverage tracking, quality measured on **≥ 20** queries | P1 | P6 | ☐ |
| **M6i** Ingestion jobs | Fetched pages → idea cards: dedupe, chunk, embed, index | Repeatable, no duplicates, **≥ 1,500 cards from ≥ 3 sources** | P1 | P4 | ☐ |
| **M7** Niche & Trend Analyst | Clusters cards into niches; rising/flat/saturated; gaps | Named niches, monthly time series, gap list feeding M8 and M9 | P1 | P6 | ☐ |
| **M8** Idea Generator agents | Ideator + Gap Analyst + Skeptic debate | Limited rounds (≤ 3), each idea cites gap evidence, defeated ideas dropped | P2 | P9 | ☐ |
| **M9** Validation agents | 4 scorers in parallel: Demand & Pain, Competition & Differentiation, Feasibility, Risk | Own rubric/tools/schema each; computed features + model judgment; **every score cites evidence ids or abstains** | P2 | P7 | ☐ |
| **M10** Scoring Model | Fine-tuned 1B–3B model (LoRA/QLoRA) in its own container | **≥ 300** examples, **≥ 60** hand-checked, hosted fallback, base vs fine-tuned vs hosted comparison | P2 | P8 | ☐ |
| **M10t** Fine-tuning pipeline | Offline: data, training, evaluation, model | Data, scripts and documented commands **in the repo** | P2 | P8 | ☐ |
| **M11** Verdict Engine | Six scores → verdict via fixed rules | **Plain code, no LLM**, deterministic, rules in **ConfigMap**, unit tests for every gate, threshold edge, sensitivity check and what-if | P2 | P3 | ☐ |
| **M12** Critic & Guardrails | Stops unsupported claims and manipulation | Claim check vs evidence, **injection defence** (fetched text is data), input rail, approval above budget | P2 | P7 | ☐ |
| **M13** AgenticOps | Shows, limits and evaluates agent behaviour | Tracing per run, budgets, prompt/rubric registry, evaluation harness, drift reports, dashboard | P1 | P11 | ☐ |
| **M14** Platform | Builds, tests, ships, runs everything | GitHub with protected main + PRs, **GitHub Actions on every PR**, **Jenkins** delivery, one Docker image per module, full Kubernetes deployment with **rollout and rollback** | P1 | P1, P2, P10 | ☐ |

---

## 4. Verdict logic: the part marks will test hardest [B][G]

```
idea + profile + six scored dimensions
 └─ Evidence gate    (≥3 sources, ≥2 platforms)?  no → INSUFFICIENT EVIDENCE
 └─ Feasibility gate (fits student's hours)?       no → NO-GO (hours gap stated)
 └─ Risk gate        (no legal/safety blocker)?    no → NO-GO (blocker named)
 └─ Duplicate gate   (no same-user clone, unless Differentiation ≥ 3)? no → NO-GO (product named)
 └─ weighted score 0–100 from the profile's weights
 └─ overall confidence < 0.5 ?                     yes → INSUFFICIENT EVIDENCE
 └─ score ≥ T_go (70) and no first-five score < floor (1.5)?
        yes → sensitivity check → GO (STABLE) or GO, BORDERLINE (show what flips it)
        no  → score ≥ T_no (50)? yes → PIVOT (name weakest dimension) · no → NO-GO
```

- **Confidence** = 0.7 × mean(dimension confidence) + 0.3 × min(1, sources / 5).
- **Challenge:** each critic-accepted objection → matching score −0.5 (max −1.0), confidence −0.1.
- **Sensitivity:** 6 weights × (+20 %, −20 %) + least-confident score ±1 = **14 runs**; any flip → BORDERLINE.
- **What-if:** smallest change that flips the verdict; applying it creates version 2 (scorers + engine re-run).

**Worked example from the brief (must be a unit test):** Portfolio weights 15/15/15/25/10/20; scores 3.5, 2.0, 3.0, 4.0, 3.5, 4.5 → sum 352.5 ÷ 5 = **70.5 → GO**. Feasibility weight 25 → 20 (freed 5 shared proportionally) → **≈ 69.9 → PIVOT**, so the card says **GO, BORDERLINE**. Raising Competition 2.0 → 3.0 gives **73.5** (≈ **73.1** under the same weight change) → stable GO. *(I re-computed these numbers: they check out.)*

---

## 5. Submission checklist (via GCR) [B]

### 5.1 GitHub repository (markers must be able to open it)
- [ ] Code for all modules
- [ ] Dockerfiles (one per module, ≥ 6 distinct images)
- [ ] `.github/workflows/` (PR checks)
- [ ] `Jenkinsfile`
- [ ] `k8s/` manifests
- [ ] Fine-tuning data + scripts (+ documented commands)
- [ ] Rubrics (`rubrics/`, versioned), config (`config/`), evaluation sets (`eval/`)
- [ ] README: how to start the system step by step (Windows-friendly)
- [ ] `.env.example` (no secrets); secret scan passed; snapshot of card data

### 5.2 Report (PDF, ≤ 10 pages, screenshots not counted)
- [ ] Summary and changes from the given architecture
- [ ] Modules and architecture figure
- [ ] Verdict design: gates, weights, thresholds, rubrics, tuning results with **before/after confusion matrix**, one worked example
- [ ] Knowledge base: sources, card counts, retrieval results
- [ ] Fine-tuning: data, settings, comparison table, **one case where it did not help**
- [ ] AgenticOps results
- [ ] Platform: pipeline, Kubernetes design, **how requests and limits were measured**
- [ ] Known limits and next steps

### 5.3 Screenshots (each with a one-line caption)
- [ ] Protected `main` + a PR with required checks
- [ ] The merge-conflict PR
- [ ] A **green** and a **failing** GitHub Actions run
- [ ] A **green** and a **failing** Jenkins run
- [ ] All pods running
- [ ] A rollout **and** a rollback
- [ ] The NetworkPolicy test (non-M5 pod fails, M5 works)
- [ ] UI: profile · Discover results · verdict card · challenge · what-if version 2 · INSUFFICIENT EVIDENCE
- [ ] A trace · the dashboard · a drift report
- [ ] Retrieval result · fine-tuning comparison

### 5.4 Other
- [ ] AI-usage log (`docs/ai-usage-log.md`)
- [ ] ≥ 3 design decision records (`docs/decisions/`, ≤ 1 page each)
- [ ] Contribution table, **signed by both members**, matching git history

---

## 6. Quantitative targets (never go below) [B][G]

| Target | Minimum |
|---|---|
| Sources / cards | ≥ 3 sources, ≥ 1,500 cards |
| Retrieval queries | ≥ 20 hand-written, with a baseline score used by the PR gate |
| Fine-tuning data | ≥ 300 examples, ≥ 60 hand-checked, split by idea |
| Model size | 1B–3B, LoRA/QLoRA |
| Docker images | ≥ 6 distinct |
| Decision records | ≥ 3 |
| Debate rounds | ≤ 3 |
| Labelled verdict set | Our own; clear GOs, NO-GOs, borderline, thin-evidence (suggest ≥ 30 ideas [T]) |
| Report length | ≤ 10 pages |

---

## 7. Suggested timeline [T]

| Week | Both | Member 1 (Data & Platform) | Member 2 (Product & Intelligence) |
|---|---|---|---|
| 1 | **P0** Windows setup · **P1** repo, protection, contracts | repo + protection + CI skeleton | schemas / contracts, issue plan |
| 2 | | **P2** k3d, registry, compose, Docker pattern, **thin slice of all modules on K8s** | **P3** Verdict Engine (pure code + unit tests) |
| 3 | | **P4** M2, M5, M4, M6i → first cards | **P5** M1 gateway + UI + auth |
| 4 | | P4 continues → **1,500 cards, 3 sources** | P5 continues (live progress, verdict card) |
| 5 | | **P6** M6 hybrid search, 20-query eval, M7 | **P7** M3 + M9 + M12 (Validate end-to-end with hosted LLM) |
| 6 | | P6 continues | P7 continues |
| 7 | | **P10** Jenkins, NetworkPolicy, HPA, probes, limits | **P8** fine-tune dataset → Colab training → serve M10 |
| 8 | | **P11** M13 AgenticOps | **P9** M8 Discover + debate loop, challenge, what-if, compare |
| 9 | **P12** label set, tune thresholds, evaluation | | |
| 10 | **P13** report, screenshots, README polish, rehearse, submit | | |

**Rule of thumb [G]:** by the end of week 2 a thin version of everything must run end to end on Kubernetes. Do not leave Docker, Jenkins and Kubernetes to the last days.

**Critical path:** P0 → P1 → P2 → (P4 → P6) → P8 (needs cards for training data) → P12 → P13. P3, P5, P7, P9 run in parallel with Member 1's data work, using stub data until real cards exist.

---

## 8. Final "definition of done" gate (tick before submitting)

- [ ] Fresh clone on the other member's PC starts with the README steps only
- [ ] `kubectl get pods -n idea-validator` shows all pods **Running/Ready**
- [ ] U1–U10 all demonstrated end to end in the UI
- [ ] Verdict unit tests green; worked example test green
- [ ] No secret in the repo or history (`gitleaks` clean)
- [ ] Rollback demonstrated (`kubectl rollout undo`); NetworkPolicy test captured
- [ ] Nightly Jenkins evaluation has run at least once and compares with the baseline
- [ ] Report ≤ 10 pages; all screenshots captioned
- [ ] AI-usage log complete; contribution table signed and consistent with `git shortlog -sn`
- [ ] Each member can explain every module (cross-walkthrough done)

---

## 9. Risks and mitigations [T]

| Risk | Mitigation |
|---|---|
| Laptop RAM exhausted by Docker + k3d + model server | `.wslconfig` cap; small replicas; quantised GGUF model; set requests/limits from `kubectl top`; stop unused containers |
| Scraping blocked / API limits | Official APIs; cache; keep a **snapshot** of cards; slow cron schedule |
| Fine-tuning gives no gain | Still deliver: the brief asks for a comparison and **one case where it did not help**. Keep the hosted fallback |
| Thresholds over-fit to labelled set | Hold out part of the labelled set; report GO-vs-NO-GO errors separately |
| CI/CD left to the end | P1/P2 deliver green CI and a Jenkins pipeline on stub services in weeks 1–2 |
| Private-repo branch protection unavailable | GitHub Student Developer Pack, or make the repo public after a secret scan |
| One member holds all the knowledge | Cross-review every PR; walkthrough sessions; contribution table honesty |
| Windows CRLF breaks Linux scripts | `.gitattributes` with `eol=lf` from day 1 |

---

## 10. Contribution table (fill in; sign at the end) [G]

| Area | Member 1 (name, roll no.) | Member 2 (name, roll no.) |
|---|---|---|
| Modules owned | M2, M4, M5, M6, M6i, M7, M13, M14 | M1, M3, M8, M9, M10, M10t, M11, M12 |
| Pull requests authored / reviewed | | |
| Approximate hours | | |
| Signature | | |
