. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device
& $adb shell "input keyevent 4" # KEYCODE_BACK
Start-Sleep -Milliseconds 600
& $adb shell "screencap -p /sdcard/after_back.png"
& $adb pull /sdcard/after_back.png "$outDir\after_back.png"
