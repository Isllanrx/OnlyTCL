. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

& $adb logcat -c
Write-Host "=== Disparando Keycode 231 (KEYCODE_VOICE_ASSIST) ==="
& $adb shell "input keyevent 231"
Start-Sleep -Seconds 2

Write-Host "=== Capturando Screenshot do Overlay ==="
& $adb shell "screencap -p /sdcard/overlay_from_voice_key.png"
& $adb pull /sdcard/overlay_from_voice_key.png "$outDir\overlay_from_voice_key.png"

Write-Host "=== Logcat ClaudeTvA11y ==="
& $adb logcat -d -s ClaudeTvA11y ClaudeTV | Select-Object -Last 10
