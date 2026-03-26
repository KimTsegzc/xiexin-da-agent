param(
    [int]$Port = 8501,
    [string]$PythonOverride = ""
)

$ErrorActionPreference = "Stop"

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

if ((-not $PythonOverride) -and (Test-Path $LauncherExe)) {
    & $LauncherExe --stop --port $Port
    return
}

if (-not (Test-Path $LauncherScript)) {
    throw "Launcher script not found: $LauncherScript"
}

$PythonPath = Find-Python
if (-not $PythonPath) {
    throw "No Python found. Install a venv, conda env, or add python to PATH. Or pass -PythonOverride <path>."
}

$launcherArgs = @($LauncherScript, '--stop', '--port', $Port)
if ($PythonOverride) {
    $launcherArgs += @('--python', $PythonOverride)
}

& $PythonPath @launcherArgs