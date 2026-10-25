#!/usr/bin/env bash
set -e
ADB="${ADB:-adb}"
$ADB devices
$ADB install -r apks/zeusbr-tv.apk
$ADB install -r apks/gamepass-tv-custom.apk
$ADB shell pm grant gamepass.fire.tv android.permission.WRITE_SECURE_SETTINGS
$ADB install -r apks/claude-tv.apk
$ADB shell pm grant com.anthropic.claude android.permission.RECORD_AUDIO
$ADB shell settings put secure enabled_accessibility_services com.anthropic.claude/com.anthropic.claude.tv.ClaudeTvAccessibilityService
$ADB shell settings put secure accessibility_enabled 1
$ADB install -r apks/tv-home.apk
$ADB install -r apks/zeusremote.apk
$ADB shell cmd package compile -m speed -f com.isllantoso.zeusbr
$ADB shell cmd package compile -m speed -f gamepass.fire.tv
$ADB shell cmd package compile -m speed -f com.anthropic.claude
$ADB shell cmd package compile -m speed -f com.ansub.tvhome
