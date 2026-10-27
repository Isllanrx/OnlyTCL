. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device
& $adb shell "input keyevent 111" # KEYCODE_ESCAPE
Start-Sleep -Milliseconds 500
& $adb shell "input keyevent 4" # KEYCODE_BACK
Start-Sleep -Milliseconds 500
& $adb shell "screencap -p /sdcard/ime_test.png"
& $adb pull /sdcard/ime_test.png "$outDir\ime_test.png"
