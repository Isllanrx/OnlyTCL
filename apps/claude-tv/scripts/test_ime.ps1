$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555
& $adb shell "input keyevent 111" # KEYCODE_ESCAPE
Start-Sleep -Milliseconds 500
& $adb shell "input keyevent 4" # KEYCODE_BACK
Start-Sleep -Milliseconds 500
& $adb shell "screencap -p /sdcard/ime_test.png"
& $adb pull /sdcard/ime_test.png "E:\projeto_twitchlit\claude-tv\screenshots\ime_test.png"
