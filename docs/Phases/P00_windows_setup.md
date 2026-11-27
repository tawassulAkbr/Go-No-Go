# P0. Windows workstation setup: **Both members, each on their own PC**

> **Owner:** Both members (each on their own PC)  
> Part of the CS4032 *Idea Generator with Go / No-Go* project. [Rules](../rule.md) · [Checklist](../project_completion.md) · [Project index](../../README.md)


**Goal:** both laptops can build images, run a local Kubernetes, and use the same toolchain.
**Done when:** each member completes the workstation setup, runs the Docker smoke test in §0.4, and gets exit code 0 from the checker in §0.7. Cluster creation belongs to P2.

### 0.1 Requirements
- Windows 10 22H2 (build 19045+) or Windows 11; **16 GB RAM recommended** (8 GB is very tight); **≥ 40 GB free disk**.
- **Virtualization on:** Task Manager → Performance → CPU → *Virtualization: Enabled*. If not, enable *Intel VT-x / AMD SVM* in BIOS/UEFI.

### 0.2 Enable WSL 2 (Admin PowerShell, then reboot)
```powershell
wsl --install -d Ubuntu  # reboot when asked, then open Ubuntu to finish setup
wsl --set-default-version 2
wsl --status
```
Limit WSL memory so Docker doesn't swallow the PC. Create `%UserProfile%\.wslconfig`:
```ini
[wsl2]
# use memory=6GB on an 8–12 GB machine (keep comments on their own line)
memory=8GB
processors=4
swap=4GB
```
Then `wsl --shutdown` (applies on next start).

### 0.3 Install the tools (PowerShell; accept UAC prompts)
```powershell
winget install -e --id Git.Git
winget install -e --id GitHub.cli
winget install -e --id Python.Python.3.12
winget install -e --id OpenJS.NodeJS.LTS
winget install -e --id Microsoft.VisualStudioCode
winget install -e --id Docker.DockerDesktop
winget install -e --id Kubernetes.kubectl
winget install -e --id Helm.Helm
```
If an ID isn't found, run `winget search <name>` and use the ID it shows. **Close and reopen PowerShell** afterwards so `PATH` refreshes.

**k3d** (the local Kubernetes). Pick one:
```powershell
# Option A: Scoop (no admin)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
scoop install k3d
# Option B: Chocolatey (Admin PowerShell, if you already use it)
choco install k3d -y
# Option C: download k3d-windows-amd64.exe from the k3d GitHub releases, rename to k3d.exe, put it on PATH
```

### 0.4 Docker Desktop settings
1. Start Docker Desktop → *Settings → General* → ✅ **Use the WSL 2 based engine**.
2. *Resources → WSL integration* → enable for your Ubuntu distro.
3. **Do NOT enable Docker Desktop's built-in Kubernetes** (we use k3d; the built-in cluster may not enforce NetworkPolicy). **[T]**
4. Test: `docker run --rm hello-world` and `docker compose version`.

### 0.5 Git, GitHub, Python
```powershell
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"      # must match your GitHub email so commits count
git config --global init.defaultBranch main
git config --global core.autocrlf input
git config --global core.longpaths true
gh auth login                                          # GitHub.com → HTTPS → login with browser
```
Python tooling (once per machine; each service gets its own venv later):
```powershell
py -3.12 --version
py -3.12 -m pip install --user pipx ruff mypy pytest pre-commit
```
VS Code extensions: *Python*, *Pylance*, *Docker*, *Kubernetes*, *YAML*, *GitLens*, *EditorConfig*.

### 0.6 Where to put the repo
Use a **short path**: `C:\dev\idea-validator`. Avoid OneDrive/Desktop (sync + long paths cause pain).

### 0.7 Environment check script
Run the [environment checker](../../scripts/check_env.ps1) from the repository root on each Windows PC after reopening PowerShell and starting Docker Desktop.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\check_env.ps1
$LASTEXITCODE
```

Each failed check names the tool or setting to fix. Exit code 0 means all checks passed. Confirm disk space, Docker Desktop settings and the `hello-world` run separately, then record the result in the [completion checklist](../project_completion.md).

### 0.8 Windows pitfalls
| Symptom | Fix |
|---|---|
| `bad interpreter: /bin/sh^M` in a container | CRLF in a `.sh` file → `.gitattributes` with `eol=lf` (P1), then `git add --renormalize .` |
| `docker: error during connect` | Docker Desktop not running / WSL not started |
| Port already in use (5432, 6379, 8080) | `netstat -ano \| findstr :5432` then stop the process, or change the host port in compose |
| Very slow builds | Keep the repo on `C:` (not network drive); close the antivirus real-time scan on the repo folder if allowed |
| `.ps1 cannot be loaded` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
