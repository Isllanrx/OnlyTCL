param(
    [string]$Device = "192.168.76.209:5555",
    [int]$Seconds = 30
)

# Medição PASSIVA de quadros do Claude na TV durante uma fase escolhida pelo usuário
# (ex.: resposta falada no modo de voz). Zera os contadores do gfxinfo, espera o intervalo
# enquanto o usuário usa o app, e imprime o histograma. Não envia teclas nem altera áudio.
#
# Uso: abra o modo de voz na TV, rode este script, faça uma pergunta e aguarde o fim.

$ErrorActionPreference = "Continue"
$adb = "E:\Android\Sdk\platform-tools\adb.exe"
if (-not (Test-Path -LiteralPath $adb)) { $adb = "adb" }
$package = "com.anthropic.claude"

& $adb connect $Device | Out-Null
$state = (& $adb -s $Device get-state 2>$null | Out-String).Trim()
if ($state -ne "device") { throw "TV indisponível em ${Device}: $state" }

& $adb -s $Device shell dumpsys gfxinfo $package reset | Out-Null
$t0 = Get-Date
Write-Host "[gfxinfo] contadores zerados; medindo por $Seconds s... use o app agora." -ForegroundColor Cyan
Start-Sleep -Seconds $Seconds

$report = & $adb -s $Device shell dumpsys gfxinfo $package
$report | Select-String -Pattern "Total frames rendered|Janky frames|50th percentile|90th percentile|95th percentile|99th percentile|Number Missed Vsync|Number High input latency|Number Slow UI thread|Number Slow bitmap uploads|Number Slow issue draw commands|Number Frame deadline missed|gpu percentile" | ForEach-Object { $_.Line }

$cpu = & $adb -s $Device shell "top -b -n 1 -o PID,%CPU,RES,ARGS | grep -E 'anthropic|PID'"
Write-Host "`n[top]"
$cpu | ForEach-Object { Write-Host $_ }
Write-Host "`nJanela medida: $t0 -> $(Get-Date)" -ForegroundColor Green
