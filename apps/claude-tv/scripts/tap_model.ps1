. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== TAPPING MODEL SELECTION PILL ==="
& $adb shell "input tap 460 1004"
Start-Sleep -Seconds 2

Write-Host "=== CAPTURING SCREENSHOT ==="
& $adb shell "screencap -p /sdcard/overlay_model_sheet.png"
& $adb pull /sdcard/overlay_model_sheet.png claude-tv/screenshots/overlay_model_sheet.png
