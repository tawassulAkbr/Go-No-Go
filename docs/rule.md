# rule.md — Rules, Requirements and Limitations

Project: **CS4032 Semester Project — Idea Generator with Go / No-Go** (group of 2, NUCES Software Engineering)

This file is the single list of things we **must do**, **must not do**, and the **limits** we work inside.
Read it before starting any phase. If a rule here conflicts with the PDFs, the PDFs win; fix this file.

**Source tags**

| Tag | Meaning |
|---|---|
| **[B]** | Stated in `Project.pdf` (the project description / brief) |
| **[G]** | Stated in `Project_Guide.pdf` (setup and reference guide) |
| **[T]** | Our own team convention. Not demanded by the PDFs; we can change it, but only by editing this file in a PR |

Keywords: **MUST** / **MUST NOT** are non-negotiable. **SHOULD** is the default unless we write down a reason.

---

## 1. Team rules

1. Group of **2** students. **Both** members commit code, review each other's pull requests, and must be able to explain the **whole** system, not only their own modules. **[B]**
2. The contribution table is **signed by both members** and **must match the git history**. So neither member may do all the commits, and no work may be committed under the other person's name. **[B]**
3. Each member owns the modules assigned in `phases/`, but every module needs the other member as reviewer. **[T]**
4. One issue per task, linked to its pull request. Small branches with one purpose. **[G]**
5. Before the final submission, each member walks the other through every module (30 minutes each). Anything the other can't explain is rewritten or documented. **[T]**

## 2. AI-usage rules

1. AI coding tools and any library or framework are **allowed**. **[B]**
2. We are **responsible for every line**. Nothing is committed that we cannot explain. **[B]**
3. Keep an **AI-usage log** (`docs/ai-usage-log.md`) with columns: Date · Tool · What you asked for · What you changed · Why. **[B][G]**
4. Update the log in the same PR that contains the AI-written code. **[T]**
5. Design decision records marked "AI use: drafted by AI, numbers checked and changed by us" must be true. Numbers in them must come from our own measurements. **[G]**

## 3. Data collection and ethics

1. Collect data **only through official APIs or pages that allow it**. **[B]**
2. Official APIs first: Hacker News (Firebase), GitHub (REST), Reddit and Product Hunt (official APIs, with keys). **MUST NOT** scrape HTML where an API exists. **[G]**
3. Read each site's terms and **robots.txt**; obey it. **[B][G]**
4. Per-domain **rate limits**, a clear `User-Agent`, caching, back-off on errors. **[G]**
5. **No logins, no private data.** Keep only what an idea card needs: name, public text, public URL. **[B][G]**
6. Every card keeps its **source and URL**, and the verdict card links to them. **[G]**
7. **Fetched text is data, never instructions.** It may contain prompts aimed at models; M12 and M5's sanitiser must neutralise them. **[B][G]**
8. Keep a **snapshot** of the card data in the repo or a release asset so the system doesn't depend on a website being up. **[G]**
9. All internet access goes through **M5 only**. Scouts, agents, the browser and every other module have no route out. **[B]** This includes calls to a hosted LLM (agents, labelling, the M10 fallback): they go through an M5 connector, so M5 holds the LLM API key. **[T]** (A7)

## 4. Secrets and security

1. **Never commit keys or passwords.** **[B]**
2. Commit a `.env.example` with names only. Real values live in `.env` (git-ignored), Kubernetes **Secrets**, and Jenkins **Credentials**. **[G]**
3. The kubeconfig used by Jenkins is a **Jenkins credential**, never in the repository. **[G]**
4. If a secret is ever committed: rotate it first, then clean history. Deleting the file in a later commit is not enough. **[T]**
5. Add secret scanning to the PR checks (for example `gitleaks`). **[T]**
6. Login, rate limits and input validation are required **[B]**; passwords are stored as hashes, never plain text **[G]** (the guide's `users.hash`).
7. Containers run as **non-root**. **[G]**

## 5. Architecture hard rules

1. The system has **14 modules (M1–M14)** plus the jobs M6i, M10t. **Each module is its own container.** The whole system runs on **Kubernetes**. **[B]**
2. **The language model never outputs the verdict.** Models give evidence-backed scores; only the Verdict Engine (M11, plain code, no LLM) decides. **[B]**
3. The browser **MUST NOT** call models or scouts directly. The **only** entrance is M1. **[B][G]**
4. **Never hard-code `localhost`** (or any address) in an image. The API address is set **at runtime** (env var / ConfigMap). **[B][G]**
5. All modules exchange **JSON**. Define each schema once, validate **every** input and output against it, and keep schema files in the repo. **[G]**
6. Every service exposes `/health` (alive) and `/ready` (can serve now, e.g. DB reachable). **[G]**
7. M2's backend is layered: **routes → services → repositories**. **[B]**
8. **Cache keys include the profile version and the rubric version.** Cache hits are visible (in trace and UI). **[B][G]**
9. Every score and claim **cites evidence ids**. A scorer with no evidence **abstains**. Competitors named must exist in the knowledge base. **[B][G]**
10. Orchestration must have **limits**: max retries, timeouts, max debate rounds (3), and a spend budget. No "one long prompt that does everything". **[B][G]**
11. At budget limit, the system **stops and asks the user** (approve or decline). It never silently overspends. **[B]**
12. Re-run **only what changed** (for example, after a what-if, re-run the affected scorers and the engine). **[B]**
13. Every decision is traced under one run id. **[B]**
14. Ideas that are renamed copies of existing products, or that ignore the student's hours, are **bugs**. **[G]**

## 6. Verdict rules (M11)

1. **Verdicts:** `GO`, `PIVOT`, `NO-GO`, `INSUFFICIENT_EVIDENCE`. Stability: `STABLE` or `BORDERLINE`. **[B]**
2. **Six dimensions**, each 0–5 (higher is better for the student), with confidence 0–1 and evidence ids: Demand & pain · Competition · Differentiation · Feasibility for this student · Risk · Learning & portfolio value. **[B]**
3. **Hard gates are checked first, in this order**; a failed gate decides the verdict whatever the score. **[B]**

   | Gate | Passes when | If it fails |
   |---|---|---|
   | Evidence | ≥ 3 independent sources on ≥ 2 platforms | INSUFFICIENT EVIDENCE |
   | Feasibility | Estimated build effort fits the student's hours | NO-GO, hours gap stated |
   | Risk | No legal or safety blocker | NO-GO, blocker named |
   | Duplicate | No existing product with the same core features for the same user, unless Differentiation ≥ 3 | NO-GO, product named |

4. **Weighted score** = Σ(weight × score) scaled to 0–100 (i.e. Σ ÷ 5 when weights sum to 100). Weights come from the goal and **add to 100**. Starting presets (changes must be justified): **[B]**

   | Goal | Demand | Compet. | Differ. | Feasib. | Risk | Learn. |
   |---|---|---|---|---|---|---|
   | Startup | 25 | 20 | 20 | 15 | 15 | 5 |
   | Portfolio | 15 | 15 | 15 | 25 | 10 | 20 |
   | Course project | 10 | 10 | 15 | 35 | 10 | 20 |

5. **Thresholds** (starting values, tunable): `T_go = 70`, `T_no = 50`, `floor = 1.5`. **[B]**
   - GO: score ≥ T_go **and** no score below the floor on the **first five** dimensions (Learning is exempt).
   - PIVOT: T_no ≤ score < T_go, **or** a floor breach when score ≥ T_no (A8). It names the weakest dimension (for a breach, the breaching one).
   - NO-GO: score < T_no, including when a floor is also breached (A8, as in Figure 4).
6. **Confidence** = `0.7 × mean(dimension confidence) + 0.3 × min(1, sources / 5)`. Below **0.5** → INSUFFICIENT EVIDENCE (the system abstains instead of guessing). **[B]**
7. **Challenge:** each objection the critic accepts as evidence-backed lowers the matching score by **0.5** (at most **1.0**) and its confidence by **0.1**. Unsupported objections are discarded. **[B]**
8. **Sensitivity:** recompute with each weight moved ±20 % (the difference shared among the others) and the least-confident score moved ±1. If any run changes the verdict, the card says **BORDERLINE** and shows what flips it. (6 weights × 2 + 2 = **14 runs**, matching the guide's example.) **[B][G]**
9. **What would make this GO:** the engine finds the smallest change that flips the verdict. Applying it re-runs scorers + engine and creates **version 2**. **[B]**
10. Same input → same output (**deterministic**). Rules live in a **ConfigMap**. Unit tests for **every gate, threshold edge, sensitivity check and what-if**. **[B]**
11. Tuning: build **our own labelled set**, build before/after **confusion matrices**, report **"GO where experts said NO-GO" separately** (the worst error), and **do not over-fit** thresholds to the labelled set. **[G]**
12. Nothing that is not the engine may change a verdict. Not the critic, the orchestrator, the UI or a prompt. **[B][G]**
13. The worked example in the brief (§5.4: 70.5 → GO, flips to ≈ 69.9 PIVOT → BORDERLINE; raising Competition to 3.0 gives 73.5 / ≈ 73.1 → stable GO) **MUST** be a unit test. **[T]**

## 7. Knowledge base and retrieval rules (M6, M6i, M7)

1. At least **1,500 idea cards from at least 3 sources**. **[B]**
2. Ingestion is **repeatable without duplicates** (dedupe by URL / canonical id). **[B]**
3. **Hybrid search with reranking**; filters by **date, source and niche**; card ids for citations; **freshness and coverage tracking**. **[B]**
4. Retrieval quality is **measured on at least 20 hand-written queries** (not "by eye"). A retrieval gate fails the PR if the score drops below baseline. **[B][G]**
5. When chunking text, **keep the card id** on every chunk. **[G]**
6. M7 outputs **named niches**, **monthly time series**, rising / flat / saturated labels, and a **list of gaps** that feeds M8 and M9. **[B]**

## 8. Agents and orchestration rules (M3, M8, M9, M12)

1. M3 runs Discover and Validate as **testable state machines**, with parallel agents, retries and timeouts, budget stop, re-run-only-what-changed and full tracing. **[B]**
2. Discover: Ideator → Gap Analyst → Skeptic → Critic, **at most 3 debate rounds**; ideas the Skeptic defeats **with evidence** are dropped; survivors go through Validate. **[B]**
3. Validate runs **4 scorers in parallel** (Demand & Pain, Competition & Differentiation, Feasibility for this student, Risk), each with **its own rubric, tools and output schema**. Scores = **computed features + model judgment**. **[B]**
4. Learning & portfolio value is the sixth dimension. Decide in a decision record which scorer produces it (the brief lists four scorers for six dimensions). **[T]**
5. The Critic (M12) checks each claim against its evidence and removes unsupported claims. It has an **input rail** and an **approval step above budget**. **[B]**
6. Ask the user **only questions that change the result** (clarifying questions). **[B]**
7. If a scorer returns invalid JSON: **retry once, then fall back** to the hosted model, and **log the fallback**. **[G]**
8. Prompts and rubrics are **versioned files**. A change means a **new version and a new evaluation**. Each verdict records the versions used. **[G]**

## 9. Fine-tuning rules (M10, M10t)

1. Base model **1B–3B** open model, **LoRA or QLoRA**. **[B][G]**
2. **At least 300** (idea, evidence, dimension) training examples, covering **all six dimensions and all score levels**. **At least 60 checked by hand** (marked as checked) and used for evaluation. **[B][G]**
3. **Split by idea, not by row**, e.g. 80 / 20. One idea never appears in both train and test. **[G]**
4. **Never train on the labelled verdict set** (used for tuning/measuring only). **[G]**
5. Training data format: **one JSON object per line** (`messages` with system / user / assistant). **[G]**
6. Record settings (rank, learning rate, epochs, batch size) in the repo. Data, scripts and commands are in the repo. **[B][G]**
7. **Do not commit large weights to Git.** Use a release asset or a registry. **[G]**
8. Serve in its own container with `POST /score`, `/health`, `/ready`. Validate every output against the schema. **[G]**
9. Evaluate **base vs fine-tuned vs hosted** in one table: MAE vs human, share within 1 point, valid-JSON rate, share of real evidence ids, latency, cost per score. Include **one case where fine-tuning did not help** and why. **[B][G]**
10. The aim is cheaper, faster, more consistent, **not** smarter than a hosted model. Don't claim otherwise. **[G]**

## 10. AgenticOps rules (M13)

1. **Tracing:** every agent step, tool call and model call writes a trace record under one run id; a **replay** command re-runs a stored run from recorded tool results. **[G]**
2. **Budgets:** caps on tokens, pages, steps and cost per run, enforced in the orchestrator and the tool layer. **[G]**
3. **Prompt and rubric registry** (versioned). **[B][G]**
4. **Evaluation harness** on labelled ideas: agreement, confusion matrix, tools used, evidence cited, budget kept, injection resisted. Runs as a **Kubernetes Job** and **nightly from Jenkins**. **[G]**
5. **Drift reports** after each ingestion: data freshness, niche coverage, shift in verdict distribution. **[G]**
6. **Dashboard:** cost per verdict, latency per agent, cache hit rate, fallbacks, approvals, blocked injections. **[G]**
7. **Behaviour tests with recorded model responses** (no live model in tests). At minimum: invalid JSON from a scorer, a tool timeout, an empty source, a poisoned page. **[G]**

## 11. Git and review rules

1. Create the repository **on day 1**. **[G]**
2. **`main` is protected:** no direct pushes, pull requests only, required status checks, **one review from the other member**. **[B][G]**
3. Conventional commits: `feat(verdict): add duplicate gate`, `fix(kb): dedupe by url`, `test(scouts): add source failure case`. **[G]**
4. **Create one merge conflict on purpose** (two branches edit the same lines), resolve it in a pull request, and **keep the screenshot**. **[G]**
5. Keep a **green** and a **failing** run of GitHub Actions and of Jenkins for the screenshots. **[B]**
6. Branch names: `feat/<module>-<what>`, `fix/…`, `test/…`, `docs/…`. PRs ≤ ~400 changed lines where possible. **[T]**
7. GitHub note: branch protection on a **private** repo needs a paid plan (GitHub Student Developer Pack gives it free). Otherwise make the repo public, **after** checking that no secret is in history. The markers must be able to open the repo. **[B][T]**

## 12. Docker rules

1. **One image per module, at least 6 distinct images.** **[G]**
2. **Multi-stage**, **non-root user**, **pinned versions**, a `.dockerignore`. **[G]**
3. Tag images by **commit SHA**, **never only `latest`**. **[G]**
4. **Scan images in CI** (Trivy; fail on CRITICAL). **[G]**
5. Base image `python:3.12-slim` pattern from the guide (build stage → runtime stage, `USER app`, port 8000, `uvicorn`). **[G]**
6. `docker-compose.yml` is for **development only**. The deployment target is **Kubernetes**. **[G]**
7. Build context is the **repo root** so shared contracts can be copied into every image. **[T]**

## 13. Kubernetes rules

1. Namespace **`idea-validator`**. **[G]**
2. Deployments + Services for M1–M13 (the guide's list omits M2 and M4, but both need a Service; M4 also has CronJobs). StatefulSet/PVC for Postgres, Redis (if persistent), vector store. **CronJobs** for scouts and ingestion; a **Job** for evaluation. ConfigMaps (weights, thresholds, floors, rubric versions, budgets) and Secrets (API keys, DB password). **[B][G]**
3. **Liveness + readiness probes**, **requests and limits** (taken from `kubectl top` measurements, and say so in the report), **non-root**, **pinned image** on **every** workload. **[G]**
4. **Autoscaler** on the API gateway. **[G]**
5. **Rolling update** with `maxUnavailable: 0`; demonstrate **`kubectl rollout undo`** on a bad release. **[G]**
6. **NetworkPolicy:** default-deny egress for the namespace; allow DNS, service-to-service traffic, and **internet egress only for M5 pods** (by label). The cluster's network plugin **must enforce** NetworkPolicy (k3d/k3s does; plain kind/Docker Desktop Kubernetes may not). **[B][G]**
7. **Test the policy:** from a non-M5 pod an external call **fails**; from M5 it **works**. Keep the screenshot. **[G]**
8. UI reaches the API only; nothing else is exposed except through the Ingress. **[G]**
9. Get a **thin version of everything running end to end on Kubernetes early**, then improve each part. **[G]**

## 14. CI/CD rules

**GitHub Actions on every pull request (all are *required checks* on `main`):** **[G]**
lint + type checks · unit tests (incl. Verdict Engine) · component tests (UI) · retrieval quality gate (fails below baseline) · docker build + image scan · Kubernetes manifest validation.

**Jenkins (after merge, and nightly):** checkout → build and tag by commit SHA → push to registry → deploy to the test cluster → smoke test → (nightly) full evaluation compared with the stored baseline. **A failure stops the pipeline and nothing is deployed.** Rollback = `kubectl rollout undo`. **[B][G]**

1. Jenkins runs in a container with access to Docker and the cluster's kubeconfig (as a Jenkins credential). **[G]**
2. A GitHub webhook can't reach Jenkins on a laptop: use **SCM polling** (e.g. every 2 minutes) or a tunnel such as ngrok. **[G]**
3. Nothing is merged with a red check. No `--no-verify`, no force-push to `main`. **[T]**

## 15. Minimum numbers (checklist)

| Item | Minimum | Source |
|---|---|---|
| Group size | 2 | [B] |
| Data sources | ≥ 3 | [B] |
| Idea cards | ≥ 1,500 | [B] |
| Retrieval test queries (hand-written) | ≥ 20 | [B] |
| Fine-tuning examples | ≥ 300 | [B] |
| Hand-checked examples | ≥ 60 | [B] |
| Fine-tuned model size | 1B–3B | [B] |
| Distinct Docker images | ≥ 6 | [G] |
| Design decision records | ≥ 3 (≤ 1 page each) | [B][G] |
| Debate rounds | ≤ 3 | [B] |
| Evidence gate | ≥ 3 independent sources on ≥ 2 platforms | [B] |
| Challenge penalty | −0.5 per accepted objection, max −1.0; confidence −0.1 | [B] |
| Starting thresholds | T_go 70, T_no 50, floor 1.5; confidence floor 0.5 | [B] |
| Report | PDF, **≤ 10 pages**, screenshots not counted | [B] |

## 16. Windows-specific rules [T]

1. Windows 10 22H2 or Windows 11; **virtualization enabled** in BIOS/UEFI; **WSL 2** + **Docker Desktop (WSL 2 backend)**.
2. **Do not** enable Docker Desktop's built-in Kubernetes. We use **k3d** (k3s in Docker) because it enforces NetworkPolicy.
3. Cap WSL memory in `%UserProfile%\.wslconfig` so the laptop stays usable (see `phases/` P0).
4. Keep the repo in a **short path** (`C:\dev\idea-validator`) and run `git config --global core.longpaths true`.
5. **Line endings:** commit `.gitattributes` with `* text=auto eol=lf` (and `*.ps1 text eol=crlf`). Shell scripts with CRLF break inside Linux containers (`bad interpreter`).
6. Shell scripts (`*.sh`) run **inside Linux containers / Jenkins**. On Windows, run them from Git Bash or WSL. PowerShell equivalents live next to them when a member needs one.
7. Use `docker compose` (v2, space), not `docker-compose`.
8. Large model files and Docker volumes eat disk. Run `docker system df` regularly; keep **≥ 40 GB** free.
9. Fine-tuning does **not** run on the laptop. Use **Colab or Kaggle** (free GPU). The laptop only serves the finished, quantised model on CPU.
10. Never run `kubectl` against a cluster you didn't create. Check `kubectl config current-context` shows `k3d-idea-validator` before applying anything.

## 17. Submission rules and limits

Submit through **GCR** with: **[B]**

1. **GitHub repository link** with code, Dockerfiles, workflows, `Jenkinsfile`, `k8s/`, fine-tuning data and scripts, rubrics, evaluation sets and a **README** that lets someone else start the system. **The markers must be able to open it.**
2. **Report (PDF, ≤ 10 pages, not counting screenshots)** with sections: summary and changes from the architecture · modules and architecture figure · verdict design (gates, weights, thresholds, rubrics, tuning results with **before and after confusion matrix**, one worked example) · knowledge base (sources, card counts, retrieval results) · fine-tuning (data, settings, comparison table, **one case where it did not help**) · AgenticOps results · platform (pipeline, Kubernetes design, **how requests and limits were measured**) · known limits and next steps.
3. **Screenshots with one-line captions:** protected main and a PR with required checks · the merge-conflict PR · a green and a failing GitHub Actions run · a green and a failing Jenkins run · all pods running · a rollout and a rollback · the NetworkPolicy test · the interface (profile, Discover results, verdict card, challenge, what-if version 2, INSUFFICIENT EVIDENCE) · a trace, the dashboard and a drift report · the retrieval result and the fine-tuning comparison.
4. **AI-usage log** and **≥ 3 short design decision records** (templates in Guide §11).
5. **Contribution table, signed by both members**, matching the git history.

## 18. "Do not" list (common mistakes from the guide) **[G]**

- ❌ One long prompt that "does everything", with no limit on retries, debate rounds or spending.
- ❌ Caching a verdict without the profile and rubric version in the key.
- ❌ Letting a model (instead of M11) decide or adjust the verdict.
- ❌ Scores or claims with no evidence id, or a competitor that isn't in the knowledge base.
- ❌ Calling the model or scouts directly from the browser, or hard-coding `localhost` in an image.
- ❌ Testing retrieval only by eye, or splitting text without keeping the card id.
- ❌ Ideas that are renamed copies of existing products, or that ignore the student's hours.
- ❌ Leaving Docker, Jenkins and Kubernetes to the last days.

## 19. Ambiguities in the brief: our decisions (fill in, then turn into decision records) [T]

| # | Ambiguity | Our decision | Decided on |
|---|---|---|---|
| A1 | Sensitivity moves the "least confident" score (text, §5.3) vs the "weakest" score (Figure 4) | _Run both variants; report either way. Proposed default: least-confident, as in the text._ | |
| A2 | "Available hours" for the Feasibility gate | _Proposed: `hours_per_week × weeks_available × team_size` vs the estimated build effort._ | |
| A3 | Four scorers but six dimensions: which scorer outputs Learning? | _Proposed: Feasibility scorer also outputs Learning, or a computed-feature scorer._ | |
| A4 | Challenge cap "at most 1.0": per dimension or per idea? | _Proposed: per dimension._ | |
| A5 | "Weights ±20 %": relative (25 → 20) or absolute points? | _Brief's example is relative (25 → 20); use relative._ | |
| A6 | Which third data source(s) and which vector store | _Proposed: Hacker News + GitHub + Product Hunt (+ Reddit only if its current API terms allow); Qdrant._ | |
| A7 | Agents need a hosted LLM, but "only M5 reaches the internet" | _Proposed: route all LLM calls through an M5 connector (`POST /llm`), so M5 holds the key and counts tokens/cost._ | |
| A8 | Floor breach with score < T_no: PIVOT (text §5.3) or NO-GO (Figure 4)? | _Proposed: follow Figure 4: PIVOT only if score ≥ T_no, otherwise NO-GO._ | |
| A9 | A scorer abstains: how does M11 treat that dimension? | _Proposed: exclude it from the weighted sum and rescale the other weights to 100; count it as confidence 0; more than `abstain.max_abstained` (1) abstained dimensions → INSUFFICIENT_EVIDENCE._ | |
| A10 | "Smallest change" in what-if vs the brief's example (Competition 2.0 → 3.0) | _Proposed: search a 0.5 grid and return the smallest change that gives a stable GO; the brief's example is an illustration, tested by direct recomputation._ | |
