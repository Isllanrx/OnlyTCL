. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device
Write-Host "=== Clicando no botao Enviar (1710, 920) ==="
& $adb shell "input tap 1710 920"
Start-Sleep -Seconds 3
& $adb shell "screencap -p /sdcard/after_send_tap.png"
& $adb pull /sdcard/after_send_tap.png "$outDir\after_send_tap.png"
