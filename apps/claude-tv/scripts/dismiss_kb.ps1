$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555
# Dismiss keyboard
& $adb shell "input keyevent 4"
Start-Sleep -Seconds 1
# Capture screenshot without keyboard
& $adb shell "screencap -p /sdcard/tv_chat_clean.png"
& $adb pull /sdcard/tv_chat_clean.png "E:\projeto_twitchlit\claude-tv\screenshots\tv_chat_clean.png"
# Dump UI hierarchy
& $adb shell "uiautomator dump /sdcard/ui_chat.xml"
& $adb pull /sdcard/ui_chat.xml "E:\projeto_twitchlit\claude-tv\screenshots\ui_chat.xml"
Write-Host "Done"
