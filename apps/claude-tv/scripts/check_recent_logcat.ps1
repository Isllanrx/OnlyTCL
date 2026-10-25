$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== LOGCAT RECENT 50 LINES FOR ACCESSIBILITY ==="
& $adb shell "logcat -d -t 100" | Select-String -Pattern "accessibility|ClaudeTv|TclAppBoot|ActivityManager"
