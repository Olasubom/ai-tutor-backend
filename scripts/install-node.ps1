# Download portable Node.js (with npm) into .tools/node
$nodeVersion = "v22.22.0"
$root = Split-Path $PSScriptRoot -Parent
$toolsDir = Join-Path $root ".tools"
$nodeDir = Join-Path $toolsDir "node"
$zipPath = Join-Path $toolsDir "node.zip"
$url = "https://nodejs.org/dist/$nodeVersion/node-$nodeVersion-win-x64.zip"

New-Item -ItemType Directory -Force -Path $toolsDir | Out-Null

if (Test-Path (Join-Path $nodeDir "node.exe")) {
    Write-Host "Node.js already installed at $nodeDir"
    & (Join-Path $nodeDir "node.exe") --version
    & (Join-Path $nodeDir "npm.cmd") --version
    exit 0
}

Write-Host "Downloading Node.js $nodeVersion..."
Invoke-WebRequest -Uri $url -OutFile $zipPath -UseBasicParsing
Expand-Archive -Path $zipPath -DestinationPath $toolsDir -Force
if (Test-Path $nodeDir) { Remove-Item $nodeDir -Recurse -Force }
Rename-Item (Join-Path $toolsDir "node-$nodeVersion-win-x64") $nodeDir
Remove-Item $zipPath -Force

Write-Host "Installed:"
& (Join-Path $nodeDir "node.exe") --version
& (Join-Path $nodeDir "npm.cmd") --version
