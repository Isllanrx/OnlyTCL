. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== TAPPING MODEL PILL (1034, 1010) ==="
& $adb shell "input tap 1034 1010"
Start-Sleep -Seconds 2

& $adb shell "screencap -p /sdcard/model_sheet_main.png"
& $adb pull /sdcard/model_sheet_main.png "$outDir\model_sheet_main.png"
& $adb shell "uiautomator dump /sdcard/ui_model.xml"
& $adb pull /sdcard/ui_model.xml "$outDir\ui_model.xml"
Write-Host "Model sheet opened and captured"
