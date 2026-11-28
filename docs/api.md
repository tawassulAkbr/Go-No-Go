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
| M11 Verdict | POST /verdict | Evaluate six scores, profile, gate inputs and versioned config. Return a Verdict. |
| M11 Verdict | POST /whatif | Evaluate changes against the same inputs and return candidate changes and recomputed outcomes. |
| M12 Critic | POST /check | Check claims and their evidence IDs. Return support or rejection per claim. |
| M13 AgenticOps | POST /trace | Append a batch of Trace records. |
| M13 AgenticOps | GET /runs/{id}/trace | Retrieve the steps recorded under the run ID. |

### Phase 4 service interfaces

All M2 paths are internal. The gateway supplies the authenticated user ID when calling user-scoped endpoints.

| Method and path | Input and result |
|---|---|
| POST /users, POST /users/authenticate | Email and password. Returns the user ID and email. Duplicate registration returns 409 and invalid credentials return 401. |
| GET or PUT /users/{uid}/profile | PUT accepts the shared Profile record. Both return the Profile fields and its integer version. Identical writes preserve the version. |
| POST /users/{uid}/ideas, POST /users/{uid}/ideas/{id}/versions | Accept an idea JSON object and return its ID, version and stored body. |
| GET /users/{uid}/ideas, GET /users/{uid}/history, GET /users/{uid}/ideas/{id}/versions | Return saved versions and associated verdicts, newest first within each idea. |
| GET /users/{uid}/compare?a={id}&b={id} | Returns each idea's latest version and verdicts. |
| PUT or GET /runs/{id} | Persist or resume a run with user, idea, mode, state, state JSON and budget JSON. |
| POST /verdicts, GET /runs/{id}/verdict | Store the shared Verdict and six dimension rows in one transaction, or retrieve the complete verdict. |
| POST /approvals, PUT /approvals/{id}, GET /runs/{id}/approvals | Open an approval with a run ID and reason, submit a boolean decision, or list a run's approvals. |
| POST /cache/write, POST /cache/read | Supply a run ID and typed key. Writes include a JSON value. Reads include the value, cache_hit and X-Cache header. Entries expire after one hour. |
| M4 POST /scout | Supply source, run_id, optional query and limit. Completed pages persist even when a later page fails. |
| M5 POST /fetch | Supply run_id, purpose and either url or connector plus params. Search results include normalized items, cursor, escaped content, source URL, timestamp and flags. |
| M5 POST /llm | Supply run_id, messages, optional output_schema and max_tokens. Returns content, model, token usage and estimated cost. Budget exhaustion returns 402. |

M5 supports hn, github, producthunt, reddit, crates and rubygems. Connector parameters include operation (search or get), query, page (zero-based), size, cursor and id. Hacker News also accepts topstories and newstories. GitHub accepts kind repositories or issues. Service OpenAPI documents the request models.
