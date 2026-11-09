$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
uv run --locked uvicorn heatbrief.api:app --host 127.0.0.1 --port 8000 --env-file .env
