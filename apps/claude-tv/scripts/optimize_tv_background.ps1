$adb = "E:\Android\Sdk\platform-tools\adb.exe"
$dev = "192.168.76.209:5555"
& $adb connect $dev | Out-Null

Write-Host "1. Whitelisting Claude and granting full background priorities..." -ForegroundColor Cyan
& $adb -s $dev shell cmd deviceidle whitelist +com.anthropic.claude
& $adb -s $dev shell cmd appops set com.anthropic.claude RUN_IN_BACKGROUND allow
& $adb -s $dev shell cmd appops set com.anthropic.claude RUN_ANY_IN_BACKGROUND allow
& $adb -s $dev shell cmd appops set com.anthropic.claude START_FOREGROUND allow
& $adb -s $dev shell cmd appops set com.anthropic.claude APP_AUTO_START allow

Write-Host "2. Enforcing background process limit to prevent background app accumulation..." -ForegroundColor Cyan
& $adb -s $dev shell settings put global background_process_limit 1

Write-Host "3. Stopping background heavy apps and restricting their background permissions..." -ForegroundColor Cyan
$heavyApps = @(
    "com.netflix.ninja",
    "org.videolan.vlc",
    "com.global.unitviptv"
)

foreach ($pkg in $heavyApps) {
    & $adb -s $dev shell am force-stop $pkg
    & $adb -s $dev shell cmd appops set $pkg RUN_IN_BACKGROUND ignore
    & $adb -s $dev shell cmd appops set $pkg RUN_ANY_IN_BACKGROUND ignore
    Write-Host "Restricted $pkg" -ForegroundColor Yellow
}

Write-Host "`n4. Current deviceidle whitelist verification:" -ForegroundColor Green
& $adb -s $dev shell dumpsys deviceidle whitelist | Select-String "anthropic"

Write-Host "`nBackground optimization completed successfully!" -ForegroundColor Green
