#!/usr/bin/env bash
set -e

echo "========================================================"
echo "      OnlyTCL - Script de Limpeza e Debloat da TV"
echo "========================================================"

ADB="${ADB:-adb}"

BLOAT=(
  com.tcl.bi
  com.tcl.logkit
  com.tcl.usercenter
  com.tcl.overseasappshow
  com.tcl.tv.tclhome_passive
  com.tcl.messagebox
  com.tcl.channelplus
  com.tcl.waterfall.overseas
  com.tcl.esticker
  com.tcl.smartalexa
  com.tcl.assistant
  com.tcl.browser
  com.tcl.gallery
  com.tcl.ui_mediaCenter
  com.tcl.ocean.instructions
  com.tcl.keyhelp
  com.tcl.hearaid
  com.tcl.factory.view
  com.android.messaging
  com.android.camera2
  org.chromium.webview_shell
  com.google.android.play.games
  com.google.android.videos
  com.google.android.marvin.talkback
  au.com.stan.and
  tv.wuaki.apptv
  com.amazon.amazonvideo.livingroom
  com.tcl.MultiScreenInteraction_TV
  com.tcl.miracast
  com.tcl.gamebar
  com.google.android.apps.tv.dreamx
)

for p in "${BLOAT[@]}"; do
  echo "Desativando $p..."
  $ADB shell pm disable-user --user 0 "$p" 2>/dev/null || true
done

echo "Ajustando animacoes para 0.5x..."
$ADB shell settings put global window_animation_scale 0.5
$ADB shell settings put global transition_animation_scale 0.5
$ADB shell settings put global animator_duration_scale 0.5

echo "Limpando caches do sistema..."
$ADB shell cmd package trim-caches 4096M

echo "[SUCESSO] TV TCL otimizada!"
