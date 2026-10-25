$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== TAPPING MODEL PILL (1034, 1010) ==="
& $adb shell "input tap 1034 1010"
Start-Sleep -Seconds 2

& $adb shell "screencap -p /sdcard/model_sheet_main.png"
& $adb pull /sdcard/model_sheet_main.png "E:\projeto_twitchlit\claude-tv\screenshots\model_sheet_main.png"
& $adb shell "uiautomator dump /sdcard/ui_model.xml"
& $adb pull /sdcard/ui_model.xml "E:\projeto_twitchlit\claude-tv\screenshots\ui_model.xml"
Write-Host "Model sheet opened and captured"
