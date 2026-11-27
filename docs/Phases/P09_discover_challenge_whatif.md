# P9. Discover workflow, challenge, what-if, compare: **Member 2** (M8 + M3, M1 updates)

> **Owner:** Member 2  
> Part of the CS4032 *Idea Generator with Go / No-Go* project. [Rules](../rule.md) · [Checklist](../project_completion.md) · [Project index](../../README.md)


**Goal:** Discover mode (U2) with a limited debate, plus U7/U8/U9. **[B §3.1]**
**Depends on:** P6 (niches/gaps), P7 (Validate), P3 (what-if).
**Done when:** a profile produces a **ranked list of ideas, each with a verdict and short reason**; ideas defeated by evidence are dropped; Challenge and What-if (version 2) work in the UI.

### 9A. M8: Idea Generator agents (`services/ideation`)
1. **Ideator:** input = profile + chosen niches (M7 `/niches`) + gaps (M7 `/gaps`) + KB search (M6); output = candidate ideas **each citing a gap id and evidence ids** [B]. Ideas must fit hours/skills/compute.
2. **Gap Analyst:** adds complaints and missing features from the KB for each candidate; drops gap claims it cannot support.
3. **Skeptic:** argues **against** each idea with evidence (existing products, infeasibility, legal issue). Objections need evidence ids.
4. **Critic (M12):** keeps only evidence-backed objections.
5. **Debate loop [B]:** steps 3→6 repeat **at most 3 rounds**; stop early when a round adds no accepted objection. An idea the Skeptic **defeats with evidence** (e.g. an existing product with the same core features for the same user) is **dropped**.
6. **Clone check (rule 14):** before presenting an idea, compare with the KB (name + embedding similarity); a renamed copy is dropped.
7. **Survivors → Validate workflow** (parallel, within budget). **Rank** by verdict (GO > PIVOT > NO-GO), then score, then confidence. Each result = verdict card + short reason.
8. Demonstrate the **profile effect**: same idea → GO for a team with 200 free hours, NO-GO for a solo student with 20 hours.

**Discover state machine (M3, brief §3 / M3 row):** like Validate, an explicit enum + transition table, unit-tested: `INTAKE → NICHES → IDEATE → GAP_CHECK → SKEPTIC → CRITIC → (loop, ≤ 3 rounds) → VALIDATE_SURVIVORS → RANK → CARD`, plus `WAIT_APPROVAL` over budget.

### 9B. Challenge (U8), What-if (U7), Compare/history (U9)
- `POST /ideas/{id}/challenge {claim_id}` → Skeptic argues the opposite → M12 checks evidence → **defend** or **remove** the claim; accepted objections reduce score by 0.5 (max 1.0) and confidence by 0.1 **via M11**, producing an updated verdict.
- `POST /ideas/{id}/whatif {change}` → create **idea version 2**, **re-run only the scorers that depend on the change**, then M11; the UI shows v1 vs v2.
- `GET /ideas`, `/ideas/{id}/versions`, `/compare?a=&b=` → history list + side-by-side on all six dimensions (UI radar/table).
- **INSUFFICIENT EVIDENCE (U10):** when M11 abstains, the card lists missing evidence (e.g. "only 1 source / 1 platform") and does **not** guess.

**Tests:** Discover transition table (every state and edge); debate stops at 3 rounds; defeated idea is dropped; every idea has gap evidence ids; what-if only re-runs dependants; challenge penalties applied by M11 (not by an LLM).
**Screenshots:** Discover results, challenge, what-if v2, INSUFFICIENT EVIDENCE card, compare view.
