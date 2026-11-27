param([string]$Service = 'all')
$ErrorActionPreference = 'Stop'
$services = @('gateway','ui','profile','orchestrator','scouts','tools','kb','analyst','ideation','validators','scorer','verdict','critic','agentops')
if ($Service -ne 'all' -and $Service -notin $services) { throw "Unknown service: $Service" }
$tag = (git rev-parse --short=7 HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not read commit SHA' }
$selected = if ($Service -eq 'all') { $services } else { @($Service) }
foreach ($name in $selected) {
    docker build -f "services/$name/Dockerfile" -t "localhost:5001/${name}:$tag" .
    if ($LASTEXITCODE -ne 0) { throw "Build failed: $name" }
    docker push "localhost:5001/${name}:$tag"
    if ($LASTEXITCODE -ne 0) { throw "Push failed: $name" }
}
