[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Targets = @(
  "README.md",
  "CHANGELOG.md",
  "docs",
  "frontend/src",
  "frontend/e2e",
  "runtime/src",
  "runtime/tests",
  "backend/app"
)

$MojibakeChars = @(
  [char]0xFFFD, # replacement character
  [char]0x93B5, # mojibake: e.g. execution
  [char]0x9365, # mojibake: e.g. chart
  [char]0x7487, # mojibake: e.g. request
  [char]0x7EDB, # mojibake: e.g. waiting
  [char]0x6FB6, # mojibake: e.g. failure
  [char]0x95CA, # mojibake: e.g. audio
  [char]0x60CE, # mojibake: e.g. enabled
  [char]0x53A4, # mojibake: e.g. config
  [char]0x756C, # mojibake: e.g. complete
  [char]0x95AC, # mojibake: e.g. channel
  [char]0x6522, # mojibake: e.g. sales
  [char]0x935E, # mojibake: e.g. sales
  [char]0x20AC  # mojibake continuation
)
$MojibakePattern = ($MojibakeChars | ForEach-Object { [regex]::Escape([string]$_) }) -join "|"
$findings = @()

foreach ($target in $Targets) {
  $path = Join-Path $Root $target
  if (-not (Test-Path $path)) {
    continue
  }

  $items = if ((Get-Item $path).PSIsContainer) {
    Get-ChildItem -Path $path -Recurse -File |
      Where-Object { $_.Extension -in @(".md", ".py", ".ts", ".tsx", ".json") }
  } else {
    @(Get-Item $path)
  }

  foreach ($item in $items) {
    $matches = Select-String -Path $item.FullName -Pattern $MojibakePattern -Encoding UTF8
    foreach ($match in $matches) {
      $relativePath = Resolve-Path -Path $match.Path -Relative
      $findings += ("{0}:{1}: {2}" -f $relativePath, $match.LineNumber, $match.Line.Trim())
    }
  }
}

if ($findings.Count -gt 0) {
  Write-Host "Possible garbled Chinese text found:"
  $findings | ForEach-Object { Write-Host $_ }
  exit 1
}

Write-Host "Text encoding check passed."
