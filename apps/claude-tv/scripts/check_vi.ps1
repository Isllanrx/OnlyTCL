. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== DUMPSYS PACKAGE CLAUDE SERVICES ==="
& $adb shell "dumpsys package com.anthropic.claude" | Select-String -Pattern "VoiceInteraction|AccessibilityService|AssistantOverlay" -Context 3,3

Write-Host "=== LOGCAT FOR VOICE INTERACTION ==="
& $adb shell "logcat -d" | Select-String -Pattern "VoiceInteractionManagerService|VoiceInteraction"
