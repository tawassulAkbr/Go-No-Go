# Service interfaces

M1 is the browser entry point. Ingress adds the public prefix `/api` and strips it before forwarding. Paths below are service-relative. All services expose `GET /health` for liveness, `GET /ready` for readiness and `GET /metrics` for metrics. The [shared schemas](../libs/contracts/schemas/) describe the JSON records. Validate records with the Python package to enforce cross-field rules such as matching an evidence ID to its card.

## Public gateway (M1)

| Method and path | Request and result |
|---|---|
| POST /auth/register | Register an account using email and password. |
| POST /auth/login | Authenticate and return an access token. |
| GET /profile, PUT /profile | Read or update the authenticated student's Profile. |
| POST /discover | Start discovery with the saved profile and optional niche. Return the run ID. |
| POST /validate | Start validation with an idea and the saved profile. Return the run ID. |
| GET /runs/{id} | Read status and the result when available. |
| GET /runs/{id}/events | Stream progress, tool activity, spend and requests for input using server-sent events. |
| POST /runs/{id}/answer | Submit an answer to the pending clarification. |
| POST /runs/{id}/approve | Submit an approve or decline decision for the pending action. |
| POST /ideas/{id}/challenge | Recheck a cited claim and return the critic's finding and updated verdict. |
| POST /ideas/{id}/whatif | Apply a proposed change, rescore affected dimensions and return the new idea version. |
| GET /ideas, GET /ideas/{id}/versions | List the student's ideas or an idea's version history. |
| GET /compare?a={id}&b={id} | Return two ideas with comparable dimension scores. |

## Internal services

| Module | Method and path | Request and result |
|---|---|---|
| M4 Scouts | POST /scout | Source, query and run ID trigger on-demand collection through M5. |
| M5 Tools | POST /fetch | Fetch an allowed resource with robots, cache, rate-limit and sanitisation checks. |
| M5 Tools | POST /llm | Forward messages and optional output schema to the hosted model. Return model output and usage for the run. |
| M6 Knowledge Base | POST /search | Query with date, source or niche filters. Return ranked Evidence records. |
| M10 Scorer | POST /score | Score an idea against a dimension rubric and evidence. Return a DimensionScore, including abstention when needed. |
| M11 Verdict | POST /verdict | Accept `EvaluationInput` (idea/run/version, `Profile`, six cited `DimensionScore` records, independent source and platform counts, estimated build hours, optional risk blocker, duplicate product and accepted objection dimensions). Return the shared `Verdict` with gate reasons and rule versions. |
| M11 Verdict | POST /whatif | Accept the same `EvaluationInput`; return the smallest single change that yields stable GO, or `null` when no such change is available. Later phases apply accepted changes and persist version 2. |
| M12 Critic | POST /check | Check claims and their evidence IDs. Return support or rejection per claim. |
| M13 AgenticOps | POST /trace | Append a batch of Trace records. |
| M13 AgenticOps | GET /runs/{id}/trace | Retrieve the steps recorded under the run ID. |
