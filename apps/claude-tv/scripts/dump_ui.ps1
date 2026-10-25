$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

& $adb shell "uiautomator dump /sdcard/ui_dump.xml"
& $adb pull /sdcard/ui_dump.xml claude-tv/screenshots/ui_dump.xml
Write-Host "UI dump pulled successfully"
