. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

& $adb shell "uiautomator dump /sdcard/ui_dump.xml"
& $adb pull /sdcard/ui_dump.xml claude-tv/screenshots/ui_dump.xml
Write-Host "UI dump pulled successfully"
