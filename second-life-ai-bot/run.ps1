$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Fill in SL_FIRST_NAME, SL_PASSWORD, OWNER_UUID, and your chosen AI settings, then run this again."
    exit 0
}

dotnet restore
dotnet run --configuration Release
