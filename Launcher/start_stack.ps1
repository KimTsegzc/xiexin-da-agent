param(
    [int]$Port = 8501,
    [string]$PythonOverride = "",
    [switch]$NoBrowser,
    [switch]$WeChat,
    [switch]$UseLauncherExe
)

$ErrorActionPreference = "Stop"

function Show-Phase([string]$text) {
    Write-Host "[start_stack] $text" -ForegroundColor Cyan
}

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$LauncherExe = Join-Path $RepoRoot "Go_XIEXin.exe"
$LauncherScript = Join-Path $RepoRoot "Launcher\Go_XIEXin.py"

function Find-Python {
    if ($PythonOverride -and (Test-Path $PythonOverride)) {
        return $PythonOverride
    }

    foreach ($venvDir in @(".venv311", ".venv", "venv", ".venv312", ".venv310")) {
        $candidate = Join-Path $RepoRoot "$venvDir\Scripts\python.exe"
        if (Test-Path $candidate) { return $candidate }
    }

    if ($env:CONDA_PREFIX) {
        $condaPython = Join-Path $env:CONDA_PREFIX "python.exe"
        if (Test-Path $condaPython) { return $condaPython }
    }

    $systemPython = Get-Command python -ErrorAction SilentlyContinue |
                    Select-Object -First 1 -ExpandProperty Source
    if ($systemPython) { return $systemPython }

    return $null
}

if ($UseLauncherExe -and (-not $PythonOverride) -and (Test-Path $LauncherExe)) {
    Show-Phase "using launcher exe"
    $launcherArgs = @('--port', $Port)
    if ($NoBrowser) {
        $launcherArgs += '--no-browser'
    }
    & $LauncherExe @launcherArgs
    return
}

if (-not (Test-Path $LauncherScript)) {
    throw "Launcher script not found: $LauncherScript"
}

$PythonPath = Find-Python
if (-not $PythonPath) {
    throw "No Python found. Install a venv, conda env, or add python to PATH. Or pass -PythonOverride <path>."
}

Show-Phase "python=$PythonPath"
Show-Phase "starting full stack (backend + frontend)"

$launcherArgs = @($LauncherScript, '--port', $Port)
if ($PythonOverride) {
    $launcherArgs += @('--python', $PythonOverride)
}
if ($NoBrowser) {
    $launcherArgs += '--no-browser'
}

& $PythonPath @launcherArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host "[start_stack] launcher failed exitCode=$exitCode" -ForegroundColor Red
    $runtimeDir = Join-Path $RepoRoot ".runtime"
    $backendErr = Join-Path $runtimeDir "backend-8766.err.log"
    $frontendErr = Join-Path $runtimeDir "frontend-$Port.err.log"
    if (Test-Path $backendErr) {
        Write-Host "[start_stack] backend err tail:" -ForegroundColor Yellow
        Get-Content $backendErr -Tail 30
    }
    if (Test-Path $frontendErr) {
        Write-Host "[start_stack] frontend err tail:" -ForegroundColor Yellow
        Get-Content $frontendErr -Tail 30
    }
    exit $exitCode
}

$backend = try { (Invoke-WebRequest -Uri "http://127.0.0.1:8766/health" -UseBasicParsing -TimeoutSec 5).StatusCode } catch { "ERR" }
$frontend = try { (Invoke-WebRequest -Uri "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec 5).StatusCode } catch { "ERR" }
Show-Phase "health backend=$backend frontend=$frontend"
