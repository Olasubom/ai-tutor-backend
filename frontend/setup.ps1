# Adds project-local Node.js to PATH for this PowerShell session.
# Node is installed at ../.tools/node (no system-wide install required).

$nodeDir = Resolve-Path (Join-Path $PSScriptRoot "..\.tools\node")
if (-not (Test-Path (Join-Path $nodeDir "npm.cmd"))) {
    Write-Host "Node.js not found. Run from project root:" -ForegroundColor Yellow
    Write-Host "  powershell -ExecutionPolicy Bypass -File .\scripts\install-node.ps1"
    exit 1
}

$env:PATH = "$nodeDir;$env:PATH"
Write-Host "Node $(node --version) | npm $(npm --version) ready." -ForegroundColor Green
