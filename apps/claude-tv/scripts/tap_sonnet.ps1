$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== TAPPING SONNET ==="
& $adb shell "input tap 500 810"
Start-Sleep -Seconds 2

Write-Host "=== CAPTURING SCREENSHOT ==="
& $adb shell "screencap -p /sdcard/overlay_after_sonnet.png"
& $adb pull /sdcard/overlay_after_sonnet.png claude-tv/screenshots/overlay_after_sonnet.png
