. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
# ATENCAO (2026-10-05): este servico filtra TODAS as teclas da TV pelo processo do Claude (ver DIAGNOSTICO_TV_2026-10-05.md, secao 3).
# O botao de voz funciona pelo papel ASSISTANT sem ele. Nao reativar sem medir a latencia de entrada.
& $adb connect $device
& $adb shell "settings put secure enabled_accessibility_services com.anthropic.claude/com.anthropic.claude.tv.ClaudeTvAccessibilityService"
& $adb shell "settings put secure accessibility_enabled 1"
Start-Sleep -Seconds 1
& $adb shell "settings get secure enabled_accessibility_services"
& $adb shell "settings get secure accessibility_enabled"
