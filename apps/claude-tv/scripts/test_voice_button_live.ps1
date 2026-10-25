$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

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
& $adb pull /sdcard/overlay_live_test.png "E:\projeto_twitchlit\claude-tv\screenshots\overlay_live_test.png"

Write-Host "=== 6. VERIFYING BOUND SERVICES ==="
& $adb shell "dumpsys accessibility services"

Write-Host "TEST COMPLETE!"
