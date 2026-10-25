$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555
& $adb shell "dumpsys package com.anthropic.claude | grep -E 'versionName|lastUpdateTime'"
& $adb logcat -d -s ClaudeTV ClaudeTvRtk
