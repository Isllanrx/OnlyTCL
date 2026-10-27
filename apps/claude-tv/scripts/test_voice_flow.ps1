. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== 1. Testando tecla Voice Assist (231) no controle ==="
& $adb shell "input keyevent 231"
Start-Sleep -Seconds 2
& $adb shell "screencap -p /sdcard/voice_assist_triggered.png"
& $adb pull /sdcard/voice_assist_triggered.png "$outDir\voice_assist_triggered.png"

Write-Host "=== 2. Testando comando de voz local via RTK: 'abrir youtube' ==="
& $adb logcat -c
& $adb shell "am broadcast -a com.anthropic.claude.tv.VOICE_COMMAND --es query 'abrir youtube'"
Start-Sleep -Seconds 1
& $adb logcat -d -s ClaudeTV ClaudeTvRtk | Select-Object -Last 10
