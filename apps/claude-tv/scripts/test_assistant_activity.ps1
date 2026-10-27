. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== CONFIGURING ASSISTANT TO OVERLAY ACTIVITY ==="
& $adb shell "settings put secure assistant com.anthropic.claude/.mainactivity.AssistantOverlayActivity"
& $adb shell "settings put secure voice_interaction_service ''"

Write-Host "=== VERIFY SETTINGS ==="
& $adb shell "settings get secure assistant"
& $adb shell "settings get secure voice_interaction_service"

Write-Host "=== SENDING KEYCODE_VOICE_ASSIST (231) ==="
& $adb shell "input keyevent 231"
Start-Sleep -Seconds 2

Write-Host "=== CURRENT FOCUS ==="
& $adb shell "dumpsys window | grep -E mCurrentFocus"

Write-Host "=== LOGCAT ==="
& $adb shell "logcat -d -t 30" | Select-String -Pattern "AssistantOverlayActivity|TclPhoneWindowManager|anthropic"
