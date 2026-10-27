. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== SENDING KEYCODE_VOICE_ASSIST (231) ==="
& $adb shell "input keyevent 231"
Start-Sleep -Seconds 2

Write-Host "=== CURRENT FOCUS ==="
& $adb shell "dumpsys window | grep -E mCurrentFocus"

Write-Host "=== LOGCAT FOR ClaudeTvA11y ==="
& $adb shell "logcat -d -t 30" | Select-String -Pattern "ClaudeTv|AssistantOverlayActivity"
