param(
    [string]$TvIp = ""
)

. "$PSScriptRoot\load_env.ps1"
if (-not $TvIp) { $TvIp = $env:TV_IP }
$adb = $env:ADB_PATH

Write-Host "Conectando ao ADB (${TvIp})..." -ForegroundColor Cyan
& $adb connect "${TvIp}:5555"

$targetPackages = @(
    @{ Name = "UniTV IPTV"; Pkg = "com.global.unitviptv" },
    @{ Name = "YouTube TV"; Pkg = "com.google.android.youtube.tv" },
    @{ Name = "YouTube Music TV"; Pkg = "com.google.android.youtube.tvmusic" },
    @{ Name = "Zeus BR"; Pkg = "com.isllantoso.zeusbr" }
)

Write-Host "`n=== ADICIONANDO PACOTES À WHITELIST DE ISENÇÃO DE ENERGIA / IDLE ===" -ForegroundColor Yellow
foreach ($app in $targetPackages) {
    Write-Host "Processando: $($app.Name) ($($app.Pkg))..."
    $resIdle = & $adb -s "${TvIp}:5555" shell dumpsys deviceidle whitelist +$($app.Pkg)
    Write-Host "  -> DeviceIdle: $resIdle"

    # Buscar UID
    $uidLine = & $adb -s "${TvIp}:5555" shell pm list packages -U $($app.Pkg)
    if ($uidLine -match "uid:(\d+)") {
        $uid = $Matches[1]
        $resNet = & $adb -s "${TvIp}:5555" shell cmd netpolicy add restrict-background-whitelist $uid 2>&1
        Write-Host "  -> NetPolicy Whitelist (UID $uid): Sucesso"
    }
}

Write-Host "`n=== CONFERÊNCIA DOS PACOTES NA WHITELIST DO DEVICEIDLE ===" -ForegroundColor Yellow
$whitelist = & $adb -s "${TvIp}:5555" shell dumpsys deviceidle whitelist
foreach ($app in $targetPackages) {
    if ($whitelist -match $app.Pkg) {
        Write-Host " [OK] $($app.Name) ($($app.Pkg)) presente na Whitelist!" -ForegroundColor Green
    } else {
        Write-Host " [FALHA] $($app.Name) não encontrado na whitelist." -ForegroundColor Red
    }
}
