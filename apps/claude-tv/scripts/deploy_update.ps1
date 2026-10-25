param(
    [string]$TvIp = "192.168.76.209"
)

$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "install_tv.ps1") -TvIp $TvIp -ConfigureAssistant
