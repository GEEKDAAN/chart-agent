[CmdletBinding()]
param(
  [ValidateSet("off", "openai")]
  [string]$LlmMode = "off",
  [int]$BackendPort = 8004,
  [int]$RuntimePort = 8014,
  [int]$FrontendPort = 5184,
  [string]$HostAddress = "127.0.0.1",
  [string]$PythonExe = "",
  [string]$NpmExe = "",
  [switch]$NoRestart
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$TmpDir = Join-Path $Root "tmp"
$PidFile = Join-Path $TmpDir "dev-processes.json"

New-Item -ItemType Directory -Force $TmpDir | Out-Null

if (-not $NoRestart -and (Test-Path $PidFile)) {
  & (Join-Path $PSScriptRoot "stop-dev.ps1") | Out-Null
}

if (-not $PythonExe) {
  $bundledPython = "D:\python\python3.11.2\python.exe"
  $PythonExe = if (Test-Path $bundledPython) { $bundledPython } else { "python" }
}

if (-not $NpmExe) {
  $bundledNpm = "D:\nodejs\npm.cmd"
  $NpmExe = if (Test-Path $bundledNpm) { $bundledNpm } else { "npm.cmd" }
}

function Escape-ForCmdDoubleQuotedString {
  param([string]$Value)
  return $Value.Replace('"', '\"')
}

function ConvertTo-CmdArgumentList {
  param([string[]]$Arguments)

  $quoted = @()
  foreach ($argument in $Arguments) {
    $quoted += '"{0}"' -f (Escape-ForCmdDoubleQuotedString $argument)
  }
  return ($quoted -join " ")
}

function Start-DevService {
  param(
    [string]$Name,
    [string]$WorkingDirectory,
    [string]$FilePath,
    [string[]]$Arguments,
    [hashtable]$EnvVars,
    [string]$LogName
  )

  $logPath = Join-Path $TmpDir "$LogName.log"
  $scriptPath = Join-Path $TmpDir "$LogName.cmd"
  $commandParts = @()
  foreach ($key in $EnvVars.Keys) {
    $value = Escape-ForCmdDoubleQuotedString ([string]$EnvVars[$key])
    $commandParts += 'set "{0}={1}"' -f $key, $value
  }

  $escapedWorkingDirectory = Escape-ForCmdDoubleQuotedString $WorkingDirectory
  $escapedFilePath = Escape-ForCmdDoubleQuotedString $FilePath
  $escapedLogPath = Escape-ForCmdDoubleQuotedString $logPath
  $argumentList = ConvertTo-CmdArgumentList $Arguments
  $commandParts += 'cd /d "{0}"' -f $escapedWorkingDirectory
  $commandParts += '"{0}" {1} > "{2}" 2>&1' -f $escapedFilePath, $argumentList, $escapedLogPath
  $script = "@echo off`r`n$($commandParts -join " && ")"

  Set-Content -Path $logPath -Encoding UTF8 -Value "Starting $Name at $((Get-Date).ToString("o"))"
  Set-Content -Path $scriptPath -Encoding Default -Value $script

  $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
  $startInfo.FileName = "cmd.exe"
  $startInfo.Arguments = '/D /C call "{0}"' -f $scriptPath
  $startInfo.WorkingDirectory = $WorkingDirectory
  $startInfo.UseShellExecute = $false
  $startInfo.CreateNoWindow = $true
  $process = [System.Diagnostics.Process]::Start($startInfo)

  return [ordered]@{
    name = $Name
    pid = $process.Id
    log = $logPath
    script = $scriptPath
    workingDirectory = $WorkingDirectory
  }
}

$backendUrl = "http://${HostAddress}:${BackendPort}"
$runtimeUrl = "http://${HostAddress}:${RuntimePort}"
$frontendUrl = "http://${HostAddress}:${FrontendPort}"

$services = @()
$services += Start-DevService `
  -Name "backend" `
  -WorkingDirectory (Join-Path $Root "backend") `
  -FilePath $PythonExe `
  -Arguments @("-m", "uvicorn", "app.main:app", "--host", $HostAddress, "--port", ([string]$BackendPort)) `
  -EnvVars @{ CHART_AGENT_LLM_MODE = $LlmMode } `
  -LogName "dev-backend"

$services += Start-DevService `
  -Name "runtime" `
  -WorkingDirectory (Join-Path $Root "runtime") `
  -FilePath $NpmExe `
  -Arguments @("run", "dev") `
  -EnvVars @{ PORT = $RuntimePort; CHART_AGENT_BACKEND_URL = $backendUrl } `
  -LogName "dev-runtime"

$services += Start-DevService `
  -Name "frontend" `
  -WorkingDirectory (Join-Path $Root "frontend") `
  -FilePath $NpmExe `
  -Arguments @("run", "dev", "--", "--host", $HostAddress, "--port", ([string]$FrontendPort)) `
  -EnvVars @{
    VITE_COPILOT_RUNTIME_URL = "/copilotkit"
    VITE_BACKEND_PROXY_URL = $backendUrl
    VITE_COPILOT_RUNTIME_PROXY_URL = $runtimeUrl
  } `
  -LogName "dev-frontend"

$metadata = [ordered]@{
  startedAt = (Get-Date).ToString("o")
  llmMode = $LlmMode
  urls = [ordered]@{
    frontend = $frontendUrl
    backend = $backendUrl
    runtime = "$runtimeUrl/copilotkit"
  }
  services = $services
}

$metadata | ConvertTo-Json -Depth 6 | Set-Content -Path $PidFile -Encoding UTF8

Write-Host "chart-agent dev services started."
Write-Host "Frontend: $frontendUrl"
Write-Host "Backend:  $backendUrl"
Write-Host "Runtime:  $runtimeUrl/copilotkit"
Write-Host "LLM mode: $LlmMode"
Write-Host "Logs:     $TmpDir"
Write-Host "Stop:     powershell -ExecutionPolicy Bypass -File scripts/stop-dev.ps1"
