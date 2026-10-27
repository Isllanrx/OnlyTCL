. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== LOGCAT RECENT 50 LINES FOR ACCESSIBILITY ==="
& $adb shell "logcat -d -t 100" | Select-String -Pattern "accessibility|ClaudeTv|TclAppBoot|ActivityManager"
