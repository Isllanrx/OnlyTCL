$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== 1. ALWAYS FINISH ACTIVITIES ==="
& $adb shell "settings get global always_finish_activities"

Write-Host "=== 2. BACKGROUND PROCESS LIMIT ==="
& $adb shell "settings get global background_process_limit"

Write-Host "=== 3. ASSISTANT SETTINGS ==="
& $adb shell "settings get secure assistant"
& $adb shell "settings get secure voice_interaction_service"
& $adb shell "settings get secure voice_recognition_service"

Write-Host "=== 4. ACCESSIBILITY SERVICES ==="
& $adb shell "settings get secure enabled_accessibility_services"
& $adb shell "settings get secure accessibility_enabled"

Write-Host "=== 5. RUNNING PROCESSES (CLAUDE & ASSISTANT) ==="
& $adb shell "ps -A | grep -E 'anthropic|katniss|google'"

Write-Host "=== 6. BATTERY WHITELIST / DEVICEIDLE ==="
& $adb shell "dumpsys deviceidle whitelist | grep anthropic"

Write-Host "=== 7. APPOPS RUN IN BACKGROUND ==="
& $adb shell "cmd appops get com.anthropic.claude RUN_IN_BACKGROUND"
& $adb shell "cmd appops get com.anthropic.claude RUN_ANY_IN_BACKGROUND"

Write-Host "=== 8. DUMPSYS ACCESSIBILITY SERVICE DETAILS ==="
& $adb shell "dumpsys accessibility services"
