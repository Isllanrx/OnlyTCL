$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555
& $adb shell input keyevent 111
Start-Sleep -Seconds 1
& $adb shell screencap -p /sdcard/tv_final_clean.png
& $adb pull /sdcard/tv_final_clean.png "E:\projeto_twitchlit\claude-tv\screenshots\tv_final_clean.png"
Write-Host "CLEAN_PULLED_SUCCESS"
