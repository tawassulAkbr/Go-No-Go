# P12. Labelling, tuning and evaluation: **Both members**

> **Owner:** Both members  
> Part of the CS4032 *Idea Generator with Go / No-Go* project. Rules: `../rule.md` · Checklist: `../project_completion.md` · Index: `../README.md`


**Goal:** thresholds and weights that agree with humans, with honest before/after numbers. **[G §10]**
**Done when:** the labelled set exists, before/after **confusion matrices** are saved, and the final values are in the **ConfigMap**.

1. **Build the labelled set** (`eval/labelled/`): *suggested ≥ 30–40 ideas* with a **profile** each and a **human verdict**; include **clear GOs, clear NO-GOs, borderline/PIVOT, and thin-evidence** (INSUFFICIENT EVIDENCE) cases.
2. **Both members label independently** (`labels_m1.csv`, `labels_m2.csv`: `idea_id, profile_id, verdict, rationale`), compute **Cohen's kappa**, resolve differences together, and **write down who labelled what** [G].
3. **Leakage guard:** `python scripts\check_leakage.py` must pass: no labelled idea in the fine-tuning train set [G].
4. **Run the eval job → BEFORE confusion matrix** (`eval/results/before.json`).
5. **Tune** `T_go`, `T_no`, `floor`, weights (grid/random search script `scripts/tune.py`). Objective: maximise agreement but **penalise "GO where humans said NO-GO" most**; report that error **separately** [G]. **Hold out ~30 %** of the labelled set (tune on 70 %, check on 30 %) so values don't over-fit [G].
6. Justify any change to the weight presets in a short note/DDR [B].
7. **AFTER confusion matrix** (`eval/results/after.json`), plots with `matplotlib` (`pip install matplotlib scikit-learn`).
8. Put final values in `k8s/base/verdict-config.yaml` (ConfigMap) and `config/verdict.yaml`; roll out; **re-run** the evaluation, the model comparison and the retrieval benchmark to get the final report numbers.
