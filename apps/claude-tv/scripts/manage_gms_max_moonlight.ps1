param(
    [string]$TvIp = "192.168.76.209"
)

$ErrorActionPreference = "Continue"
$adb = "E:\Android\Sdk\platform-tools\adb.exe"
$projectRoot = "E:\projeto_twitchlit"

Write-Host "Conectando a TV em ${TvIp}:5555..." -ForegroundColor Cyan
& $adb connect "${TvIp}:5555"

# ==============================================================================
# 1. Desinstalar Max (HBO)
# ==============================================================================
Write-Host "`n============================================================" -ForegroundColor Yellow
Write-Host "[1/3] Removendo Max (com.wbd.stream) da TV..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow

$uninstallResult = & $adb -s "${TvIp}:5555" uninstall com.wbd.stream
Write-Host "Resultado da desinstalacao do Max: $uninstallResult" -ForegroundColor Green

# ==============================================================================
# 2. Backup e Compilacao AOT (speed) do Google Play Services
# ==============================================================================
Write-Host "`n============================================================" -ForegroundColor Yellow
Write-Host "[2/3] Backup e Compilacao AOT do Google Play Services (com.google.android.gms)..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow

$gmsApkDir = Join-Path $projectRoot "gms\apk"
$gmsDecompDir = Join-Path $projectRoot "gms\decompiled"

if (-not (Test-Path $gmsApkDir)) { New-Item -ItemType Directory -Force -Path $gmsApkDir | Out-Null }

Write-Host "  Puxando APKs do Google Play Services da TV..." -ForegroundColor Cyan
$pathLines = & $adb -s "${TvIp}:5555" shell pm path com.google.android.gms
$pulledApks = @()

foreach ($line in ($pathLines -split "`r?`n")) {
    if ($line -match '^package:(.+)$') {
        $remotePath = $Matches[1].Trim()
        $fileName = Split-Path -Leaf $remotePath
        if ($fileName -eq "base.apk") {
            $fileName = "gms-base.apk"
        } elseif ($fileName.StartsWith("split_")) {
            $fileName = "gms-$fileName"
        }
        $localDest = Join-Path $gmsApkDir $fileName
        Write-Host "  Puxando: $remotePath -> $fileName" -ForegroundColor Gray
        & $adb -s "${TvIp}:5555" pull $remotePath $localDest
        $pulledApks += $localDest
    }
}

$baseApk = $pulledApks | Where-Object { $_ -like "*gms-base.apk" -or $_ -like "*base.apk" } | Select-Object -First 1
if ($baseApk -and (Test-Path $baseApk)) {
    Write-Host "  Descompilando manifesto e recursos do Google Play Services para backup..." -ForegroundColor Cyan
    & apktool.cmd d -s -f -o $gmsDecompDir $baseApk
}

Write-Host "  Compilando Google Play Services para AOT speed na TV..." -ForegroundColor Cyan
$compileGms = & $adb -s "${TvIp}:5555" shell cmd package compile -m speed -f com.google.android.gms
Write-Host "  Resultado da compilacao: $compileGms" -ForegroundColor Green

# ==============================================================================
# 3. Compilacao AOT (speed) do Moonlight Game Streaming
# ==============================================================================
Write-Host "`n============================================================" -ForegroundColor Yellow
Write-Host "[3/3] Compilando Moonlight (com.limelight) para AOT speed..." -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow

$compileMoonlight = & $adb -s "${TvIp}:5555" shell cmd package compile -m speed -f com.limelight
Write-Host "  Resultado da compilacao: $compileMoonlight" -ForegroundColor Green

# ==============================================================================
# Verificacao do Estado Dexopt
# ==============================================================================
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "Verificando Estado Dexopt dos Pacotes na TV..." -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$dexoptGms = & $adb -s "${TvIp}:5555" shell dumpsys package dexopt | Select-String -Pattern "com.google.android.gms" -Context 0, 3
Write-Host "Google Play Services Dexopt:" -ForegroundColor Yellow
$dexoptGms | ForEach-Object { Write-Host $_ }

$dexoptMoonlight = & $adb -s "${TvIp}:5555" shell dumpsys package dexopt | Select-String -Pattern "com.limelight" -Context 0, 3
Write-Host "`nMoonlight Dexopt:" -ForegroundColor Yellow
$dexoptMoonlight | ForEach-Object { Write-Host $_ }

Write-Host "`n[OK] Processo concluido com sucesso!" -ForegroundColor Green
