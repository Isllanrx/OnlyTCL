. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== SET APP_AUTO_START allow ==="
& $adb shell "cmd appops set com.anthropic.claude APP_AUTO_START allow"

Write-Host "=== VERIFY APPOPS ==="
& $adb shell "cmd appops get com.anthropic.claude APP_AUTO_START"

Write-Host "=== TOGGLE ACCESSIBILITY ==="
& $adb shell "settings put secure enabled_accessibility_services com.anthropic.claude/com.anthropic.claude.tv.ClaudeTvAccessibilityService"
& $adb shell "settings put secure accessibility_enabled 0"
Start-Sleep -Seconds 1
& $adb shell "settings put secure accessibility_enabled 1"
Start-Sleep -Seconds 2

Write-Host "=== CHECK BOUND SERVICES ==="
& $adb shell "dumpsys accessibility services"
