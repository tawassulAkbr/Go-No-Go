# Phase 3 implementation plan

1. Add focused failing tests for config loading, gate order and reason payloads, weighted score and confidence. Implement pure functions in `services/verdict/src/engine.py` and versioned `k8s/base/config/verdict.yaml`.
2. Add failing tests for threshold boundaries, floor rules, abstentions, challenge caps, and deterministic output. Implement decision composition into the shared Verdict contract.
3. Add failing tests for all 14 sensitivity runs, the brief's worked example, and smallest stable-GO what-if. Implement both pure searches.
4. Add failing HTTP tests for `/verdict`, `/whatif`, `/ready` and the retained demo path. Implement validated request models and real routes in `services/verdict/src/main.py`.
5. Add six versioned rubric files, a decision record, config mount via Kustomize, Dockerfile and CI dependency changes. Run full Python checks, image/manifests checks, then push a Phase 3 branch as `tawassulAkbr`.
