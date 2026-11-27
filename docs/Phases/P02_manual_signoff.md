# Phase 2 workstation and team sign-off

The repository contains the Phase 2 stubs and deployment files. The following checks require a member's configured Windows workstation and GitHub/Jenkins access. Record commands, exit codes and screenshots before marking P2 complete.

## Workstation prerequisites (both members)

1. Follow [P0](P00_windows_setup.md). Save the output and exit code of `scripts/check_env.ps1` and `docker run --rm hello-world` for each member. Install `k3d` if the checker cannot find it.
2. Use a short checkout path such as `C:\dev\idea-validator`. Windows npm command shims fail in this workspace path because `Go&No-Go` contains `&`.
3. Copy `.env.example` to `.env`, set a local `POSTGRES_PASSWORD`, then run `docker compose up -d` and `docker compose ps`. Do not commit `.env` or print its values in screenshots.

## Local cluster (one member, witnessed by the other)

1. Create the `idea-registry` registry and `idea-validator` k3d cluster using the commands in [P2](P02_platform_skeleton.md). Check `kubectl config current-context` equals `k3d-idea-validator` before changing cluster resources.
2. Create the namespace and a secret from the local `.env`: `kubectl create namespace idea-validator`, then `kubectl create secret generic platform-secrets -n idea-validator --from-env-file=.env`. This avoids putting the password on the command line. Never commit or share `.env`.
3. On a committed SHA-tagged branch, run `scripts/build_push.ps1`, then from Git Bash run `bash scripts/deploy.sh <7-character commit SHA>` and `bash scripts/smoke_test.sh`. The smoke test requires at least 17 Ready pods and a marked demo response through UI → gateway → orchestrator → verdict.
4. Capture `kubectl get pods -n idea-validator`, the browser demo at `http://localhost:8080`, and the smoke-test output. Confirm `kubectl get networkpolicy -n idea-validator` lists the P2 egress policy; perform its external-access test in P10.
5. Measure actual pod CPU and memory with `kubectl top pods -n idea-validator` during the demo. Replace P2's provisional requests and limits with measured values in P10 and document the measurements in the report.

## GitHub and Jenkins (team members)

1. Create or link the P2 task issue, push this branch, open a PR into `main` (or into `dev` followed by a reviewed PR into `main`), and have the other member review it. Both members must understand the implementation and log their contributions truthfully.
2. Wait for every PR job to pass. Save one green and one deliberately failing Actions run. After the first green run, protect `main` with the exact job names from the PR checks, require one teammate review, and disallow direct pushes. Save the protection screenshot.
3. Run Jenkins in a container with Docker access. Store its kubeconfig as a Jenkins **file credential** named `kubeconfig`; create a Pipeline-from-SCM job that reads `Jenkinsfile` from the integration target. Run its checkout → build → push → deploy → smoke pipeline and save a green and a deliberately failing run. Jenkins must be able to reach the local k3d registry and cluster. The pipeline uses `SMOKE_BASE_URL=http://host.docker.internal:8080` for Docker Desktop on Windows; set this to the actual reachable ingress URL if Jenkins runs elsewhere.

P2 is complete only when the cluster, CI and Jenkins checks above have observed evidence. Do not use the stub verdict as a real decision about an idea.
