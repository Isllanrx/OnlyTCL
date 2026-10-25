@echo off
chcp 65001 >nul
echo ========================================================
echo       OnlyTCL - Script de Limpeza e Debloat da TV
echo ========================================================
echo.

set ADB=adb

echo Desativando 31 bloatwares e servicos de telemetria pesados da TCL...
set BLOAT=com.tcl.bi com.tcl.logkit com.tcl.usercenter com.tcl.overseasappshow com.tcl.tv.tclhome_passive com.tcl.messagebox com.tcl.channelplus com.tcl.waterfall.overseas com.tcl.esticker com.tcl.smartalexa com.tcl.assistant com.tcl.browser com.tcl.gallery com.tcl.ui_mediaCenter com.tcl.ocean.instructions com.tcl.keyhelp com.tcl.hearaid com.tcl.factory.view com.android.messaging com.android.camera2 org.chromium.webview_shell com.google.android.play.games com.google.android.videos com.google.android.marvin.talkback au.com.stan.and tv.wuaki.apptv com.amazon.amazonvideo.livingroom com.tcl.MultiScreenInteraction_TV com.tcl.miracast com.tcl.gamebar com.google.android.apps.tv.dreamx

for %%p in (%BLOAT%) do (
    echo Desativando %%p...
    %ADB% shell pm disable-user --user 0 %%p >nul 2>&1
)

echo.
echo Ajustando velocidade das animacoes para 0.5x (fluidez maxima)...
%ADB% shell settings put global window_animation_scale 0.5
%ADB% shell settings put global transition_animation_scale 0.5
%ADB% shell settings put global animator_duration_scale 0.5

echo.
echo Liberando memoria RAM e caches...
%ADB% shell cmd package trim-caches 4096M

echo.
echo [SUCESSO] TV TCL otimizada com sucesso!
pause
