# P4. Data foundation: DB/cache, tool layer, scouts, ingestion: **Member 1** (M2, M5, M4, M6i)

> **Owner:** Member 1  
> Part of the CS4032 *Idea Generator with Go / No-Go* project. [Rules](../rule.md) · [Checklist](../project_completion.md) · [Project index](../../README.md)


**Goal:** real data flows in through the *only* internet exit (M5) and ends as **≥ 1,500 idea cards from ≥ 3 sources**, stored in Postgres + the vector store, plus the profile/session/cache service. **[B]**
**Depends on:** P2 (cluster, images). **Done when:** `SELECT source, count(*) FROM cards GROUP BY 1;` shows ≥ 3 sources and ≥ 1,500 rows, re-running ingestion adds **0 duplicates**, and a scout CronJob runs on the cluster.

### Windows setup for this phase
```powershell
cd C:\dev\idea-validator
docker compose up -d                                   # postgres, redis, qdrant from P2
foreach ($s in "profile","tools","scouts") { py -3.12 -m venv services\$s\.venv }
# per service, e.g. profile:
.\services\profile\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic psycopg[binary] redis pydantic-settings httpx pytest pytest-asyncio
pip install -e libs\contracts
docker compose exec postgres psql -U app -d ideas      # SQL shell without installing psql
```
API keys (create each, put in your local `.env` only; **never commit** [B]):
| Source | How | Notes |
|---|---|---|
| Hacker News | none (Firebase API, Algolia search API) | Rate-limit politely |
| GitHub | Settings → Developer settings → **fine-grained (or classic) token with no extra scopes** (public read) | 5,000 req/h authenticated |
| Product Hunt | Create an app at the Product Hunt API dashboard → developer token (GraphQL v2) | Check current terms |
| Reddit | `reddit.com/prefs/apps` → "script" app → client id/secret | **Reddit's API terms changed; read the current terms before use.** If not allowed or unavailable, use HN + GitHub + Product Hunt |
| YC directory | No official API: **only** if its terms and robots.txt allow, otherwise skip | Don't scrape against robots.txt [B] |

Load secrets into the cluster later with (PowerShell): `kubectl create secret generic api-keys -n idea-validator --from-literal=GITHUB_TOKEN=$env:GITHUB_TOKEN --from-literal=PRODUCTHUNT_TOKEN=$env:PRODUCTHUNT_TOKEN`

### 4A. M2: Profile, Session, Cache (`services/profile`)
1. **Layers [B]:** `routes/` (HTTP only) → `services/` (business rules) → `repositories/` (SQL only). No SQL in routes.
2. **Alembic migrations [B]:** `alembic init`, then create tables from the guide's data model (§2): `users`, `profiles`, `ideas`, `idea_versions`, `verdicts`, `dimension_scores`, `conversations`, `approvals`, `traces_index`, `runs`, `cards`, `card_sources`, `niches`, `niche_stats`, `ingestion_runs`. Add `profiles.version` (integer, incremented on every change). `runs` (brief M2: "users, profiles, ideas, versions and **runs**") holds `run_id, user_id, idea_id, mode (discover|validate), state, state_json, budget_json, created_at, updated_at`; M3 persists waiting runs here (P7). `verdicts` stores the `versions` object plus `gates`/`missing_evidence` as JSONB; `dimension_scores` stores `abstained`, `features`, `rubric_version`, `model`.
   ```powershell
   cd services\profile ; alembic revision --autogenerate -m "initial" ; alembic upgrade head
   ```
   On Kubernetes run `alembic upgrade head` as an **initContainer or Job**.
3. **Redis cache [B]:** keys **must** include versions, e.g.
   `verdict:{idea_hash}:{profile_version}:{rubric_version}:{engine_version}` and `retrieve:{query_hash}:{filters_hash}:{kb_version}` (retrieval does not depend on profile or rubric, so those versions are deliberately absent: say so in a decision record or the report); TTL on all. Return a `cache_hit` flag (response header `X-Cache: HIT|MISS` and the trace record's `cache_hit`) so hits are **visible**.
4. **Endpoints** for M1/M3 (document in `docs/api.md`): users, profile (GET/PUT), ideas, versions, verdicts, history, compare data, approvals; `/health`, `/ready` (DB + Redis reachable), `/metrics`.
5. **Tests:** repository tests with a throwaway DB; "profile change bumps version and invalidates old cache key"; "stored password is a hash".

### 4B. M5: Tool Layer (`services/tools`) is the single exit to the internet
1. `POST /fetch` `{url | connector+params, run_id, purpose}` applies in this order: **domain allow-list** (config) → **robots.txt** (`urllib.robotparser`, cached per host) → **per-domain rate limit** (token bucket in Redis) → **cache** (Redis, TTL) → fetch with a clear `User-Agent` and timeout/size limit → **back-off** on 429/5xx → **sanitiser** → return `{content, source, url, fetched_at, flags}`.
2. **Sanitiser [B]:** strip scripts/HTML to text; drop or neutralise instruction-like text aimed at models (e.g. "ignore previous instructions", role markers, tool-call syntax, hidden/zero-width text); wrap output as **data** (`<untrusted_data source=…>…</untrusted_data>`); set `flags.injection_suspected` and increment a metric (`blocked_injections_total`).
3. **Connectors:** `hn` (Firebase `…/v0/topstories|newstories|item/{id}.json`, Algolia search), `github` (REST search repos/issues by topic), `producthunt` (GraphQL), `reddit` (OAuth). One class per connector with the same interface (`search`, `get`).
4. **LLM calls also go through M5** (decision A7 in `rule.md`): add `POST /llm` as a connector whose domain is the hosted-LLM provider's API host. Reason: the brief says **only M5 reaches the internet**, and agents (M8/M9/M12) and the model fallback (M10) need a hosted model. API keys for the LLM then live **only** in M5's Secret. Count tokens/cost here too.
5. **Budget:** per `run_id` page cap enforced here (config from `config/budgets.yaml`) → HTTP 402-style "budget exceeded" the orchestrator turns into an approval request.
6. Label the M5 pod `egress: internet` (used by the NetworkPolicy in P10).
7. **Tests (mocked HTTP):** disallowed domain, robots disallow, rate limit hit, 429 back-off, cache hit, **poisoned page** is neutralised, oversize body is cut.

### 4C. M4: Scout agents (`services/scouts`)
1. A scout = connector + query plan + normaliser. It **never** uses `requests`/`httpx` to the internet directly, only `POST http://tools:8000/fetch`.
2. Query plans per source (examples): HN "Show HN"/"Ask HN" stories (keywords: *I wish there was*, *alternative to*, *launched*), GitHub repos by topic/recent stars, Product Hunt daily/weekly launches, Reddit subreddits permitted by rules.
3. Two run modes: **CLI for CronJobs** (`python -m scouts --source hn --limit 500`) and **on-demand** `POST /scout {source, query, run_id}` for the orchestrator.
4. Failure handling: per-source rate limit, retry with back-off, partial results kept, errors recorded in `ingestion_runs` and the trace.
5. Store raw items (`raw_items` table or `data/raw/*.jsonl`, git-ignored) → hand to M6i.
6. **CronJobs** (`k8s/base/cron-scout-<source>.yaml`, from guide §9.2). The same `scouts` image also runs as the Deployment + Service created in P2 for on-demand `POST /scout`; the CronJobs run `python -m scouts --source ...`: `schedule: "0 */6 * * *"`, `restartPolicy: OnFailure`. **Trigger one manually:**
   `kubectl create job --from=cronjob/scout-hn scout-hn-manual -n idea-validator` then `kubectl logs job/scout-hn-manual -n idea-validator`.

### 4D. M6i: Ingestion job (`jobs/ingestion`)
1. Pipeline: **raw item → card → dedupe → chunk → embed → index → record run.**
2. **Card** (guide §2.1): `id` = `card_` + first 8 hex of `sha1(canonical_url)` (**deterministic ⇒ repeatable, no duplicates**), `name`, `summary`, `problem`, `customer`, `niche_tags`, `stage`, `funding_usd`, `source`, `url`, `published_at`, `fetched_at`, `text`. Extraction = rules first, LLM (via M5) only to fill `problem/customer/niche_tags`.
3. **Dedupe:** canonical URL (strip `utm_*`, trailing slash, `www.`), normalised name, and a near-duplicate check on embeddings (flag at cosine ≥ ~0.92). Upsert, don't insert blindly.
4. **Chunk** `text` into ~200–300-token pieces; **chunk ids = `<card_id>#c<n>`** (keeps the card id for citations [G]).
5. **Embed + index** into Qdrant (payload: `card_id`, `source`, `niche`, `published_at`) and keep Postgres rows in `cards` + `card_sources`.
6. Write an `ingestion_runs` row (`added`, `dropped`, per source counts, duration).
7. **Snapshot** [G]: `scripts/export_snapshot.py` writes `data/snapshot/cards.jsonl.gz` (commit it; ~MBs). `python -m ingestion --from-snapshot` rebuilds the KB offline.
8. **Verify:** run twice; second run `added = 0`. Record counts per source for the report.

**Screenshots/evidence:** `kubectl get cronjob`, a completed scout Job, the card-count query.
