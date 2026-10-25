$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== 1. Digitando mensagem no Claude ==="
& $adb shell "input text 'Ola%sClaude'"
Start-Sleep -Milliseconds 600

Write-Host "=== 2. Enviando mensagem (Enter / Send) ==="
& $adb shell "input keyevent 66" # KEYCODE_ENTER
Start-Sleep -Seconds 4

Write-Host "=== 3. Fechando teclado para visualização da resposta ==="
& $adb shell "input keyevent 111" # KEYCODE_ESCAPE
Start-Sleep -Milliseconds 500

Write-Host "=== 4. Capturando resposta na TV ==="
& $adb shell "screencap -p /sdcard/chat_response.png"
& $adb pull /sdcard/chat_response.png "E:\projeto_twitchlit\claude-tv\screenshots\chat_response.png"

Write-Host "=== 5. Verificando métricas do módulo Rust RTK ==="
& $adb logcat -d -s ClaudeTV ClaudeTvRtk | Select-Object -Last 20
