param(
    [string]$TvIp = "192.168.76.209"
)

$ErrorActionPreference = "Continue"
$adb = "E:\Android\Sdk\platform-tools\adb.exe"
$projectRoot = "E:\projeto_twitchlit"

Write-Host "Conectando a TV em ${TvIp}:5555..." -ForegroundColor Cyan
& $adb connect "${TvIp}:5555"

$keyboards = @(
    @{ Name = "gboard";   Pkg = "com.google.android.inputmethod.latin";    Desc = "Gboard Android TV (Teclado do Google)" },
    @{ Name = "tcl_ime";  Pkg = "com.tcl.inputmethod.international";       Desc = "TCL T_IME (Teclado do Fabricante TCL)" }
)

foreach ($kb in $keyboards) {
    Write-Host "`n============================================================" -ForegroundColor Yellow
    Write-Host "Processando: $($kb.Desc) ($($kb.Pkg))" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow

    $apkDir = Join-Path $projectRoot "tv-system-backups\$($kb.Name)\apk"
    $decompDir = Join-Path $projectRoot "tv-system-backups\$($kb.Name)\decompiled"

    if (-not (Test-Path $apkDir)) { New-Item -ItemType Directory -Force -Path $apkDir | Out-Null }

    # 1. Puxar APKs da TV
    Write-Host "[1/3] Puxando APKs da TV..." -ForegroundColor Cyan
    $pathLines = & $adb -s "${TvIp}:5555" shell pm path $kb.Pkg
    $pulledApks = @()

    foreach ($line in ($pathLines -split "`r?`n")) {
        if ($line -match '^package:(.+)$') {
            $remotePath = $Matches[1].Trim()
            $fileName = Split-Path -Leaf $remotePath
            if ($fileName -eq "base.apk") {
                $fileName = "$($kb.Name)-base.apk"
            } elseif ($fileName.StartsWith("split_")) {
                $fileName = "$($kb.Name)-$fileName"
            }
            $localDest = Join-Path $apkDir $fileName
            Write-Host "  Puxando: $remotePath -> $fileName" -ForegroundColor Gray
            & $adb -s "${TvIp}:5555" pull $remotePath $localDest
            $pulledApks += $localDest
        }
    }

    # 2. Descompilar manifesto e recursos como backup
    $baseApk = $pulledApks | Where-Object { $_ -like "*base.apk" -or $_ -like "*T_IME.apk" } | Select-Object -First 1
    if (-not $baseApk -and $pulledApks.Count -gt 0) {
        $baseApk = $pulledApks[0]
    }

    if ($baseApk -and (Test-Path $baseApk)) {
        Write-Host "[2/3] Descompilando manifesto e recursos ($baseApk) para backup..." -ForegroundColor Cyan
        & apktool.cmd d -s -f -o $decompDir $baseApk
    }

    # 3. Compilar AOT speed na TV
    Write-Host "[3/3] Compilando para AOT speed na TV..." -ForegroundColor Cyan
    $compileRes = & $adb -s "${TvIp}:5555" shell cmd package compile -m speed -f $kb.Pkg
    Write-Host "  Resultado da compilacao: $compileRes" -ForegroundColor Green
}

# Verificacao final de dexopt
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "Verificando Estado Dexopt dos Teclados na TV..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

foreach ($kb in $keyboards) {
    $res = & $adb -s "${TvIp}:5555" shell dumpsys package dexopt | Select-String -Pattern $kb.Pkg -Context 0, 3
    Write-Host "$($kb.Desc):" -ForegroundColor Yellow
    $res | ForEach-Object { Write-Host $_ }
}

Write-Host "`n[OK] Otimizacao dos teclados concluida!" -ForegroundColor Green
