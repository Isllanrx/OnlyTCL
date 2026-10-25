$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== 1. Testando tecla Voice Assist (231) no controle ==="
& $adb shell "input keyevent 231"
Start-Sleep -Seconds 2
& $adb shell "screencap -p /sdcard/voice_assist_triggered.png"
& $adb pull /sdcard/voice_assist_triggered.png "E:\projeto_twitchlit\claude-tv\screenshots\voice_assist_triggered.png"

Write-Host "=== 2. Testando comando de voz local via RTK: 'abrir youtube' ==="
& $adb logcat -c
& $adb shell "am broadcast -a com.anthropic.claude.tv.VOICE_COMMAND --es query 'abrir youtube'"
Start-Sleep -Seconds 1
& $adb logcat -d -s ClaudeTV ClaudeTvRtk | Select-Object -Last 10
