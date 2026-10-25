param(
    [switch]$Deploy,
    [string]$TvIp = "192.168.76.209"
)

$ErrorActionPreference = "Stop"
& (Join-Path $PSScriptRoot "build_helper.ps1")
& (Join-Path $PSScriptRoot "rebuild_local.ps1")

if ($Deploy) {
    & (Join-Path $PSScriptRoot "install_tv.ps1") -TvIp $TvIp -ConfigureAssistant
}
