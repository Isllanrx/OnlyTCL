#!/usr/bin/env bash
ADB="${ADB:-adb} -s ${TV:-192.168.76.209:5555}"
echo "=== MEMORIA DISPONIVEL ==="
$ADB shell "cat /proc/meminfo | grep -E 'MemTotal|MemFree|MemAvailable|SwapTotal|SwapFree'"
echo "=== SERVICOS DE ACESSIBILIDADE ATIVOS ==="
$ADB shell "settings get secure enabled_accessibility_services"
echo "=== PROCESSOS NO TOPO (CPU) ==="
$ADB shell "top -n 1 -b -m 5"
