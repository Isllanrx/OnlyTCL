$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== TAPPING SONNET 5.5 (960, 622) ==="
& $adb shell "input tap 960 622"
Start-Sleep -Seconds 2

& $adb shell "screencap -p /sdcard/tv_sonnet_selected.png"
& $adb pull /sdcard/tv_sonnet_selected.png "E:\projeto_twitchlit\claude-tv\screenshots\tv_sonnet_selected.png"
Write-Host "Sonnet selected and captured"
