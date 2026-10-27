#!/usr/bin/env bash
ADB="${ADB:-adb} -s ${TV:-${TV_IP:-192.168.1.100}:5555}"
PKG="${1:-gamepass.fire.tv}"
PID="$($ADB shell pidof $PKG | tr -d '')"
if [ -z "$PID" ]; then
  echo "Processo $PKG nao encontrado em execucao."
  exit 1
fi
echo "Sockets TCP ativos para $PKG (PID: $PID):"
$ADB shell "cat /proc/$PID/net/tcp"
