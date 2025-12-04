# Run all integration tests and generate report
#
# Usage (PowerShell):
#   .\run_tests.ps1 [-Verbose] [-Coverage]

param(
    [switch]$Verbose,
    [switch]$Coverage
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$resultsDir = Join-Path $scriptDir "results"
$logsDir = Join-Path $scriptDir "logs"

New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null
New-Item -ItemType Directory -Path $logsDir -Force | Out-Null

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "  Running Integration Tests (v2 Routing System)" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""

# Build pytest arguments
$pytestArgs = @(
    "tests/"
    "--pythonpath=src"
    "-v"
    "--tb=short"
    "--junit-xml=$resultsDir/junit.xml"
    "--log-file=$logsDir/test_run.log"
)

if ($Coverage) {
    $pytestArgs += @("--cov=src/routing_v2")
}

Write-Host "Running pytest..."
& pytest @pytestArgs | Tee-Object -FilePath "$resultsDir/test_output.txt"
$testExitCode = $LASTEXITCODE

# Generate summary
Write-Host ""
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""

if ($testExitCode -eq 0) {
    Write-Host "✓ ALL TESTS PASSED" -ForegroundColor Green
} else {
    Write-Host "✗ SOME TESTS FAILED (exit code: $testExitCode)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Artifacts:" -ForegroundColor Yellow
Write-Host "  Logs:      $logsDir/test_run.log"
Write-Host "  Results:   $resultsDir/"
Write-Host "  Output:    $resultsDir/test_output.txt"
Write-Host ""

exit $testExitCode
