param(
    [string]$Device = "192.168.76.209:5555"
)

$ErrorActionPreference = "Stop"
$adb = "E:\Android\Sdk\platform-tools\adb.exe"
$role = "android.app.role.ASSISTANT"
$package = "com.anthropic.claude"

function Get-AssistantHolder {
    $state = @(& $adb -s $Device shell dumpsys role)
    if ($LASTEXITCODE -ne 0) { throw "Falha ao consultar dumpsys role" }

    $roleIndex = -1
    for ($i = 0; $i -lt $state.Count; $i++) {
        if ($state[$i] -match '^\s*name=android\.app\.role\.ASSISTANT\s*$') {
            $roleIndex = $i
            break
        }
    }
    if ($roleIndex -lt 0) { throw "Papel android.app.role.ASSISTANT nao encontrado" }

    for ($i = $roleIndex + 1; $i -lt $state.Count -and $state[$i] -notmatch '^\s*\}'; $i++) {
        if ($state[$i] -match '^\s*holders=(?<holders>.*)$') {
            return $Matches.holders.Trim()
        }
    }
    return ""
}

if (-not (Test-Path -LiteralPath $adb)) { throw "ADB não encontrado: $adb" }

$installed = & $adb -s $Device shell pm path $package
if ($LASTEXITCODE -ne 0 -or -not ($installed -match "package:")) {
    throw "Claude TV não está instalado no dispositivo $Device"
}

$previous = Get-AssistantHolder
if ($LASTEXITCODE -ne 0) { throw "Não foi possível consultar o assistente atual" }
if ($previous -match [regex]::Escape($package)) {
    Write-Output "Claude TV já possui o papel de assistente"
    exit 0
}

& $adb -s $Device shell cmd role add-role-holder --user 0 $role $package
if ($LASTEXITCODE -ne 0) { throw "Falha ao definir Claude TV como assistente; papel anterior: $previous" }

$current = Get-AssistantHolder
if ($LASTEXITCODE -ne 0 -or -not ($current -match [regex]::Escape($package))) {
    throw "Android não confirmou Claude TV como assistente; papel anterior: $previous"
}

Write-Output "Assistente anterior: $previous"
Write-Output "Assistente atual: $current"

# Manter o serviço de reconhecimento de fala apontando para o Katniss nativo (evita que o stub do Claude quebre o STT)
& $adb -s $Device shell "settings put secure voice_recognition_service com.google.android.katniss/com.google.android.apps.tvsearch.voice.recognition.KatnissRecognitionService"
& $adb -s $Device shell "cmd appops set com.anthropic.claude APP_AUTO_START allow"
& $adb -s $Device shell "cmd appops set com.anthropic.claude START_FOREGROUND allow"
Write-Output "Permissões de segundo plano e reconhecimento de voz configurados com sucesso."
