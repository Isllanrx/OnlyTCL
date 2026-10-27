. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== GLOBAL VOICE SETTINGS ==="
& $adb shell "settings list global" | Select-String -Pattern "voice|assist|hotkey|mic|remote"

Write-Host "=== SECURE VOICE SETTINGS ==="
& $adb shell "settings list secure" | Select-String -Pattern "voice|assist|hotkey|mic|remote"
