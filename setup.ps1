# Wire0 one-click installer — run setup.bat or: powershell -ExecutionPolicy Bypass -File setup.ps1
$ErrorActionPreference = "Stop"

$Orange = "DarkYellow"
$Dim = "DarkGray"
$Root = $PSScriptRoot
$PyCheck = 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'

function Write-Step($msg) { Write-Host "  " -NoNewline; Write-Host $msg -ForegroundColor $Orange }
function Write-Ok($msg)   { Write-Host "  [ok] $msg" -ForegroundColor Green }
function Write-Err($msg)  { Write-Host "  [!!] $msg" -ForegroundColor Red }

function Test-Python311Exe([string]$exe) {
    & $exe -c $PyCheck 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

function Test-PyLauncher([string]$ver) {
    & py $ver -c $PyCheck 2>$null | Out-Null
    return $LASTEXITCODE -eq 0
}

function Find-Python {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($ver in @("-3.13", "-3.12", "-3.11")) {
            if (Test-PyLauncher $ver) { return @{ Exe = "py"; Prefix = @($ver) } }
        }
    }
    foreach ($name in @("python3", "python")) {
        if (Get-Command $name -ErrorAction SilentlyContinue) {
            if (Test-Python311Exe $name) { return @{ Exe = $name; Prefix = @() } }
        }
    }
    $patterns = @(
        "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe",
        "$env:ProgramFiles\Python3*\python.exe"
    )
    foreach ($pat in $patterns) {
        $found = Get-ChildItem -Path $pat -ErrorAction SilentlyContinue | Sort-Object FullName -Descending
        foreach ($p in $found) {
            if (Test-Python311Exe $p.FullName) { return @{ Exe = $p.FullName; Prefix = @() } }
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

function Get-PyOutput($python, [string[]]$PyArgs) {
    if ($python.Exe -eq "py") {
        $prefix = $python.Prefix
        return (& py @prefix @PyArgs | Select-Object -Last 1).Trim()
    }
    return (& $python.Exe @PyArgs | Select-Object -Last 1).Trim()
}

Write-Host ""
Write-Host "  Wire0 Setup" -ForegroundColor $Orange
Write-Host "  -----------" -ForegroundColor $Dim
Write-Host ""

Write-Step "Looking for Python 3.11+..."
$python = Find-Python
if (-not $python) {
    Write-Err "Python 3.11+ not found."
    Write-Host ""
    Write-Host "  Install from https://www.python.org/downloads/" -ForegroundColor $Dim
    Write-Host "  Check 'Add python.exe to PATH' during setup." -ForegroundColor $Dim
    Write-Host ""
    exit 1
}

$ver = Get-PyOutput $python @("-c", "import sys; print('.'.join(map(str, sys.version_info[:3])))")
Write-Ok "Python $ver"

Write-Step "Upgrading pip..."
Invoke-Py $python @("-m", "pip", "install", "--upgrade", "pip", "-q") 2>$null
Write-Ok "pip ready"

Write-Step "Installing Wire0..."
Invoke-Py $python @("-m", "pip", "install", $Root, "-q") 2>$null
Write-Ok "Wire0 installed"

$scripts = Get-PyOutput $python @("-c", "import sysconfig; print(sysconfig.get_path('scripts'))")

Write-Host ""
Write-Host "  Wire0 is ready" -ForegroundColor $Orange
Write-Host ""
Write-Host "  Run anywhere:" -ForegroundColor $Dim
Write-Host "    wire0"
Write-Host "    wire0 C:\path\to\project"
Write-Host ""

$onPath = ($env:Path -split ';' | ForEach-Object { $_.TrimEnd('\') }) -contains $scripts.TrimEnd('\')
if (-not $onPath) {
    Write-Host "  If 'wire0' is not recognized, add Scripts to PATH:" -ForegroundColor $Dim
    Write-Host "    $scripts"
    Write-Host ""
    Write-Host "  Or run:" -ForegroundColor $Dim
    if ($python.Exe -eq "py") {
        Write-Host "    py $($python.Prefix -join ' ') -m wire0"
    } else {
        Write-Host "    `"$($python.Exe)`" -m wire0"
    }
    Write-Host ""
}

Write-Host "  Set your OpenRouter key on first run with /key" -ForegroundColor $Dim
Write-Host ""
