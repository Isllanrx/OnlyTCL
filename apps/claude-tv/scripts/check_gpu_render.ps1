$adb = "E:\Android\Sdk\platform-tools\adb.exe"
& $adb connect 192.168.76.209:5555

Write-Host "=== 1. GRAPHICS / RENDERER PROPERTIES ==="
& $adb shell "getprop | grep -iE 'render|gpu|opengl|egl|skia|hwui|mali'"

Write-Host "=== 2. GFXINFO FOR CLAUDE ==="
& $adb shell "dumpsys gfxinfo com.anthropic.claude"

Write-Host "=== 3. SURFACEFLINGER HARDWARE COMPOSER ==="
& $adb shell "dumpsys SurfaceFlinger | grep -iE 'GLES|HWC|Mali|Software'"
