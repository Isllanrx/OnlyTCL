. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== TAPPING SONNET 5.5 (960, 622) ==="
& $adb shell "input tap 960 622"
Start-Sleep -Seconds 2

& $adb shell "screencap -p /sdcard/tv_sonnet_selected.png"
& $adb pull /sdcard/tv_sonnet_selected.png "$outDir\tv_sonnet_selected.png"
Write-Host "Sonnet selected and captured"
