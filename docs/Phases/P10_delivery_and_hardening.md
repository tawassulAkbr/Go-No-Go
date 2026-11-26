# P10. Delivery and hardening: **Member 1** (M14 part 2, M5 NetworkPolicy)

> **Owner:** Member 1  
> Part of the CS4032 *Idea Generator with Go / No-Go* project. Rules: `../rule.md` · Checklist: `../project_completion.md` · Index: `../README.md`


**Goal:** Jenkins delivers merged code to the cluster safely; the cluster is locked down and measured. **[B][G §8–9]**
**Depends on:** P2 (cluster, scripts), real services from P4–P7. **Done when:** a merge to `main` is built, pushed, deployed and smoke-tested by Jenkins; a nightly evaluation run exists; NetworkPolicy test, autoscaler, rollout and **rollback** are demonstrated.

### 10A. Jenkins in Docker on Windows
1. **Image** `jenkins/Dockerfile` (CLI tools inside, daemon from the host):
   ```dockerfile
   FROM jenkins/jenkins:lts-jdk17
   USER root
   RUN apt-get update && apt-get install -y docker.io curl git && rm -rf /var/lib/apt/lists/*
   RUN curl -fsSLo /usr/local/bin/kubectl https://dl.k8s.io/release/v1.30.0/bin/linux/amd64/kubectl && chmod +x /usr/local/bin/kubectl
   ```
   *(Jenkins runs as root here so it can use the Docker socket: a lab convenience; mention it in the report's limits.)*
2. **Run** (joins the k3d network so it can reach the cluster API):
   ```powershell
   docker build -t idea-jenkins .\jenkins
   docker run -d --name jenkins --restart unless-stopped --user root `
     --network k3d-idea-validator `
     -p 8081:8080 -p 50000:50000 `
     -v jenkins_home:/var/jenkins_home `
     -v /var/run/docker.sock:/var/run/docker.sock `
     idea-jenkins
   docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
   ```
   Open `http://localhost:8081`, finish the wizard, install suggested plugins + **Pipeline**, **Git**, **Credentials Binding**, **Timestamper**. *(If Git Bash rewrites the socket path, use `//var/run/docker.sock`.)*
3. **Kubeconfig as a Jenkins credential [G]:**
   ```powershell
   k3d kubeconfig get idea-validator > kubeconfig-jenkins.yaml
   ```
   Edit `server:` to `https://k3d-idea-validator-serverlb:6443` (resolvable inside the k3d network). If you get a TLS name error: lab-only fix: delete `certificate-authority-data` and add `insecure-skip-tls-verify: true`, and note it in the report. Upload via *Manage Jenkins → Credentials → Global → Add → Secret file*, ID **`kubeconfig`**. **Delete the local file afterwards; never commit it.**
4. **GitHub access:** add a GitHub token credential (*Username with password*, ID `github`). Create a **Pipeline job** (*Pipeline script from SCM*, repo URL, branch `main`, script path `Jenkinsfile`).
5. **Trigger:** webhooks can't reach a laptop → **SCM polling** `H/2 * * * *`, or a tunnel (`ngrok http 8081`) if you prefer webhooks [G]. **Nightly eval:** `cron('H 2 * * *')`.

### 10B. `Jenkinsfile` (extends the guide's example)
```groovy
pipeline {
  agent any
  options { timestamps() }
  triggers { pollSCM('H/2 * * * *'); cron('H 2 * * *') }
  environment {
    TAG = "${env.GIT_COMMIT.take(7)}"
    PUSH_REG = "localhost:5001"              // used by the docker daemon on the host
    CLUSTER_REG = "k3d-idea-registry:5001"   // used by the cluster
    NS = "idea-validator"
  }
  stages {
    // Unit tests already ran as required checks in GitHub Actions before merge; Jenkins focuses on delivery.
    stage('Build')  { steps { sh './scripts/build_all.sh $TAG' } }               // docker build per service, tagged by SHA
    stage('Push')   { steps { sh './scripts/push_images.sh $TAG' } }
    stage('Deploy') {
      steps { withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
        sh './scripts/deploy.sh $TAG'          // kubectl set image deploy/<svc> <svc>=$CLUSTER_REG/<svc>:$TAG ; kubectl rollout status
      } }
    }
    stage('Smoke')  { steps { withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) { sh './scripts/smoke_test.sh' } } }
    stage('Eval')   {
      when { triggeredBy 'TimerTrigger' }
      steps { withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
        sh 'kubectl apply -f k8s/eval-job.yaml && ./scripts/check_eval.sh'          // compares with eval/baseline.json
      } }
    }
  }
  post {
    failure {
      withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
        sh './scripts/rollback.sh || true'     // kubectl rollout undo for services changed in this run
      }
      echo 'Pipeline failed, nothing promoted'
    }
  }
}
```
**Rule [G]:** a failing stage stops the pipeline, so nothing later (deploy) runs. Make the shell scripts LF (`.gitattributes`), executable (`git update-index --chmod=+x scripts/*.sh`) and have them use `set -euo pipefail`.
**Screenshots:** one **green** and one **failing** Jenkins run (break `smoke_test.sh` on a branch on purpose, then fix).

### 10C. NetworkPolicy: only M5 reaches the internet [B][G §9.3]
`k8s/base/networkpolicy.yaml`:
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny-egress, namespace: idea-validator }
spec: { podSelector: {}, policyTypes: [Egress] }
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-dns-and-internal, namespace: idea-validator }
spec:
  podSelector: {}
  policyTypes: [Egress]
  egress:
  - to: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } } }]
    ports: [{ protocol: UDP, port: 53 }, { protocol: TCP, port: 53 }]
  - to: [{ podSelector: {} }]                       # traffic between our own services
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-internet-m5, namespace: idea-validator }
spec:
  podSelector: { matchLabels: { egress: internet } }   # ONLY the tool-layer pods carry this label
  policyTypes: [Egress]
  egress: [{ to: [{ ipBlock: { cidr: 0.0.0.0/0 } }] }]
```
**Test it (screenshot) [G]:**
```powershell
# 1) a normal pod (no egress=internet label) must FAIL to reach the internet
kubectl run nettest --image=busybox:1.36 --restart=Never --rm -it -n idea-validator -- wget -T 5 -qO- https://example.com
#    expected: timeout / "download timed out"
# 2) the tool layer must SUCCEED
kubectl exec -n idea-validator deploy/tools -- python -c "import urllib.request;print(urllib.request.urlopen('https://example.com',timeout=8).status)"
#    expected: 200
```
If the first command *succeeds*, your CNI is not enforcing policies; check `kubectl config current-context` is the **k3d** cluster (not Docker Desktop's built-in one). Make sure **no other pod** (scouts, agents, scorer) has the `egress: internet` label; they use M5.

### 10D. Kubernetes hardening checklist [G]
- [ ] Every workload: **liveness + readiness probes**, **non-root** (`securityContext.runAsNonRoot: true`), **pinned image tag (SHA)**, **requests and limits**.
- [ ] **Requests/limits from measurements:** `scripts/measure_resources.ps1`:
  ```powershell
  1..60 | ForEach-Object { kubectl top pods -n idea-validator --no-headers | Add-Content data\top.txt ; Start-Sleep 10 }
  ```
  Run it during a realistic workflow (a Discover + several Validate runs), take typical and peak CPU/memory per pod, set requests ≈ typical and limits ≈ 1.5× peak, and put the table in the report.
- [ ] **Autoscaler on the gateway:** `kubectl autoscale deploy gateway --cpu-percent=60 --min=1 --max=4 -n idea-validator` (or an HPA manifest). Load test with `docker run --rm -i grafana/k6 run - < loadtest.js`; capture `kubectl get hpa -w`.
- [ ] **Rolling update:** `strategy: { type: RollingUpdate, rollingUpdate: { maxUnavailable: 0, maxSurge: 1 } }` on stateless deployments.
- [ ] **Rollback demo:** build a deliberately bad image (fails readiness), then
  ```powershell
  kubectl set image deploy/gateway gateway=k3d-idea-registry:5001/gateway:bad1 -n idea-validator
  kubectl rollout status deploy/gateway -n idea-validator --timeout=60s     # stalls/fails
  kubectl rollout undo deploy/gateway -n idea-validator
  kubectl rollout history deploy/gateway -n idea-validator
  ```
  Screenshot the **rollout** (good update) and the **rollback**.
- [ ] ConfigMaps: `verdict-config` (weights, thresholds, floors), `rubric-versions`, `budgets`. Secrets: API keys, DB password (created by `kubectl create secret`, never committed).
- [ ] `docker system df` and `k3d cluster stop` when not working, to save RAM and disk.
