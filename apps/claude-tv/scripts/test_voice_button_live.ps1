. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== 1. GOING HOME ==="
& $adb shell "input keyevent 3"
Start-Sleep -Seconds 2

Write-Host "=== 2. CURRENT WINDOW FOCUS ==="
& $adb shell "dumpsys window" | Select-String -Pattern "mCurrentFocus"

Write-Host "=== 3. PRESSING REMOTE MIC BUTTON (KEYCODE_VOICE_ASSIST 231) ==="
& $adb shell "input keyevent 231"
Start-Sleep -Seconds 3

Write-Host "=== 4. CURRENT WINDOW FOCUS AFTER MIC KEY ==="
& $adb shell "dumpsys window" | Select-String -Pattern "mCurrentFocus"

Write-Host "=== 5. CAPTURING OVERLAY SCREENSHOT ==="
& $adb shell "screencap -p /sdcard/overlay_live_test.png"
& $adb pull /sdcard/overlay_live_test.png "$outDir\overlay_live_test.png"

Write-Host "=== 6. VERIFYING BOUND SERVICES ==="
& $adb shell "dumpsys accessibility services"

Write-Host "TEST COMPLETE!"
