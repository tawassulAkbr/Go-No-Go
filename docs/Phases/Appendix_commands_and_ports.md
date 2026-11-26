# Appendix: Commands and Port Map

> Index: `README.md`

## A. Command cheat-sheet (PowerShell)

```powershell
# cluster
k3d cluster list ; k3d cluster stop idea-validator ; k3d cluster start idea-validator
kubectl config current-context                            # must be k3d-idea-validator
kubectl get pods,svc,cronjob,hpa -n idea-validator
kubectl logs deploy/<name> -n idea-validator --tail=100 ; kubectl logs -f deploy/<name> -n idea-validator
kubectl describe pod <pod> -n idea-validator ; kubectl top pods -n idea-validator
kubectl rollout status|history|undo deploy/<name> -n idea-validator
kubectl port-forward svc/<name> 9000:8000 -n idea-validator
kubectl create job --from=cronjob/scout-hn scout-hn-manual -n idea-validator

# images
docker build -f services/<name>/Dockerfile -t localhost:5001/<name>:$(git rev-parse --short HEAD) .
docker push localhost:5001/<name>:$(git rev-parse --short HEAD)
docker system df ; docker system prune -f                 # reclaim disk (careful: removes stopped containers)

# git
git switch -c feat/verdict-duplicate-gate
git commit -m "feat(verdict): add duplicate gate"
gh pr create --fill ; gh pr checks ; gh pr view --web
git shortlog -sn --all
```

## B. Port and name map [T]

| Module | Service / folder | Local dev port (8100 + M#) | Cluster Service |
|---|---|---|---|
| M1 | `gateway`, `ui` | 8101, 5173 | `gateway:8000`, `ui:80` |
| M2 | `profile` | 8102 | `profile:8000` |
| M3 | `orchestrator` | 8103 | `orchestrator:8000` |
| M4 | `scouts` (CronJob + on-demand) | 8104 | `scouts:8000` |
| M5 | `tools` (**label `egress=internet`**) | 8105 | `tools:8000` |
| M6 | `kb` | 8106 | `kb:8000` |
| M7 | `analyst` | 8107 | `analyst:8000` |
| M8 | `ideation` | 8108 | `ideation:8000` |
| M9 | `validators` | 8109 | `validators:8000` |
| M10 | `scorer` (+ `llama-server` sidecar) | 8110 | `scorer:8000` |
| M11 | `verdict` | 8111 | `verdict:8000` |
| M12 | `critic` | 8112 | `critic:8000` |
| M13 | `agentops` | 8113 | `agentops:8000` |
| Infra | postgres 5432 · redis 6379 · qdrant 6333 · jenkins 8081 · registry 5001 · ingress 8080 | | |
