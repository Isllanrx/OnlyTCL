$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555
Write-Host "=== Clicando no botao Enviar (1710, 920) ==="
& $adb shell "input tap 1710 920"
Start-Sleep -Seconds 3
& $adb shell "screencap -p /sdcard/after_send_tap.png"
& $adb pull /sdcard/after_send_tap.png "E:\projeto_twitchlit\claude-tv\screenshots\after_send_tap.png"
