. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== 1. Aguardando tela carregar e capturando Screenshot inicial ==="
Start-Sleep -Seconds 3
& $adb shell "screencap -p /sdcard/step1_loaded.png"
& $adb pull /sdcard/step1_loaded.png "$outDir\step1_loaded.png"

Write-Host "=== 2. Verificando estado da Activity e View Hierarchy ==="
& $adb shell "dumpsys activity activities | grep -E 'mResumedActivity|mFocusedWindow'"

Write-Host "=== 3. Testando D-Pad Down (Navegar até input/botões) ==="
& $adb shell "input keyevent 20" # KEYCODE_DPAD_DOWN
Start-Sleep -Milliseconds 600
& $adb shell "screencap -p /sdcard/step2_dpad_down.png"
& $adb pull /sdcard/step2_dpad_down.png "$outDir\step2_dpad_down.png"

Write-Host "=== 4. Testando D-Pad Right (Navegar entre botões) ==="
& $adb shell "input keyevent 22" # KEYCODE_DPAD_RIGHT
Start-Sleep -Milliseconds 600
& $adb shell "screencap -p /sdcard/step3_dpad_right.png"
& $adb pull /sdcard/step3_dpad_right.png "$outDir\step3_dpad_right.png"

Write-Host "=== 5. Testando Tecla Menu (Iniciando Nova Conversa Incógnita) ==="
& $adb shell "input keyevent 82" # KEYCODE_MENU
Start-Sleep -Milliseconds 800
& $adb shell "screencap -p /sdcard/step4_menu_incognito.png"
& $adb pull /sdcard/step4_menu_incognito.png "$outDir\step4_menu_incognito.png"

Write-Host "=== 6. Testando Disparo do Assistant Overlay ==="
& $adb shell "am start -n com.anthropic.claude/com.anthropic.claude.mainactivity.AssistantOverlayActivity"
Start-Sleep -Seconds 2
& $adb shell "screencap -p /sdcard/step5_overlay.png"
& $adb pull /sdcard/step5_overlay.png "$outDir\step5_overlay.png"

Write-Host "=== 7. Retornando para MainActivity ==="
& $adb shell "input keyevent 4" # KEYCODE_BACK (fecha overlay)
Start-Sleep -Milliseconds 600
& $adb shell "am start -n com.anthropic.claude/com.anthropic.claude.mainactivity.MainActivity"
Start-Sleep -Seconds 1
& $adb shell "screencap -p /sdcard/step6_main_return.png"
& $adb pull /sdcard/step6_main_return.png "$outDir\step6_main_return.png"

Write-Host "TESTES DE FLUXO CONCLUÍDOS!"
