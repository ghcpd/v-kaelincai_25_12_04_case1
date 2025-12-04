$ErrorActionPreference = "Stop"
if (Test-Path .venv\Scripts\Activate.ps1) { . .venv\Scripts\Activate.ps1 }
$env:PYTHONPATH = "src"
if (!(Test-Path logs)) { New-Item -ItemType Directory -Path logs | Out-Null }
python -m pytest -q | Tee-Object -FilePath logs\log_post.txt
