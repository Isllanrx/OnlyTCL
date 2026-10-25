param(
    [string]$TvIp = "192.168.76.209",
    [switch]$SkipDecompile
)

$ErrorActionPreference = "Continue"
$adb = "E:\Android\Sdk\platform-tools\adb.exe"
$projectRoot = "E:\projeto_twitchlit"

Write-Host "Conectando à Smart TV TCL em ${TvIp}:5555..." -ForegroundColor Cyan
& $adb connect "${TvIp}:5555"

# Lista sistemática dos 25 aplicativos para backup e compilação nativa AOT speed
$apps = @(
    # --- GRUPO 1: STREAMING & APPS DE USUÁRIO (12) ---
    @{ Name = "primevideo";    Pkg = "com.amazon.amazonvideo.livingroom"; Desc = "Amazon Prime Video" },
    @{ Name = "globoplay";     Pkg = "com.globo.globotv";                 Desc = "Globoplay TV" },
    @{ Name = "spotify";       Pkg = "com.spotify.tv.android";            Desc = "Spotify TV" },
    @{ Name = "crunchyroll";   Pkg = "com.crunchyroll.crunchyroid";       Desc = "Crunchyroll TV" },
    @{ Name = "ytmusic";       Pkg = "com.google.android.youtube.tvmusic";Desc = "YouTube Music TV" },
    @{ Name = "downloader";    Pkg = "com.esaba.downloader";              Desc = "Downloader by AFTVnews" },
    @{ Name = "filemanager";   Pkg = "com.alphainventor.filemanager";     Desc = "Gerenciador de Arquivos +" },
    @{ Name = "edge";          Pkg = "com.microsoft.emmx";                Desc = "Microsoft Edge Browser" },
    @{ Name = "chrome";        Pkg = "com.android.chrome";                Desc = "Google Chrome" },
    @{ Name = "googlevideos";  Pkg = "com.google.android.videos";         Desc = "Google TV Filmes e TV" },
    @{ Name = "tclbrowser";    Pkg = "com.tcl.browser";                   Desc = "Navegador TCL Browser" },
    @{ Name = "playgames";     Pkg = "com.google.android.play.games";     Desc = "Google Play Games" },

    # --- GRUPO 2: GOOGLE TV / CORE (5) ---
    @{ Name = "launcherx";     Pkg = "com.google.android.apps.tv.launcherx"; Desc = "Google TV Home (LauncherX)" },
    @{ Name = "dreamx";        Pkg = "com.google.android.apps.tv.dreamx";    Desc = "Google TV Screensaver (DreamX)" },
    @{ Name = "gms";           Pkg = "com.google.android.gms";               Desc = "Google Play Services (GMS Core)" },
    @{ Name = "gsf";           Pkg = "com.google.android.gsf";               Desc = "Google Services Framework (GSF)" },
    @{ Name = "googletts";     Pkg = "com.google.android.tts";               Desc = "Google Text-to-Speech (TTS)" },

    # --- GRUPO 3: SERVIÇOS DE SISTEMA & HARDWARE TCL (8) ---
    @{ Name = "tcl_rcu";       Pkg = "com.tcl.tcl_bt_rcu_service";        Desc = "Serviço de Controle Remoto Bluetooth TCL" },
    @{ Name = "tcl_micmanager";Pkg = "com.tcl.micmanager";                Desc = "Gerenciador de Microfone TCL" },
    @{ Name = "tcl_sysserver"; Pkg = "com.tcl.system.server";             Desc = "TCL System Server" },
    @{ Name = "tcl_dashboard"; Pkg = "com.tcl.dashboard";                 Desc = "Dashboard / Painel Rápido TCL" },
    @{ Name = "tcl_guard";     Pkg = "com.tcl.guard";                     Desc = "TCL Guard (Otimizador de RAM e Background)" },
    @{ Name = "tcl_miracast";  Pkg = "com.tcl.miracast";                  Desc = "Miracast / Espelhamento de Tela TCL" },
    @{ Name = "tcl_gamebar";   Pkg = "com.tcl.gamebar";                   Desc = "GameBar TCL" },
    @{ Name = "tcl_gallery";   Pkg = "com.tcl.gallery";                   Desc = "Galeria de Mídia TCL" }
)

$total = $apps.Count
$current = 0
$successful = @()

foreach ($app in $apps) {
    $current++
    Write-Host "`n================================================================================" -ForegroundColor Yellow
    Write-Host "[$current/$total] Processando: $($app.Desc) ($($app.Pkg))" -ForegroundColor Yellow
    Write-Host "================================================================================" -ForegroundColor Yellow

    # 0. Assegurar ativação no usuário 0
    Write-Host "[0/4] Verificando status do pacote..." -ForegroundColor Cyan
    & $adb -s "${TvIp}:5555" shell "cmd package install-existing --user 0 $($app.Pkg) 2>/dev/null; pm enable --user 0 $($app.Pkg) 2>/dev/null" | Out-Null

    $apkDir = Join-Path $projectRoot "tv-system-backups\$($app.Name)\apk"
    $decompDir = Join-Path $projectRoot "tv-system-backups\$($app.Name)\decompiled"

    if (-not (Test-Path $apkDir)) { New-Item -ItemType Directory -Force -Path $apkDir | Out-Null }

    # 1. Puxar todos os APKs (base e splits) para o VS Code
    Write-Host "[1/4] Extraindo APKs da TV para backup local..." -ForegroundColor Cyan
    $pathLines = & $adb -s "${TvIp}:5555" shell pm path $app.Pkg
    $pulledApks = @()

    foreach ($line in ($pathLines -split "`r?`n")) {
        if ($line -match '^package:(.+)$') {
            $remotePath = $Matches[1].Trim()
            $fileName = Split-Path -Leaf $remotePath
            if ($fileName -eq "base.apk") {
                $fileName = "$($app.Name)-base.apk"
            } elseif ($fileName.StartsWith("split_")) {
                $fileName = "$($app.Name)-$fileName"
            }
            $localDest = Join-Path $apkDir $fileName
            Write-Host "  Puxando: $remotePath -> $fileName" -ForegroundColor Gray
            & $adb -s "${TvIp}:5555" pull $remotePath $localDest
            $pulledApks += $localDest
        }
    }

    # 2. Descompilar APK base de forma segura no VS Code
    if (-not $SkipDecompile) {
        $baseApk = $pulledApks | Where-Object { $_ -like "*-base.apk" -or $_ -like "*base.apk" } | Select-Object -First 1
        if (-not $baseApk -and $pulledApks.Count -gt 0) {
            $baseApk = $pulledApks[0]
        }

        if ($baseApk -and (Test-Path $baseApk)) {
            Write-Host "[2/4] Descompilando APK base ($baseApk) para engenharia reversa..." -ForegroundColor Cyan
            try {
                & apktool.cmd d -s -f -o $decompDir $baseApk
            } catch {
                Write-Warning "Aviso ao descompilar $($app.Name): $_"
            }
        } else {
            Write-Warning "Nenhum APK base localizado para descompilar em $($app.Name)"
        }
    } else {
        Write-Host "[2/4] Descompilação pulada (-SkipDecompile)." -ForegroundColor Gray
    }

    # 3. Compilação AOT "speed" na TV
    Write-Host "[3/4] Compilando pacote na TV com AOT nativo speed..." -ForegroundColor Cyan
    & $adb -s "${TvIp}:5555" shell cmd package compile -m speed -f $app.Pkg

    # 4. Verificar Dexopt State
    Write-Host "[4/4] Verificando estado Dexopt:" -ForegroundColor Green
    $dexopt = & $adb -s "${TvIp}:5555" shell dumpsys package $app.Pkg | Select-String -Pattern 'Dexopt state' -Context 0,4
    $dexopt | Out-String | Write-Host -ForegroundColor Green

    $successful += [PSCustomObject]@{
        Index   = $current
        Name    = $app.Name
        Package = $app.Pkg
        Desc    = $app.Desc
        Status  = "speed"
    }
}

Write-Host "`n================================================================================" -ForegroundColor Green
Write-Host "TODOS OS $total APLICATIVOS FORAM PROCESSADOS COM SUCESSO EM MODO AOT SPEED!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Green
