#!/usr/bin/env bash
ADB="${ADB:-adb} -s ${TV:-${TV_IP:-192.168.1.100}:5555}"
echo "Verificando camadas do SurfaceFlinger e composicao de hardware..."
$ADB shell "dumpsys SurfaceFlinger" | grep -E "(Composition type|DEVICE|CLIENT|SurfaceView|gamepass|zeusbr)"
