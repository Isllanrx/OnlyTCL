. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== CURRENT TOP RESUMED ACTIVITY ==="
& $adb shell "dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity'"

Write-Host "=== ALL VISIBLE WINDOWS ==="
& $adb shell "dumpsys window windows | grep -E 'Window #|package='"
