#!/usr/bin/env bash
ADB="${ADB:-adb} -s ${TV:-192.168.76.209:5555}"
PKG="${1:-gamepass.fire.tv}"
PID="$($ADB shell pidof $PKG | tr -d '')"
if [ -z "$PID" ]; then
  echo "Processo $PKG nao encontrado em execucao."
  exit 1
fi
echo "Sockets TCP ativos para $PKG (PID: $PID):"
$ADB shell "cat /proc/$PID/net/tcp"
