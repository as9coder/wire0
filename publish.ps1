# Publish wire0 to PyPI — requires PyPI API token
# Usage: $env:TWINE_PASSWORD = "pypi-..."; .\publish.ps1
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot

if (-not $env:TWINE_PASSWORD) {
    Write-Host ""
    Write-Host "  PyPI token required." -ForegroundColor Yellow
    Write-Host "  1. Create at https://pypi.org/manage/account/token/"
    Write-Host "  2. Run:  `$env:TWINE_PASSWORD = 'pypi-...'"
    Write-Host "  3. Run:  .\publish.ps1"
    Write-Host ""
    exit 1
}

$env:TWINE_USERNAME = "__token__"

if (Get-Command py -ErrorAction SilentlyContinue) {
    $py = "py -3.13"
} else {
    $py = "python"
}

Write-Host "  Building..." -ForegroundColor DarkYellow
Invoke-Expression "$py -m pip install build twine -q"
Invoke-Expression "$py -m build"
Write-Host "  Uploading to PyPI..." -ForegroundColor DarkYellow
Invoke-Expression "$py -m twine upload `"$Root\dist\*`""
Write-Host "  Published. Install with: pip install wire0" -ForegroundColor Green
