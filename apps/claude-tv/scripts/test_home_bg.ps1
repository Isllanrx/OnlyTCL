$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== SENDING HOME KEY ==="
& $adb shell "input keyevent 3"
Start-Sleep -Seconds 3

Write-Host "=== CURRENT FOCUS ==="
& $adb shell "dumpsys window | grep -E mCurrentFocus"

Write-Host "=== ACCESSIBILITY BOUND SERVICES ==="
& $adb shell "dumpsys accessibility services"

Write-Host "=== RUNNING PROCESSES ==="
& $adb shell "ps -A | grep anthropic"
