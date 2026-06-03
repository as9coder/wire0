# Repair broken Wire0 install — run repair.bat or: powershell -ExecutionPolicy Bypass -File repair.ps1
$ErrorActionPreference = "Stop"

$Orange = "DarkYellow"
$Dim = "DarkGray"
$Root = $PSScriptRoot
$PyCheck = 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'

function Write-Step($msg) { Write-Host "  $msg" -ForegroundColor $Orange }
function Write-Ok($msg)   { Write-Host "  [ok] $msg" -ForegroundColor Green }
function Write-Err($msg)  { Write-Host "  [!!] $msg" -ForegroundColor Red }

function Find-Python {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($ver in @("-3.13", "-3.12", "-3.11")) {
            & py $ver -c $PyCheck 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { return @{ Exe = "py"; Prefix = @($ver) } }
        }
    }
    foreach ($name in @("python3", "python")) {
        if (Get-Command $name -ErrorAction SilentlyContinue) {
            & $name -c $PyCheck 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) { return @{ Exe = $name; Prefix = @() } }
        }
    }
    return $null
}

function Invoke-Py($python, [string[]]$PyArgs) {
    if ($python.Exe -eq "py") {
        $prefix = $python.Prefix
        & py @prefix @PyArgs
    } else {
        & $python.Exe @PyArgs
    }
    if ($LASTEXITCODE -ne 0) { throw "command failed: $($PyArgs -join ' ')" }
}

Write-Host ""
Write-Host "  Wire0 Repair" -ForegroundColor $Orange
Write-Host "  ------------" -ForegroundColor $Dim
Write-Host ""

$python = Find-Python
if (-not $python) {
    Write-Err "Python 3.11+ not found."
    exit 1
}

$site = if ($python.Exe -eq "py") {
    $prefix = $python.Prefix
    (& py @prefix -c "import site; print(site.getsitepackages()[0])" | Select-Object -Last 1).Trim()
} else {
    (& $python.Exe -c "import site; print(site.getsitepackages()[0])" | Select-Object -Last 1).Trim()
}

$scripts = if ($python.Exe -eq "py") {
    $prefix = $python.Prefix
    (& py @prefix -c "import sysconfig; print(sysconfig.get_path('scripts'))" | Select-Object -Last 1).Trim()
} else {
    (& $python.Exe -c "import sysconfig; print(sysconfig.get_path('scripts'))" | Select-Object -Last 1).Trim()
}

Write-Step "Removing broken pip leftovers..."
$removed = 0
foreach ($item in Get-ChildItem $site -Force -ErrorAction SilentlyContinue) {
    if ($item.Name -like '~*') {
        Remove-Item $item.FullName -Recurse -Force -ErrorAction SilentlyContinue
        $removed++
    }
}
$wireDir = Join-Path $site "wire0"
if (Test-Path $wireDir) { Remove-Item $wireDir -Recurse -Force -ErrorAction SilentlyContinue; $removed++ }
Get-ChildItem $site -Filter "wire0*.dist-info" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
    $removed++
}
$exe = Join-Path $scripts "wire0.exe"
if (Test-Path $exe) { Remove-Item $exe -Force -ErrorAction SilentlyContinue; $removed++ }
Write-Ok "cleaned $removed item(s)"

Write-Step "Installing Wire0..."
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    Invoke-Py $python @("-m", "pip", "install", "--upgrade", "pip", "-q")
    Invoke-Py $python @("-m", "pip", "install", $Root, "--force-reinstall", "--no-cache-dir")
} finally {
    $ErrorActionPreference = $prevEap
}

Write-Step "Verifying..."
if ($python.Exe -eq "py") {
    $prefix = $python.Prefix
    & py @prefix -c "import wire0; from wire0.config import DEFAULT_MODEL; print(DEFAULT_MODEL)" 2>$null | Out-Null
} else {
    & $python.Exe -c "import wire0; from wire0.config import DEFAULT_MODEL; print(DEFAULT_MODEL)" 2>$null | Out-Null
}
if ($LASTEXITCODE -ne 0) {
    Write-Err "install verification failed"
    exit 1
}

Write-Host ""
Write-Ok "Wire0 repaired - run: wire0"
Write-Host ""
