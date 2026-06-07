# Wire0 dev launcher — finds Python 3.11+, editable-installs this repo, runs wire0
$Root = $PSScriptRoot
$PyCheck = 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'

function Invoke-Wire0([string]$exe, [string[]]$prefix) {
    if ($prefix.Count) {
        & py @prefix -m pip install -e $Root -q 2>$null
        & py @prefix -m wire0 @args
    } else {
        & $exe -m pip install -e $Root -q 2>$null
        & $exe -m wire0 @args
    }
    exit $LASTEXITCODE
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    foreach ($ver in @("-3.13", "-3.12", "-3.11")) {
        & py $ver -c $PyCheck 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { Invoke-Wire0 "py" @($ver) }
    }
}

foreach ($name in @("python3", "python")) {
    if (Get-Command $name -ErrorAction SilentlyContinue) {
        & $name -c $PyCheck 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) { Invoke-Wire0 $name @() }
    }
}

Write-Host "Wire0 requires Python 3.11+. Install from https://www.python.org/downloads/" -ForegroundColor Yellow
exit 1
