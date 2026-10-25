$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== SETTING CLAUDE AS DEFAULT ASSISTANT ==="
& $adb shell "settings put secure assistant com.anthropic.claude/com.anthropic.claude.bell.assist.ClaudeVoiceInteractionService"
& $adb shell "settings put secure voice_interaction_service com.anthropic.claude/com.anthropic.claude.bell.assist.ClaudeVoiceInteractionService"
& $adb shell "settings put secure voice_recognition_service com.anthropic.claude/com.anthropic.claude.bell.assist.ClaudeRecognitionService"

Write-Host "=== VERIFYING SETTINGS ==="
& $adb shell "settings get secure assistant"
& $adb shell "settings get secure voice_interaction_service"

Write-Host "=== SENDING KEYCODE_VOICE_ASSIST (231) ==="
& $adb shell "input keyevent 231"
Start-Sleep -Seconds 2

Write-Host "=== CURRENT FOCUS ==="
& $adb shell "dumpsys window | grep -E mCurrentFocus"

Write-Host "=== LOGCAT ==="
& $adb shell "logcat -d -t 30" | Select-String -Pattern "anthropic|VoiceInteraction|katniss"
