$ErrorActionPreference = "Stop"
$ROOT = Resolve-Path "$PSScriptRoot\.."
$ISSUE_PROJECT = Resolve-Path "$ROOT\..\issue_project"
$RESULTS_DIR = "$ROOT\Shared\results"
if (!(Test-Path $RESULTS_DIR)) { New-Item -ItemType Directory -Path $RESULTS_DIR | Out-Null }

# Run legacy tests
Write-Host "Running legacy tests..."
$legacyLog = Join-Path $RESULTS_DIR "results_pre.log"
Set-Location $ISSUE_PROJECT
$legacyOutput = python -m pytest -q 2>&1 | Tee-Object -FilePath $legacyLog
$legacyExit = $LastExitCode
$resultsPre = @{ exit_code = $legacyExit; output = $legacyOutput }
$resultsPre | ConvertTo-Json -Depth 4 | Out-File (Join-Path $RESULTS_DIR "results_pre.json") -Encoding utf8

# Run greenfield tests
Set-Location $ROOT
if (!(Test-Path .venv)) { ./setup.ps1 }
./run_tests.ps1
Copy-Item "$ROOT\results\results_post.json" "$RESULTS_DIR\results_post.json" -Force

Write-Host "Artifacts in $RESULTS_DIR"
