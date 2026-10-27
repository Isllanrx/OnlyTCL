. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device
& $adb shell input keyevent 111
Start-Sleep -Seconds 1
& $adb shell screencap -p /sdcard/tv_final_clean.png
& $adb pull /sdcard/tv_final_clean.png "$outDir\tv_final_clean.png"
Write-Host "CLEAN_PULLED_SUCCESS"
