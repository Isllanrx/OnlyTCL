. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== LAUNCHING ASSISTANT OVERLAY ACTIVITY ==="
& $adb shell "am start -n com.anthropic.claude/.mainactivity.AssistantOverlayActivity -a android.intent.action.VOICE_ASSIST -f 0x34000000"
Start-Sleep -Seconds 3

Write-Host "=== CURRENT FOCUS ==="
& $adb shell "dumpsys window | grep -E mCurrentFocus"

Write-Host "=== TAKING SCREENSHOT ==="
& $adb shell "screencap -p /sdcard/overlay_screen.png"
& $adb pull /sdcard/overlay_screen.png claude-tv/screenshots/overlay_screen.png
