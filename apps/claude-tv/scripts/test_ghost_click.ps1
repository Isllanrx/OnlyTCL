. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device
& $adb shell "input tap 1850 60" # Tap ghost icon on top right
Start-Sleep -Seconds 1
& $adb shell "screencap -p /sdcard/ghost_tapped.png"
& $adb pull /sdcard/ghost_tapped.png "$outDir\ghost_tapped.png"
