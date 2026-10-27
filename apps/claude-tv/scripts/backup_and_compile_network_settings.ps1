param(
    [string]$TvIp = ""
)

. "$PSScriptRoot\load_env.ps1"
$ErrorActionPreference = "Continue"
if (-not $TvIp) { $TvIp = $env:TV_IP }
$adb = $env:ADB_PATH
$projectRoot = $env:PROJECT_ROOT

Write-Host "Conectando a TV em ${TvIp}:5555..." -ForegroundColor Cyan
& $adb connect "${TvIp}:5555"

$services = @(
    @{ Name = "tvsettings";   Pkg = "com.android.tv.settings";            Desc = "Configurações do Android TV (Menus Leanback)" },
    @{ Name = "tclsettings";  Pkg = "com.tcl.settings";                   Desc = "Configurações do Sistema TCL" },
    @{ Name = "networkstack"; Pkg = "com.android.networkstack.inprocess";  Desc = "Android Network Stack (Motor de Conectividade/DHCP/DNS)" }
)

foreach ($svc in $services) {
    Write-Host "`n============================================================" -ForegroundColor Yellow
    Write-Host "Processando: $($svc.Desc) ($($svc.Pkg))" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow

    $apkDir = Join-Path $projectRoot "tv-system-backups\$($svc.Name)\apk"
    $decompDir = Join-Path $projectRoot "tv-system-backups\$($svc.Name)\decompiled"

    if (-not (Test-Path $apkDir)) { New-Item -ItemType Directory -Force -Path $apkDir | Out-Null }

    # 1. Puxar APKs
    Write-Host "[1/3] Consultando caminhos dos APKs na TV..." -ForegroundColor Cyan
    $pathLines = & $adb -s "${TvIp}:5555" shell pm path $svc.Pkg
    $pulledApks = @()

    foreach ($line in ($pathLines -split "`r?`n")) {
        if ($line -match '^package:(.+)$') {
            $remotePath = $Matches[1].Trim()
            $fileName = Split-Path -Leaf $remotePath
            if ($fileName -eq "base.apk") {
                $fileName = "$($svc.Name)-base.apk"
            } elseif ($fileName.StartsWith("split_")) {
                $fileName = "$($svc.Name)-$fileName"
            }
            $localDest = Join-Path $apkDir $fileName
            Write-Host "  Puxando: $remotePath -> $fileName" -ForegroundColor Gray
            & $adb -s "${TvIp}:5555" pull $remotePath $localDest
            $pulledApks += $localDest
        }
    }

    # 2. Descompilar o APK base como backup
    $baseApk = $pulledApks | Where-Object { $_ -like "*-base.apk" -or $_ -like "*base.apk" } | Select-Object -First 1
    if (-not $baseApk -and $pulledApks.Count -gt 0) {
        $baseApk = $pulledApks[0]
    }

    if ($baseApk -and (Test-Path $baseApk)) {
        Write-Host "[2/3] Descompilando APK base ($baseApk) para backup..." -ForegroundColor Cyan
        & apktool.cmd d -s -f -o $decompDir $baseApk
    } else {
        Write-Warning "Nenhum APK encontrado para descompilar em $($svc.Name)"
    }

    # 3. Compilação AOT "speed" na TV
    Write-Host "[3/3] Compilando pacote na TV com AOT speed..." -ForegroundColor Cyan
    & $adb -s "${TvIp}:5555" shell cmd package compile -m speed -f $svc.Pkg
    
    # 4. Verificar Dexopt State
    Write-Host "Estado Dexopt:" -ForegroundColor Green
    & $adb -s "${TvIp}:5555" shell "dumpsys package $($svc.Pkg) | grep -A4 'Dexopt state'"
}

Write-Host "`nPROMOÇÃO AOT E BACKUPS DE REDE/SETTINGS CONCLUÍDOS COM SUCESSO!" -ForegroundColor Green
