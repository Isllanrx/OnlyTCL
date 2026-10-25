$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== GLOBAL VOICE SETTINGS ==="
& $adb shell "settings list global" | Select-String -Pattern "voice|assist|hotkey|mic|remote"

Write-Host "=== SECURE VOICE SETTINGS ==="
& $adb shell "settings list secure" | Select-String -Pattern "voice|assist|hotkey|mic|remote"
