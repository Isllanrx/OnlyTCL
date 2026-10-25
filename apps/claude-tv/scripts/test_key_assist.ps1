$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== SENDING KEYCODE_VOICE_ASSIST (231) ==="
& $adb shell "input keyevent 231"
Start-Sleep -Seconds 2

Write-Host "=== CURRENT FOCUS ==="
& $adb shell "dumpsys window | grep -E mCurrentFocus"

Write-Host "=== LOGCAT FOR ClaudeTvA11y ==="
& $adb shell "logcat -d -t 30" | Select-String -Pattern "ClaudeTv|AssistantOverlayActivity"
