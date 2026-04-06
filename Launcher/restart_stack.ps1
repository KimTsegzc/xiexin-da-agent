param(
    [int]$Port = 8501,
    [string]$PythonOverride = "",
    [switch]$NoBrowser,
    [switch]$WeChat,
    [switch]$UseLauncherExe,
    [int]$WaitMilliseconds = 400
)

$ErrorActionPreference = "Stop"

function Show-Phase([string]$text) {
    Write-Host "[restart_stack] $text" -ForegroundColor Green
}

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$StopScript = Join-Path $RepoRoot "Launcher\stop_stack.ps1"
$StartScript = Join-Path $RepoRoot "Launcher\start_stack.ps1"

if (-not (Test-Path $StopScript)) {
    throw "Launcher stop script not found: $StopScript"
}

if (-not (Test-Path $StartScript)) {
    throw "Launcher start script not found: $StartScript"
}

$stopParams = @{ Port = $Port }
if ($PythonOverride) {
    $stopParams.PythonOverride = $PythonOverride
}
if ($UseLauncherExe) {
    $stopParams.UseLauncherExe = $true
}

$startParams = @{ Port = $Port }
if ($PythonOverride) {
    $startParams.PythonOverride = $PythonOverride
}
if ($NoBrowser) {
    $startParams.NoBrowser = $true
}
if ($WeChat) {
    $startParams.WeChat = $true
}
if ($UseLauncherExe) {
    $startParams.UseLauncherExe = $true
}

Show-Phase "stopping full stack on port $Port"
& $StopScript @stopParams

if ($WaitMilliseconds -gt 0) {
    Show-Phase "waiting ${WaitMilliseconds}ms before start"
    Start-Sleep -Milliseconds $WaitMilliseconds
}

Show-Phase "starting full stack on port $Port"
& $StartScript @startParams
