$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

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
