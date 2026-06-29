<#  Bring up PostGIS, run the pipeline against it, and verify with spatial SQL.
    Run from the repo root once Docker Desktop shows "Engine running".  #>
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$py = Join-Path $root ".venv\Scripts\python.exe"

Write-Host "== Starting PostGIS ==" -ForegroundColor Cyan
docker compose -f "$root\docker-compose.yml" --env-file "$root\.env" up -d

Write-Host "== Waiting for healthy database ==" -ForegroundColor Cyan
for ($i = 0; $i -lt 30; $i++) {
    $h = docker inspect -f '{{.State.Health.Status}}' solafune_postgis 2>$null
    if ($h -eq "healthy") { break }
    Start-Sleep -Seconds 2
}
Write-Host "health: $h"

Write-Host "== Running pipeline against PostGIS ==" -ForegroundColor Cyan
$env:PYTHONPATH = $root
& $py -m src.pipeline

Write-Host "== Verifying with spatial SQL ==" -ForegroundColor Cyan
& $py -c "from src import db; print(db.run_sample_queries())"
