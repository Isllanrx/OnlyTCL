$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555
& $adb shell "settings get secure enabled_accessibility_services"
& $adb shell "settings get secure accessibility_enabled"
