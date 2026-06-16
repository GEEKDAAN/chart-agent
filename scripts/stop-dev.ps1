[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$PidFile = Join-Path (Join-Path $Root "tmp") "dev-processes.json"

if (-not (Test-Path $PidFile)) {
  Write-Host "No dev process file found."
  return
}

$metadata = Get-Content $PidFile -Raw | ConvertFrom-Json
$stopFailed = $false

foreach ($service in $metadata.services) {
  $processId = [int]$service.pid
  try {
    $process = Get-Process -Id $processId -ErrorAction Stop
    & taskkill.exe /PID $process.Id /T /F | Out-Null
    if ($LASTEXITCODE -ne 0) {
      throw "taskkill failed with exit code $LASTEXITCODE for PID $processId"
    }
    Write-Host "Stopped process tree PID $processId"
  } catch {
    $stillRunning = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($stillRunning) {
      $stopFailed = $true
      Write-Host "Failed to stop process tree PID $processId. $($_.Exception.Message)"
    } else {
      Write-Host "PID $processId is not running"
    }
  }
}

if ($stopFailed) {
  Write-Host "Some dev processes could not be stopped. Keeping $PidFile for retry."
  exit 1
}

Remove-Item -LiteralPath $PidFile -Force
Write-Host "chart-agent dev services stopped."
