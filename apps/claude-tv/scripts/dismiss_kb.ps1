. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device
# Dismiss keyboard
& $adb shell "input keyevent 4"
Start-Sleep -Seconds 1
# Capture screenshot without keyboard
& $adb shell "screencap -p /sdcard/tv_chat_clean.png"
& $adb pull /sdcard/tv_chat_clean.png "$outDir\tv_chat_clean.png"
# Dump UI hierarchy
& $adb shell "uiautomator dump /sdcard/ui_chat.xml"
& $adb pull /sdcard/ui_chat.xml "$outDir\ui_chat.xml"
Write-Host "Done"
