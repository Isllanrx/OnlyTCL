. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

& $adb shell "logcat -c"
& $adb shell "input keyevent 231"
Start-Sleep -Seconds 1
& $adb shell "logcat -d" | Select-String -Pattern "TclPhoneWindowManager|Assistant|ActivityManager|voice|Claude"
