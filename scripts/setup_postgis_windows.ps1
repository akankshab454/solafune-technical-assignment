<#
  One-time setup for running the PostGIS database on Windows.
  RUN THIS IN AN ELEVATED (Administrator) PowerShell.

  Steps 1-2 install the prerequisites (WSL2 + Docker Desktop). A REBOOT is
  required after WSL is installed. After rebooting and launching Docker Desktop
  once (accept the license), run `docker compose up -d` from the repo root.
#>

Write-Host "== 1/2: Installing WSL2 kernel (no distro needed for Docker) ==" -ForegroundColor Cyan
wsl --install --no-distribution

Write-Host "== 2/2: Installing Docker Desktop via winget ==" -ForegroundColor Cyan
winget install -e --id Docker.DockerDesktop --accept-source-agreements --accept-package-agreements

Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host "  1. REBOOT your machine (required for WSL2)."
Write-Host "  2. Launch 'Docker Desktop' and accept the license; wait until it says 'Engine running'."
Write-Host "  3. From the repo root run:  docker compose up -d"
Write-Host "  4. Then run the pipeline:   python -m src.pipeline"
