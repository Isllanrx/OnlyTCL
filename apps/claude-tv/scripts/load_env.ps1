# Shared environment loader for OnlyTCL PowerShell scripts
$loadScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path "$loadScriptDir\..\..\..").Path

$envFile = Join-Path $repoRoot ".env"
if (-not (Test-Path $envFile)) {
    $envFile = Join-Path $loadScriptDir ".env"
}
if (-not (Test-Path $envFile)) {
    $envFile = Join-Path $repoRoot "exemplo.env"
}

if (Test-Path $envFile) {
    Get-Content $envFile | Where-Object { $_ -match '^\s*([^#=\s]+)\s*=\s*(.*)$' } | ForEach-Object {
        $k = $matches[1].Trim()
        $v = $matches[2].Trim().Trim('"').Trim("'")
        if (-not [System.Environment]::GetEnvironmentVariable($k)) {
            [System.Environment]::SetEnvironmentVariable($k, $v)
        }
    }
}

if (-not $env:TV_IP) { $env:TV_IP = "192.168.1.100" }
if (-not $env:TV_PORT) { $env:TV_PORT = "5555" }
if (-not $env:TV_DEVICE) { $env:TV_DEVICE = "$($env:TV_IP):$($env:TV_PORT)" }
if (-not $env:PROJECT_ROOT) { $env:PROJECT_ROOT = $repoRoot }
if (-not $env:OUTPUT_DIR) { $env:OUTPUT_DIR = Join-Path $repoRoot "output" }

if (-not $env:ADB_PATH) {
    if ($env:ANDROID_HOME -and (Test-Path "$env:ANDROID_HOME\platform-tools\adb.exe")) {
        $env:ADB_PATH = "$env:ANDROID_HOME\platform-tools\adb.exe"
    } elseif ($env:ANDROID_SDK_ROOT -and (Test-Path "$env:ANDROID_SDK_ROOT\platform-tools\adb.exe")) {
        $env:ADB_PATH = "$env:ANDROID_SDK_ROOT\platform-tools\adb.exe"
    } else {
        $env:ADB_PATH = "adb"
    }
}
