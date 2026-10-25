$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== TAPPING MODEL SELECTION PILL ==="
& $adb shell "input tap 460 1004"
Start-Sleep -Seconds 2

Write-Host "=== CAPTURING SCREENSHOT ==="
& $adb shell "screencap -p /sdcard/overlay_model_sheet.png"
& $adb pull /sdcard/overlay_model_sheet.png claude-tv/screenshots/overlay_model_sheet.png
