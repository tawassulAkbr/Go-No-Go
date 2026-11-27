# Run from Windows PowerShell after completing docs/Phases/P00_windows_setup.md.
$ErrorActionPreference = 'Stop'
$failed = $false

function Invoke-Tool {
    param([string]$Name, [string[]]$Arguments)
    $tool = Get-Command $Name -CommandType Application -ErrorAction Stop | Select-Object -First 1
    # Native tools can write informational text to stderr on Windows PowerShell.
    $ErrorActionPreference = 'Continue'
    $lines = @(& $tool.Source @Arguments 2>&1)
    $exitCode = $LASTEXITCODE
    $message = (($lines | ForEach-Object { $_.ToString() }) -join "`n").Replace([string][char]0, '').Trim()
    if ($exitCode -ne 0) {
        throw "$Name exited with $exitCode. $message"
    }
    return $message
}

$checks = [ordered]@{
    'windows' = {
        if ([Environment]::OSVersion.Platform -ne 'Win32NT') { throw 'Run on the Windows workstation.' }
        $os = Get-CimInstance Win32_OperatingSystem
        if ($os.ProductType -ne 1 -or [int]$os.BuildNumber -lt 19045) {
            throw "Expected Windows 10 build 19045 or newer. Found $($os.Caption) build $($os.BuildNumber)."
        }
        "$($os.Caption) build $($os.BuildNumber)"
    }
    'wsl2' = {
        $distros = Invoke-Tool wsl.exe @('--list', '--verbose')
        if ($distros -notmatch '(?im)^\s*\*?\s*Ubuntu\S*\s+.+?\s+2\s*$') {
            throw 'Set up an Ubuntu distribution using WSL version 2 (wsl --list --verbose).'
        }
        'Ubuntu on WSL 2'
    }
    'git' = { Invoke-Tool git @('--version') }
    'gh' = { Invoke-Tool gh @('--version') }
    'github login' = { $null = Invoke-Tool gh @('auth', 'status', '--hostname', 'github.com'); 'Authenticated' }
    'python' = { Invoke-Tool py @('-3.12', '--version') }
    'node' = {
        Invoke-Tool node @('-p', 'process.release.lts ? process.version : process.exit(1)')
    }
    'docker' = { Invoke-Tool docker @('--version') }
    'compose' = { Invoke-Tool docker @('compose', 'version') }
    'daemon' = {
        $server = Invoke-Tool docker @('info', '--format', '{{.OSType}} {{.ServerVersion}}')
        if ($server -notmatch '^linux\s+\S+') { throw "Expected a Linux container engine. Got $server" }
        $server
    }
    'kubectl' = { Invoke-Tool kubectl @('version', '--client') }
    'helm' = { Invoke-Tool helm @('version', '--short') }
    'k3d' = { Invoke-Tool k3d @('version') }
}

foreach ($name in $checks.Keys) {
    try {
        $result = & $checks[$name]
        $firstLine = ($result -split '\r?\n')[0]
        Write-Host ("[OK]   {0,-13} {1}" -f $name, $firstLine)
    } catch {
        $failed = $true
        Write-Host ("[FAIL] {0,-13} {1}" -f $name, $_.Exception.Message)
    }
}

if ($failed) { exit 1 }
exit 0
