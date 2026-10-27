. "$PSScriptRoot\load_env.ps1"
if (-not $TvIp) { $TvIp = $env:TV_IP }
param(
    [switch]$Deploy,
    [string]$TvIp = ""
)

$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "build_helper.ps1")
& (Join-Path $PSScriptRoot "rebuild_local.ps1")

if ($Deploy) {
    & (Join-Path $PSScriptRoot "install_tv.ps1") -TvIp $TvIp -ConfigureAssistant
}
