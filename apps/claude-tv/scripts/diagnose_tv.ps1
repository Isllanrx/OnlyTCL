. "$PSScriptRoot\load_env.ps1"
param(
    [string]$Device = $env:TV_DEVICE,
    [string]$OutDir = ""
)

# Diagnóstico PASSIVO do Claude TV na TCL. Só leitura: não abre app, não envia teclas,
# não altera volume, assistente, animações ou qualquer configuração.
# Gera um diretório com os dumps necessários para fechar as causas raiz de:
#   - botão do controle (papel ASSISTANT / assistant / voice_interaction_service)
#   - microfone (chave física do mic embutido, dispositivos de entrada, mixes de política
#     do Android TV Remote Service, clientes de gravação ativos)
#   - desempenho (AOT/dexopt, escalas de animação, gfxinfo, camadas do SurfaceFlinger)

$ErrorActionPreference = "Continue"
$adb = $env:ADB_PATH
if (-not (Test-Path -LiteralPath $adb)) { $adb = "adb" }
$package = "com.anthropic.claude"

if (-not $OutDir) {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutDir = Join-Path $env:TEMP "claude-tv-diagnose\$stamp"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

function Dump([string]$name, [string[]]$shellArgs) {
    $file = Join-Path $OutDir "$name.txt"
    Write-Host "[dump] $name" -ForegroundColor Cyan
    & $adb -s $Device shell @shellArgs 2>&1 | Out-File -LiteralPath $file -Encoding utf8
}

& $adb connect $Device | Out-Null
$state = (& $adb -s $Device get-state 2>$null | Out-String).Trim()
if ($state -ne "device") { throw "TV indisponível em ${Device}: $state" }

# 1. Identidade e configuração relevante do sistema
Dump "01_props" @("getprop")
Dump "02_animation_scales" @("settings", "get", "global", "animator_duration_scale; settings get global transition_animation_scale; settings get global window_animation_scale")
Dump "03_assistant_settings" @("settings", "get", "secure", "assistant; settings get secure voice_interaction_service; settings get secure enabled_accessibility_services; settings get secure accessibility_enabled")
Dump "04_role_assistant" @("dumpsys", "role")

# 2. Pacote: versão, assinatura, estado de compilação (dexopt)
Dump "05_package" @("dumpsys", "package", $package)

# 3. Áudio: dispositivos, mixes de política (AudioBridgeX do Android TV Remote Service), clientes ativos
Dump "06_audio" @("dumpsys", "audio")
Dump "07_audio_policy" @("dumpsys", "media.audio_policy")
Dump "08_audio_flinger" @("dumpsys", "media.audio_flinger")

# 4. Gráficos: camadas compostas (janela translúcida do overlay x opaca), HWC e frames do app
Dump "09_surfaceflinger_list" @("dumpsys", "SurfaceFlinger", "--list")
Dump "10_surfaceflinger" @("dumpsys", "SurfaceFlinger")
Dump "11_gfxinfo" @("dumpsys", "gfxinfo", $package)
Dump "12_activities" @("dumpsys", "activity", "activities")

# 5. Memória e CPU do processo (amostra única)
Dump "13_meminfo" @("dumpsys", "meminfo", $package)
Dump "14_cpuinfo" @("dumpsys", "cpuinfo")

# 6. Logcat filtrado para os três fluxos (buffer existente, sem limpar)
$tags = "VoiceIo:I AtvRemote.AudioBridgeX:D AtvRemote.AudioTrackWrapper:D AudioRecord:W PuremicGlobal:I Tcl_AudioPolicyManager:D ClaudeTV:I ClaudeTvA11y:I ActivityTaskManager:I BMS-BlockMonitorManagerService:D AndroidRuntime:E *:S"
Dump "15_logcat_filtrado" @("logcat", "-d", "-v", "threadtime", $tags)
Dump "16_logcat_bruto_tail" @("logcat", "-d", "-v", "threadtime", "-t", "4000")

# 7. Resumo rápido em tela
Write-Host "`n===== RESUMO =====" -ForegroundColor Green
Write-Host "Assistente (dumpsys role):"
Select-String -LiteralPath (Join-Path $OutDir "04_role_assistant.txt") -Pattern "name=android.app.role.ASSISTANT" -Context 0,1 | ForEach-Object { $_.Line; $_.Context.PostContext }
Write-Host "`nDexopt:"
Select-String -LiteralPath (Join-Path $OutDir "05_package.txt") -Pattern "Dexopt state" -Context 0,3 | ForEach-Object { $_.Line; $_.Context.PostContext }
Write-Host "`nEscalas de animação (animator/transition/window):"
Get-Content -LiteralPath (Join-Path $OutDir "02_animation_scales.txt")
Write-Host "`nMixes de política de áudio / remote submix:"
Select-String -LiteralPath (Join-Path $OutDir "07_audio_policy.txt") -Pattern "Policy Mix|remote_submix|REMOTE_SUBMIX|addr=" | Select-Object -First 20 | ForEach-Object { $_.Line }
Write-Host "`nDispositivos de entrada disponíveis:"
Select-String -LiteralPath (Join-Path $OutDir "07_audio_policy.txt") -Pattern "Available input devices" -Context 0,12 | ForEach-Object { $_.Line; $_.Context.PostContext }
Write-Host "`nEventos de voz no logcat (últimos 40):"
Get-Content -LiteralPath (Join-Path $OutDir "15_logcat_filtrado.txt") | Select-String -Pattern "VoiceIo|AudioBridgeX|AudioTrackWrapper|PuremicGlobal|dead IAudioRecord" | Select-Object -Last 40 | ForEach-Object { $_.Line }
Write-Host "`nArquivos em: $OutDir" -ForegroundColor Green
