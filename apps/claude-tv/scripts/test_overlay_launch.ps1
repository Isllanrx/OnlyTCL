$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== LAUNCHING ASSISTANT OVERLAY ACTIVITY ==="
& $adb shell "am start -n com.anthropic.claude/.mainactivity.AssistantOverlayActivity -a android.intent.action.VOICE_ASSIST -f 0x34000000"
Start-Sleep -Seconds 3

Write-Host "=== CURRENT FOCUS ==="
& $adb shell "dumpsys window | grep -E mCurrentFocus"

Write-Host "=== TAKING SCREENSHOT ==="
& $adb shell "screencap -p /sdcard/overlay_screen.png"
& $adb pull /sdcard/overlay_screen.png claude-tv/screenshots/overlay_screen.png
