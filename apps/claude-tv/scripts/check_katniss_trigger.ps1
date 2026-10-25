$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

& $adb shell "logcat -d -t 150" | Select-String -Pattern "Katniss|katniss|PhoneWindow|intercept|voice|assist"
