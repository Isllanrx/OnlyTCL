$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== CURRENT TOP RESUMED ACTIVITY ==="
& $adb shell "dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity'"

Write-Host "=== ALL VISIBLE WINDOWS ==="
& $adb shell "dumpsys window windows | grep -E 'Window #|package='"
