. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== SENDING HOME KEY ==="
& $adb shell "input keyevent 3"
Start-Sleep -Seconds 3

Write-Host "=== CURRENT FOCUS ==="
& $adb shell "dumpsys window | grep -E mCurrentFocus"

Write-Host "=== ACCESSIBILITY BOUND SERVICES ==="
& $adb shell "dumpsys accessibility services"

Write-Host "=== RUNNING PROCESSES ==="
& $adb shell "ps -A | grep anthropic"
