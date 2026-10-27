. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device
& $adb shell "dumpsys package com.anthropic.claude | grep -E 'versionName|lastUpdateTime'"
& $adb logcat -d -s ClaudeTV ClaudeTvRtk
