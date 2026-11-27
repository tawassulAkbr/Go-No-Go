# Phase 3 verdict design

## Intent
Implement M11 as deterministic code that turns six cited dimension scores into the shared Verdict record. The Phase 2 fixed demo remains visibly demo-only until the later orchestrator is integrated.

## Constraints and approach
The brief and P3 plan specify the formulas, gate order, sensitivity cases, and API. Use pure Python functions for decisions, Pydantic request validation at the HTTP boundary, and a versioned YAML file mounted as a Kubernetes ConfigMap. The canonical file lives at `k8s/base/config/verdict.yaml` because Kustomize rejects generator files outside its base directory. The alternative of putting decision rules in the API handlers would make them harder to test and reuse; computing verdicts in an LLM would violate the brief.

## Decisions
- Available hours = hours per week × weeks available × team size (A2).
- Accepted objections lower their matching dimension by 0.5, capped at 1.0 per dimension; confidence falls 0.1 per accepted objection (A4).
- One abstention is allowed: omit its score and rescale remaining weights; count its confidence as zero. More than one abstention yields insufficient evidence (A9).
- The sensitivity score perturbation uses the least confident dimension, with stable dimension order as a tie-break (A1). Six weight increases, six decreases, and two score moves yield 14 runs.
- What-if searches one change at a time on a 0.5 point score grid, choosing the smallest stable-GO change. If feasibility is the only failed gate, it proposes reducing estimated effort by the exact hours gap. Other failed gates need new evidence and do not produce a numeric score what-if (A10).
- Every real verdict includes the config, engine, rubric, and weight versions. Invalid or unavailable config makes `/ready` fail and evaluation unavailable.

## Boundaries
P3 does not fabricate evidence, call models, collect cards, or create idea version 2. Later phases provide scored evidence and persist accepted changes. P3 returns the candidate and recomputed outcome for them.
