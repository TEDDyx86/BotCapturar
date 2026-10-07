$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
$specPath = Join-Path $repoRoot "packaging\BotCapturar.spec"
$installerPath = Join-Path $repoRoot "packaging\BotCapturar.iss"
$exePath = Join-Path $repoRoot "dist\BotCapturar.exe"
$installerOutput = Join-Path $repoRoot "dist\installer"

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Create the project environment first: python -m venv .venv and install .[build,test]."
}

if (-not (Test-Path -LiteralPath $specPath)) {
    throw "PyInstaller spec not found: $specPath"
}

if (-not (Test-Path -LiteralPath $installerPath)) {
    throw "Inno Setup definition not found: $installerPath"
}

$runningAppPids = @(
    Get-CimInstance Win32_Process |
        Where-Object { $_.ExecutablePath -eq $exePath } |
        ForEach-Object { $_.ProcessId }
)
if ($runningAppPids.Count -gt 0) {
    $pidList = $runningAppPids -join ", "
    throw "BotCapturar.exe is running (PID $pidList). Click Stop and close it before rebuilding."
}

$iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
if ($iscc) {
    $isccPath = $iscc.Source
} else {
    $knownIsccPaths = @(
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
    )
    $isccPath = $knownIsccPaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}

if (-not $isccPath) {
    throw "Inno Setup 6 is required. Install it, then rerun this script."
}

New-Item -ItemType Directory -Path $installerOutput -Force | Out-Null
Push-Location $repoRoot
try {
    & $pythonExe -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "Tests failed; packaging stopped."
    }

    & $pythonExe -m PyInstaller --noconfirm --clean $specPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed."
    }

    if (-not (Test-Path -LiteralPath $exePath)) {
        throw "PyInstaller did not create $exePath"
    }

    & $isccPath $installerPath
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup compilation failed."
    }

    $installerExe = Join-Path $installerOutput "BotCapturar-Setup.exe"
    if (-not (Test-Path -LiteralPath $installerExe)) {
        throw "Inno Setup did not create $installerExe"
    }

    Write-Output "Portable app: $exePath"
    Write-Output "Installer: $installerExe"
} finally {
    Pop-Location
}
