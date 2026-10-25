param (
    [string]$TvIp = "",
    [string]$ApkPath = "",
    [switch]$ConfigureAssistant,
    [switch]$SkipAot
)

# Instala o APK na TV sem abrir o app, sem iniciar voz e sem tocar em volume/animações.
# Depois da instalação compila o pacote em modo AOT "speed" (mesma lição do ZeusBR):
# o APK reassinado perde o perfil de nuvem do Play, e sem AOT a MainActivity levou 8,6 s
# até "Fully drawn" na TCL (A55 1,3 GHz, dex de 34 MB rodando só com JIT).

$adb = "E:\Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path $adb)) {
    $adb = "adb"
}

$apk = if ($ApkPath) { $ApkPath } else { Join-Path $PSScriptRoot "..\release\claude-tv-1.260930-20-candidate.apk" }
if (-not (Test-Path $apk)) {
    Write-Error "APK não encontrado em: $apk"
    exit 1
}

if ($TvIp) {
    Write-Host "Conectando à Smart TV em ${TvIp}:5555..." -ForegroundColor Cyan
    & $adb connect "$TvIp`:5555"
}

Write-Host "Verificando dispositivos conectados via ADB..." -ForegroundColor Cyan
& $adb devices
$device = if ($TvIp) { "$TvIp`:5555" } else {
    $connected = @(& $adb devices | Select-String -Pattern '^\S+\s+device$')
    if ($connected.Count -ne 1) { throw "Informe -TvIp quando houver zero ou vários dispositivos ADB" }
    $connected[0].ToString().Split()[0]
}

Write-Host "`nInstalando Claude TV APK..." -ForegroundColor Green
& $adb -s $device install -r $apk

if ($LASTEXITCODE -ne 0) {
    Write-Error "Falha ao instalar o APK via ADB. Verifique a conexão com a TV."
    exit 1
}

& $adb -s $device shell pm grant com.anthropic.claude android.permission.RECORD_AUDIO
if ($LASTEXITCODE -ne 0) { throw "APK instalado, mas RECORD_AUDIO não foi concedida" }

if (-not $SkipAot) {
    Write-Host "`nCompilando AOT (speed) para eliminar JIT na abertura..." -ForegroundColor Cyan
    # Demora 1–3 min na TCL. Reversível: cmd package compile --reset com.anthropic.claude
    & $adb -s $device shell cmd package compile -m speed -f com.anthropic.claude
    if ($LASTEXITCODE -ne 0) { Write-Warning "Compilação AOT falhou; o app funciona, mas abre mais lento." }
    & $adb -s $device shell "dumpsys package com.anthropic.claude | grep -A3 'Dexopt state'"
}

Write-Host "`n[SUCESSO] Claude TV instalado na Smart TV (sem abrir o app)." -ForegroundColor Green
if ($ConfigureAssistant) {
    & (Join-Path $PSScriptRoot "configure_assistant.ps1") -Device $device
}
