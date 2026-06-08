# Start the Vite dev server (loads local Node + .env)
. "$PSScriptRoot\setup.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not (Test-Path "$PSScriptRoot\.env")) {
    Copy-Item "$PSScriptRoot\.env.example" "$PSScriptRoot\.env"
}
Set-Location $PSScriptRoot
npm run dev
