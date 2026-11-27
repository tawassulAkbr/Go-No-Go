# ADR 001: Verdict rule interpretations

**Status:** implementation default; both members must review before final submission.  
**Date:** 2026-11-28  
**AI use:** Codex drafted this record and implementation. The worked-example arithmetic is checked by automated tests; the team still needs to review the choices and explain them.

## Context
The brief fixes the hard-gate order, confidence and weighted-score formulas, but leaves several edge cases open. M11 needs deterministic behavior before M9 provides real scores.

## Decisions
- Available hours = hours per week × weeks available × team size. Compare this with the estimated build effort; report the positive gap (A2).
- Sensitivity changes each weight by a relative ±20%, redistributing the remainder proportionally, and changes the least-confident score by ±1. Ties use the fixed dimension order. This matches the text and the brief's 25→20 worked example (A1, A5).
- Each accepted critic objection reduces its dimension score by 0.5, capped at 1.0 **per dimension**, and reduces that dimension's confidence by 0.1 (A4).
- A floor breach below the no-go threshold is NO-GO. At or above that threshold it is PIVOT; Learning is exempt from the floor (A8).
- One scorer may abstain: its score is excluded and other weights rescaled to 100, but its confidence counts as zero. Two or more abstentions yield INSUFFICIENT_EVIDENCE (A9).
- What-if searches one score change at a time in 0.5 steps and returns the smallest change yielding a stable GO. When only the feasibility gate fails, it may propose reducing estimated effort by the exact hours gap. The Competition 2→3 worked example is a direct recomputation, not the claimed minimum (A10).

## Consequences
Every real verdict can be reproduced from its input and config/rubric versions. M9 must supply cited scores and trustworthy gate facts; M11 does not invent them. The team must confirm these conventions before treating outputs as final project decisions.
