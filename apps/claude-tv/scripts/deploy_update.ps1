. "$PSScriptRoot\load_env.ps1"
if (-not $TvIp) { $TvIp = $env:TV_IP }
param(
    [string]$TvIp = ""
)

$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "install_tv.ps1") -TvIp $TvIp -ConfigureAssistant
