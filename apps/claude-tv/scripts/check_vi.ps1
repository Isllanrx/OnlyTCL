$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== DUMPSYS PACKAGE CLAUDE SERVICES ==="
& $adb shell "dumpsys package com.anthropic.claude" | Select-String -Pattern "VoiceInteraction|AccessibilityService|AssistantOverlay" -Context 3,3

Write-Host "=== LOGCAT FOR VOICE INTERACTION ==="
& $adb shell "logcat -d" | Select-String -Pattern "VoiceInteractionManagerService|VoiceInteraction"
