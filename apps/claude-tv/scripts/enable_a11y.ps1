# ATENCAO (2026-10-05): este servico filtra TODAS as teclas da TV pelo processo do Claude (ver DIAGNOSTICO_TV_2026-10-05.md, secao 3).
# O botao de voz funciona pelo papel ASSISTANT sem ele. Nao reativar sem medir a latencia de entrada.
$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555
& $adb shell "settings put secure enabled_accessibility_services com.anthropic.claude/com.anthropic.claude.tv.ClaudeTvAccessibilityService"
& $adb shell "settings put secure accessibility_enabled 1"
Start-Sleep -Seconds 1
& $adb shell "settings get secure enabled_accessibility_services"
& $adb shell "settings get secure accessibility_enabled"
