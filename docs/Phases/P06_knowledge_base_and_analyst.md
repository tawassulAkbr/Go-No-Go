# P6. Knowledge base (RAG) and niche analyst: **Member 1** (M6, M7)

> **Owner:** Member 1  
> Part of the CS4032 *Idea Generator with Go / No-Go* project. Rules: `../rule.md` · Checklist: `../project_completion.md` · Index: `../README.md`


**Goal:** trustworthy retrieval with citations + niches/trends/gaps. **[B]**
**Depends on:** P4 (cards). **Done when:** hybrid search with reranking answers `/search` with filters; the **≥ 20-query evaluation** exists with a baseline and a **PR gate**; `/niches`, `/trend`, `/gaps` return real data.

### Windows setup
```powershell
cd C:\dev\idea-validator\services\kb
py -3.12 -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn[standard] qdrant-client fastembed rank-bm25 numpy pytest
# only if you choose sentence-transformers instead of fastembed (CPU build, avoids a 2 GB CUDA download):
pip install torch --index-url https://download.pytorch.org/whl/cpu ; pip install sentence-transformers
# analyst
cd ..\analyst ; py -3.12 -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn[standard] scikit-learn pandas numpy qdrant-client pytest
```
Models download on first run (~100–400 MB). **Cache them into the image at build time** so pods don't need internet (the NetworkPolicy blocks it): `RUN python -c "from fastembed import TextEmbedding; from fastembed.rerank.cross_encoder import TextCrossEncoder; TextEmbedding('BAAI/bge-small-en-v1.5'); TextCrossEncoder('Xenova/ms-marco-MiniLM-L-6-v2')"` in the Dockerfile **build** stage and copy the cache dir. **Bake the cross-encoder reranker too, not only the embedder** (check the model name with `TextCrossEncoder.list_supported_models()`).

### 6A. M6: Knowledge Base (`services/kb`)
1. `POST /search` `{query, k, filters:{source, niche, date_from, date_to}}` → ranked **evidence items** (guide §2.2): `evidence_id` (`card_x#cN`), `card_id`, `quote`, `source`, `url`, `retrieved_at`, `score`.
2. **Hybrid:** (a) dense vector search in Qdrant, (b) keyword search (BM25 or Postgres full-text), (c) **fuse** with Reciprocal Rank Fusion, (d) **rerank** top ~30 with a cross-encoder → top k. Filters apply to both legs.
3. **Freshness & coverage tracking [B]:** `GET /stats` → cards per source/niche, newest/oldest `fetched_at`, % stale (> N days), niches below a minimum card count; consumed by drift reports (P11).
4. **Card ids always preserved** (chunk id → card id → URL).
5. **Cache** retrieval in Redis with `kb_version` in the key (via M2's cache helpers).
6. **Retrieval evaluation [B][G]:** `eval/retrieval/queries.jsonl` = **≥ 20 hand-written queries**, each with the card ids a human judged relevant (both members write ~10 each). Script `eval/retrieval/run.py` computes **recall@5, MRR, nDCG@10** for: vector only · keyword only · hybrid · hybrid + rerank. Save `eval/retrieval/baseline.json`.
7. **PR gate** (also remove the temporary `|| [ $? -eq 5 ]` guard from the retrieval step of the P2 workflow): `eval/retrieval/test_gate.py` fails if recall@5 or MRR falls below `baseline.json − tolerance`. In CI it builds a tiny index from `data/snapshot/cards.jsonl.gz` using Qdrant in-memory mode (`QdrantClient(":memory:")`), so no services are needed in GitHub Actions.
8. **Decision record #1** (use the numbers from step 6): *Use hybrid search with reranking* (guide §11.1 template).

### 6B. M7: Niche & Trend Analyst (`services/analyst`)
1. **Cluster** card embeddings (scikit-learn KMeans or HDBSCAN) → candidate niches; **name each niche** (top TF-IDF terms, then a short LLM label via M5). Store in `niches` (`id, name, size, trend_slope`).
2. **Monthly time series:** per niche per month `launches` (cards by `published_at`) and `mentions` → `niche_stats`.
3. **Trend labels:** fit a slope over the last 6–12 months: **rising / flat / saturated** (saturated = large size + flat or falling + many funded/launched competitors).
4. **Gaps [B]:** find recurring complaints / "I wish there was…" / "missing feature" with **no matching product** in the niche. Output `{gap_id, niche, description, evidence_ids[], strength}`.
5. Endpoints: `GET /niches`, `GET /niches/{id}/trend`, `GET /gaps?niche=`, `POST /recompute` (also run by the ingestion job after each run), `/health`, `/ready`.
6. **Tests:** known toy dataset → expected niches/trends; gap list items always carry evidence ids.

**Screenshots:** retrieval comparison table (vector vs keyword vs hybrid vs +rerank), a `/search` result, niche list with trends.
