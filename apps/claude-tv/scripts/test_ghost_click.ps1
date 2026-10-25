$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555
& $adb shell "input tap 1850 60" # Tap ghost icon on top right
Start-Sleep -Seconds 1
& $adb shell "screencap -p /sdcard/ghost_tapped.png"
& $adb pull /sdcard/ghost_tapped.png "E:\projeto_twitchlit\claude-tv\screenshots\ghost_tapped.png"
