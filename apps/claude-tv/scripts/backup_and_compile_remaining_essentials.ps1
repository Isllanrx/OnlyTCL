param(
    [string]$TvIp = "",
    [switch]$SkipDecompile,
    [switch]$SkipCompile
)

. "$PSScriptRoot\load_env.ps1"
$ErrorActionPreference = "Continue"
if (-not $TvIp) { $TvIp = $env:TV_IP }
$adb = $env:ADB_PATH
$projectRoot = $env:PROJECT_ROOT

Write-Host "Conectando a TV em ${TvIp}:5555..." -ForegroundColor Cyan
& $adb connect "${TvIp}:5555"

# Lista de aplicativos essenciais restantes mapeados para backup e AOT speed
$services = @(
    @{ 
        Name = "playstore";   
        Pkg  = "com.android.vending";                  
        Desc = "Google Play Store (Loja oficial e atualizador em background)" 
    },
    @{ 
        Name = "tcltv";       
        Pkg  = "com.tcl.tv";                           
        Desc = "TV ao Vivo e Sintonizador de Canais TCL" 
    },
    @{ 
        Name = "tvinput";     
        Pkg  = "com.tcl.tvinput";                      
        Desc = "Gerenciador de Entradas HDMI e TvPassThrough TCL" 
    },
    @{ 
        Name = "mediacenter"; 
        Pkg  = "com.tcl.ui_mediaCenter";               
        Desc = "Central de Mídia / Player Local e de Rede TCL" 
    },
    @{ 
        Name = "multiscreen"; 
        Pkg  = "com.tcl.MultiScreenInteraction_TV";    
        Desc = "Receptor DLNA DMR / T-Cast / Compartilhamento de Rede TCL" 
    },
    @{ 
        Name = "vlc";         
        Pkg  = "org.videolan.vlc";                     
        Desc = "VLC Media Player (Player de vídeo avançado para formatos locais/rede)" 
    }
)

foreach ($svc in $services) {
    Write-Host "`n============================================================" -ForegroundColor Yellow
    Write-Host "Processando: $($svc.Desc) ($($svc.Pkg))" -ForegroundColor Yellow
    Write-Host "============================================================" -ForegroundColor Yellow

    # 0. Garantir que o pacote está ativo no usuário 0 (caso tenha sido desativado em limpezas prévias)
    Write-Host "[0/4] Verificando se o pacote está habilitado para o usuário 0..." -ForegroundColor Cyan
    & $adb -s "${TvIp}:5555" shell "cmd package install-existing --user 0 $($svc.Pkg) 2>/dev/null; pm enable --user 0 $($svc.Pkg) 2>/dev/null" | Out-Null

    $apkDir = Join-Path $projectRoot "tv-system-backups\$($svc.Name)\apk"
    $decompDir = Join-Path $projectRoot "tv-system-backups\$($svc.Name)\decompiled"

    if (-not (Test-Path $apkDir)) { New-Item -ItemType Directory -Force -Path $apkDir | Out-Null }

    # 1. Puxar APKs da TV para o VS Code
    Write-Host "[1/4] Consultando caminhos dos APKs na TV..." -ForegroundColor Cyan
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

    # 2. Descompilar o APK base como backup / engenharia reversa
    if (-not $SkipDecompile) {
        $baseApk = $pulledApks | Where-Object { $_ -like "*-base.apk" -or $_ -like "*base.apk" } | Select-Object -First 1
        if (-not $baseApk -and $pulledApks.Count -gt 0) {
            $baseApk = $pulledApks[0]
        }

        if ($baseApk -and (Test-Path $baseApk)) {
            Write-Host "[2/4] Descompilando APK base ($baseApk) para backup..." -ForegroundColor Cyan
            & apktool.cmd d -s -f -o $decompDir $baseApk
        } else {
            Write-Warning "Nenhum APK encontrado para descompilar em $($svc.Name)"
        }
    } else {
        Write-Host "[2/4] Descompilação pulada (-SkipDecompile)." -ForegroundColor Gray
    }

    # 3. Compilação AOT "speed" na TV
    if (-not $SkipCompile) {
        Write-Host "[3/4] Compilando pacote na TV com AOT speed..." -ForegroundColor Cyan
        & $adb -s "${TvIp}:5555" shell cmd package compile -m speed -f $svc.Pkg
        
        # 4. Verificar Dexopt State
        Write-Host "[4/4] Estado Dexopt:" -ForegroundColor Green
        & $adb -s "${TvIp}:5555" shell dumpsys package $svc.Pkg | Select-String -Pattern 'Dexopt state' -Context 0,4
    } else {
        Write-Host "[3/4] e [4/4] Compilação AOT pulada (-SkipCompile)." -ForegroundColor Gray
    }
}

Write-Host "`nPROCESSO DE BACKUP LOCAL E PROMOÇÃO AOT CONCLUÍDOS COM SUCESSO!" -ForegroundColor Green
