. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== APPOPS LIST / CHECK ==="
& $adb shell "cmd appops get com.anthropic.claude"

Write-Host "=== TRY SETTING AUTO_START / BOOT / BACKGROUND ==="
& $adb shell "cmd appops set com.anthropic.claude AUTO_START allow"
& $adb shell "cmd appops set com.anthropic.claude OP_AUTO_START allow"
& $adb shell "cmd appops set com.anthropic.claude BOOT_COMPLETED allow"
& $adb shell "cmd appops set com.anthropic.claude RUN_IN_BACKGROUND allow"
& $adb shell "cmd appops set com.anthropic.claude RUN_ANY_IN_BACKGROUND allow"
& $adb shell "cmd appops set com.anthropic.claude START_FOREGROUND allow"
& $adb shell "cmd deviceidle whitelist +com.anthropic.claude"

Write-Host "=== CHECK APPOPS AFTER ==="
& $adb shell "cmd appops get com.anthropic.claude"

Write-Host "=== TOGGLE ACCESSIBILITY SERVICE TO RETRY BINDING ==="
& $adb shell "settings put secure enabled_accessibility_services com.anthropic.claude/com.anthropic.claude.tv.ClaudeTvAccessibilityService"
& $adb shell "settings put secure accessibility_enabled 0"
Start-Sleep -Seconds 1
& $adb shell "settings put secure accessibility_enabled 1"
Start-Sleep -Seconds 2

Write-Host "=== CHECK DUMPSYS ACCESSIBILITY ==="
& $adb shell "dumpsys accessibility services"

Write-Host "=== LOGCAT FOR TCL APP BOOT ==="
& $adb shell "logcat -d | grep -iE 'TclAppBoot|ClaudeTv' | tail -n 20"
