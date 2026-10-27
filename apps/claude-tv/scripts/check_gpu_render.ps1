. "$PSScriptRoot\load_env.ps1"
$adb = $env:ADB_PATH
$device = $env:TV_DEVICE
$outDir = $env:OUTPUT_DIR
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }
& $adb connect $device

Write-Host "=== 1. GRAPHICS / RENDERER PROPERTIES ==="
& $adb shell "getprop | grep -iE 'render|gpu|opengl|egl|skia|hwui|mali'"

Write-Host "=== 2. GFXINFO FOR CLAUDE ==="
& $adb shell "dumpsys gfxinfo com.anthropic.claude"

Write-Host "=== 3. SURFACEFLINGER HARDWARE COMPOSER ==="
& $adb shell "dumpsys SurfaceFlinger | grep -iE 'GLES|HWC|Mali|Software'"
