$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

& $adb shell "logcat -c"
& $adb shell "input keyevent 231"
Start-Sleep -Seconds 1
& $adb shell "logcat -d" | Select-String -Pattern "TclPhoneWindowManager|Assistant|ActivityManager|voice|Claude"
