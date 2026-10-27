param(
    [string]$TvIp = ""
)

. "$PSScriptRoot\load_env.ps1"
if (-not $TvIp) { $TvIp = $env:TV_IP }
$adb = $env:ADB_PATH

Write-Host "=== CONECTANDO AO ADB (${TvIp}) ===" -ForegroundColor Cyan
& $adb connect "${TvIp}:5555"

Write-Host "`n=== 1. INTERFACES E ROTEAMENTO ===" -ForegroundColor Yellow
& $adb -s "${TvIp}:5555" shell "ip route"
& $adb -s "${TvIp}:5555" shell "ip -s link"

Write-Host "`n=== 2. STATUS WI-FI / ETHERNET ===" -ForegroundColor Yellow
Write-Host "--- Ethernet ---"
& $adb -s "${TvIp}:5555" shell "dumpsys ethernet"
Write-Host "--- Wi-Fi Info ---"
& $adb -s "${TvIp}:5555" shell "dumpsys wifi | grep -E 'mWifiInfo|RSSI|Link speed|Frequency|mNetworkInfo|Frequency:' | head -n 30"

Write-Host "`n=== 3. DNS E PROPRIEDADES DE REDE ANDROID ===" -ForegroundColor Yellow
& $adb -s "${TvIp}:5555" shell "getprop | grep -E 'net\.dns|net\.tcp|net\.rmem|net\.wmem|dhcp\.'"

Write-Host "`n=== 4. PARÂMETROS DE KERNEL LINUX (SYSCTL TCP/IP) ===" -ForegroundColor Yellow
$sysctls = @(
    "net.ipv4.tcp_congestion_control",
    "net.ipv4.tcp_available_congestion_control",
    "net.ipv4.tcp_rmem",
    "net.ipv4.tcp_wmem",
    "net.core.rmem_max",
    "net.core.wmem_max",
    "net.core.rmem_default",
    "net.core.wmem_default",
    "net.ipv4.tcp_window_scaling",
    "net.ipv4.tcp_timestamps",
    "net.ipv4.tcp_sack",
    "net.ipv4.tcp_low_latency",
    "net.ipv4.tcp_fastopen",
    "net.ipv4.tcp_autocorking",
    "net.ipv4.tcp_notsent_lowat",
    "net.ipv4.ip_local_port_range"
)
foreach ($s in $sysctls) {
    $val = & $adb -s "${TvIp}:5555" shell "cat /proc/sys/$($s.Replace('.', '/')) 2>/dev/null"
    Write-Host "$s = $val"
}

Write-Host "`n=== 5. LATÊNCIA E JITTER (TESTE ICMP) ===" -ForegroundColor Yellow
Write-Host "--- Gateway Local (Roteador) ---"
$gw = & $adb -s "${TvIp}:5555" shell "ip route | grep default | awk '{print `$3}'"
Write-Host "Gateway: $gw"
if ($gw) {
    & $adb -s "${TvIp}:5555" shell "ping -c 5 -W 2 $gw"
}

Write-Host "`n--- DNS Primário (Google 8.8.8.8) ---"
& $adb -s "${TvIp}:5555" shell "ping -c 5 -W 2 8.8.8.8"

Write-Host "`n--- Microsoft / Xbox Cloud Gaming Edge (Brasil) ---"
& $adb -s "${TvIp}:5555" shell "ping -c 5 -W 2 play.xbox.com"
& $adb -s "${TvIp}:5555" shell "ping -c 5 -W 2 xboxlive.com"

Write-Host "`n=== 6. DECODIFICAÇÃO DE VÍDEO HARDWARE (CODECS PARA CLOUD GAMING) ===" -ForegroundColor Yellow
& $adb -s "${TvIp}:5555" shell "dumpsys media.player | grep -iE 'codec|omx|c2\.' | head -n 40"
& $adb -s "${TvIp}:5555" shell "cat /etc/media_codecs.xml | grep -iE 'avc|hevc|vp9|webrtc' | head -n 30"

Write-Host "`n=== 7. CONFIGURAÇÃO DO APP XBOX (WEBVIEW / WEBRTC) ===" -ForegroundColor Yellow
& $adb -s "${TvIp}:5555" shell "dumpsys activity p gamepass.fire.tv | grep -E 'ProcessRecord|oom|adj' | head -n 20"
