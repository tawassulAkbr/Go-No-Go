# AI-usage log

| Date | Tool | What you asked for | What changed | Why |
|---|---|---|---|---|
| 2026-11-26 | Codex | Review the brief and phase plans, then start Phase 0 | Added the workstation checker and per-member sign-off. Corrected documentation links, setup instructions and phase sequencing. | Make the first phase runnable and align the plan with the repository and course deliverables. |
| 2026-11-26 | Codex | Implement Phase 1 | Added repository scaffolding, contribution hooks and templates, six shared models, exported schemas, validation tests and the API reference. | Give both members a common interface and detect incompatible records before service integration. |
| 2026-11-26 | Codex | Verify Phases 0 and 1 against the course PDFs and publish a child branch | Checked setup evidence, contracts, API coverage and GitHub workflow. Added PIVOT gate validation, regression tests and an issue link in the PR template. | Record the outstanding team checks and prevent a failed hard gate from producing a PIVOT card. |
| 2026-11-27 | Codex | Start Phase 2 on a new branch and follow `rule.md` | Added module stubs, demo UI, Docker and Kubernetes files, PR checks, Jenkins pipeline, tests and a manual sign-off guide. | Establish the early deployable path required by the guide while keeping real verdict logic for P3 and product UI for P5. |
| 2026-11-27 | Codex | Diagnose failing Phase 2 PR checks | Read Actions job logs; corrected the unavailable Trivy action tag and supplied Gitleaks with the required pull-request token. | Allow the image build/scan and secret scan jobs to start and report their real results. |
| 2026-11-27 | Codex | Fix critical image scan findings in the Phase 2 PR | Updated all Python service base images and the UI runtime base image to current Alpine releases; upgraded the UI image's vulnerable `brotli-libs` package. | Remove vulnerable OS packages found by Trivy while retaining the critical severity gate. |
