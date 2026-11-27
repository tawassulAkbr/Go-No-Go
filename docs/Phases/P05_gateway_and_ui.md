# P5. Gateway and Web UI: **Member 2** (M1)

> **Owner:** Member 2  
> Part of the CS4032 *Idea Generator with Go / No-Go* project. [Rules](../rule.md) · [Checklist](../project_completion.md) · [Project index](../../README.md)


**Goal:** the only entrance to the system: login, profile, Discover/Validate screens, live progress, approval prompt, verdict card, history/compare. **[B]**
**Depends on:** P1 contracts, P2 ingress. Uses stubs for M3/M2 until P4/P7 land.
**Done when:** U1, U3 (with fake events), U4 (fake), U6, U9 work in the browser on the cluster, and `npm test` (component tests) is green.

### Windows setup
```powershell
cd C:\dev\idea-validator\services
npm create vite@latest ui -- --template react-ts
cd ui ; npm install
npm install -D vitest jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event eslint
npm install react-router-dom
npm run dev                                         # http://localhost:5173  (proxy /api → gateway)
# gateway
cd ..\gateway ; py -3.12 -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn[standard] pydantic-settings httpx python-jose[cryptography] passlib[argon2] slowapi sse-starlette redis pytest
uvicorn src.main:app --reload --port 8101
```

### 5A. Gateway API (`services/gateway`) is the public endpoints in Guide §3
`POST /auth/register|login`, `GET|PUT /profile`, `POST /discover|/validate`, `GET /runs/{id}`, `GET /runs/{id}/events` (**SSE**), `POST /runs/{id}/answer|/approve`, `POST /ideas/{id}/challenge|/whatif`, `GET /ideas`, `/ideas/{id}/versions`, `/compare`, `GET /metrics`, `/health`, `/ready`.
1. **Login [B]:** passwords hashed (argon2/bcrypt), JWT with expiry, auth dependency on every route except register/login/health.
2. **Rate limits [B]:** per-IP and per-user (`slowapi` with a Redis `storage_uri`, or a Redis token bucket; an in-memory counter breaks when the HPA runs several gateway replicas), stricter on `/auth/*` and run-starting routes. Return 429 with `Retry-After`.
3. **Input validation [B]:** Pydantic models for every body; max lengths; reject unknown fields.
4. **Live progress (U3):** `/runs/{id}/events` streams trace-like events (`agent_started`, `tool_call`, `llm_call`, `cost_update`, `needs_answer`, `needs_approval`, `done`) read from a Redis stream written by M3. Reconnect with `Last-Event-ID`.
5. **No direct calls from the browser to models or scouts [G]:** the gateway is the only thing the UI talks to.
6. Everything else is forwarded to M2/M3 over HTTP using **service DNS names from env vars** (`PROFILE_URL`, `ORCH_URL`), never `localhost`.

### 5B. UI (`services/ui`)
Screens: **Sign up/Login · Profile editor (skills, hours/week, weeks, team size, compute, goal, interests) · Discover (niche/general) · Validate (idea form + clarifying Q&A) · Live run panel (running agent, tool calls, spend, cache hits) · Approval modal (states the cost, Approve/Decline) · Verdict card · What-if (apply → version 2) · Challenge button per claim · History · Compare (two ideas on all six dimensions)**.
- **Verdict card must show [B]:** verdict, the four gates (pass/fail + reason), six scores with **evidence links** (source + URL), weights, confidence, stability (STABLE/BORDERLINE + what flips it). **INSUFFICIENT EVIDENCE variant:** shows *what was missing* and does not guess (U10).
- **API address at runtime [B][G]:** the UI loads `/config.js` (`window.__CONFIG__ = { API_BASE: "/api" }`) generated **at container start** from an env var, not baked in at build time.
- **Component tests (Vitest + Testing Library) [B]:** VerdictCard (all four verdicts + BORDERLINE), InsufficientEvidenceCard, ApprovalPrompt (Approve/Decline call the API), ProfileForm validation, LiveRunPanel renders events, ComparePanel. Add `"test": "vitest"` to `package.json`.
- **UI image:**
  ```dockerfile
  FROM node:20-alpine AS build
  WORKDIR /app
  COPY services/ui/package*.json ./
  RUN npm ci
  COPY services/ui/ .
  RUN npm run build

  FROM nginxinc/nginx-unprivileged:1.27-alpine        # non-root, listens on 8080
  COPY services/ui/nginx/default.conf /etc/nginx/conf.d/default.conf
  COPY --from=build /app/dist /usr/share/nginx/html
  COPY services/ui/docker-entrypoint.sh /docker-entrypoint.d/40-config.sh
  ```
  `docker-entrypoint.sh` writes `/tmp/config.js` from `$API_BASE`; nginx serves it with `location = /config.js { alias /tmp/config.js; }`. The Kubernetes `Service` maps **80 → targetPort 8080**.
- Rebuild/push/deploy: `scripts\build_push.ps1 ui` then `kubectl rollout restart deploy/ui -n idea-validator`.

**Screenshots:** profile page, live run panel, approval prompt, verdict card (these are needed for the report).
