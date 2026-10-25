#!/usr/bin/env bash
ADB="${ADB:-adb} -s ${TV:-192.168.76.209:5555}"
echo "Verificando camadas do SurfaceFlinger e composicao de hardware..."
$ADB shell "dumpsys SurfaceFlinger" | grep -E "(Composition type|DEVICE|CLIENT|SurfaceView|gamepass|zeusbr)"
