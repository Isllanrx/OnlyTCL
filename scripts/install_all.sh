#!/usr/bin/env bash
set -e

echo "========================================================"
echo "      OnlyTCL - Instalador Automático de APKs"
echo "========================================================"

ADB="${ADB:-adb}"

$ADB devices

echo "[1/5] Instalando ZeusBR (Twitch Nativo 1080p60 Realtek VSC)..."
$ADB install -r apks/zeusbr-tv.apk

echo "[2/5] Instalando Xbox Game Pass TV Custom (1080p60 Hardware Realtek + Brasil)..."
$ADB install -r apks/gamepass-tv-custom.apk
$ADB shell pm grant gamepass.fire.tv android.permission.WRITE_SECURE_SETTINGS

echo "[3/5] Instalando Claude TV (Assistente Conversacional por Voz na TV)..."
$ADB install -r apks/claude-tv.apk
$ADB shell pm grant com.anthropic.claude android.permission.RECORD_AUDIO
$ADB shell settings put secure enabled_accessibility_services com.anthropic.claude/com.anthropic.claude.tv.ClaudeTvAccessibilityService
$ADB shell settings put secure accessibility_enabled 1

echo "[4/5] Instalando tv-home (Launcher minimalista sem anúncios)..."
$ADB install -r apks/tv-home.apk

echo "[5/5] Instalando ZeusRemote (Controle T-Cast)..."
$ADB install -r apks/zeusremote.apk

echo "--------------------------------------------------------"
echo "Otimizando compilação AOT (dex2oat speed)..."
echo "--------------------------------------------------------"
$ADB shell cmd package compile -m speed -f com.isllantoso.zeusbr
$ADB shell cmd package compile -m speed -f gamepass.fire.tv
$ADB shell cmd package compile -m speed -f com.anthropic.claude
$ADB shell cmd package compile -m speed -f com.ansub.tvhome

echo "[SUCESSO] Instalação e otimização concluídas!"
