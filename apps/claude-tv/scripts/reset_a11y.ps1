. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== RESETTING ACCESSIBILITY SETTINGS ==="
& $adb shell "settings put secure enabled_accessibility_services ''"
Start-Sleep -Seconds 1
& $adb shell "settings put secure enabled_accessibility_services 'com.anthropic.claude/com.anthropic.claude.tv.ClaudeTvAccessibilityService'"
& $adb shell "settings put secure accessibility_enabled 1"
Start-Sleep -Seconds 2

Write-Host "=== CHECK DUMPSYS ACCESSIBILITY ==="
& $adb shell "dumpsys accessibility services"

Write-Host "=== CHECK LOGCAT FOR CLAUDETV OR TCL ==="
& $adb shell "logcat -d -t 50" | Select-String -Pattern "ClaudeTv|TclAppBoot|Accessibility"
