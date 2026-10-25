$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555
& $adb shell "input keyevent 4" # KEYCODE_BACK
Start-Sleep -Milliseconds 600
& $adb shell "screencap -p /sdcard/after_back.png"
& $adb pull /sdcard/after_back.png "E:\projeto_twitchlit\claude-tv\screenshots\after_back.png"
