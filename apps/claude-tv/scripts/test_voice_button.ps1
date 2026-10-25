$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

& $adb logcat -c
Write-Host "=== Disparando Keycode 231 (KEYCODE_VOICE_ASSIST) ==="
& $adb shell "input keyevent 231"
Start-Sleep -Seconds 2

Write-Host "=== Capturando Screenshot do Overlay ==="
& $adb shell "screencap -p /sdcard/overlay_from_voice_key.png"
& $adb pull /sdcard/overlay_from_voice_key.png "E:\projeto_twitchlit\claude-tv\screenshots\overlay_from_voice_key.png"

Write-Host "=== Logcat ClaudeTvA11y ==="
& $adb logcat -d -s ClaudeTvA11y ClaudeTV | Select-Object -Last 10
