#!/usr/bin/env python3
"""Aplica (de forma idempotente) os hooks do Claude TV no projeto descompilado pelo apktool.

Uso:
    python apply_tv_hooks.py <dir_descompilado> [--check]

Os patches são textuais, mínimos e verificáveis; cada um declara o trecho original
esperado e o trecho substituído. Com --check o script só valida o estado (0 = todos
aplicados, 2 = pendente, 1 = inconsistência).

Hooks cobertos:
  1. AssistantOverlayActivity.onCreate -> ClaudeTvHelper.onOverlayCreate(Activity)Z
     Configura a janela do overlay e mantém a Activity nativa do modo de voz.
  2. Composer principal da TV: remove o botão de anexos sem alterar a lógica de envio.
  3. Aviso textual de limite semanal: omite somente a faixa redundante em pt/en.
  4. MainActivity.onCreate/onKeyDown: valida os hooks de janela e controle remoto.
  5. Overlay: recursos de transição e seleção Buttery nas sessões de voz.
  6. Modo de voz: rota Software (VOICE_RECOGNITION) para o microfone do controle abrir.
  7. Visualizador de voz: shader sem ruído, precisão média e ~30 quadros/s (gargalo de GPU na Mali-G31).
  8. Áudio do modo de voz via OpenSL ES (AudioRecord sobrevive à troca de rota da ponte do controle).
  9. Captura só pelo mic da TV (fonte MIC) e AEC com ganho fixo +18 dB e supressão de ruído nível 2.
 10. Saída de voz sem trilha FAST (OpenSL performance NONE), contra underruns nos GCs do processo.
 11. Pre-roll da reprodução de voz em 400 ms e telemetria Datadog desligada (CPU disputada com a voz).
 12. Sem animações: escala de movimento Compose 0 no app e visualizador GL do modo de voz desligado.
"""
from __future__ import annotations

import sys
import re
from pathlib import Path

HELPER = "Lcom/anthropic/claude/tv/ClaudeTvHelper;"

OVERLAY_SMALI = Path("smali_classes3/com/anthropic/claude/mainactivity/AssistantOverlayActivity.smali")
MAIN_SMALI = Path("smali/com/anthropic/claude/mainactivity/MainActivity.smali")
BELL_SERVICE_SMALI = Path("smali_classes2/com/anthropic/claude/bell/BellModeService.smali")
# A ponte de voz do controle (com.google.android.tv.remote.service, AudioBridgeX) só entrega o áudio
# do controle a gravações com fonte VOICE_RECOGNITION (6). A rota "Platform" do modo de voz grava com
# VOICE_COMMUNICATION (7) e o microfone do controle nunca abre (DIAGNOSTICO_TV_2026-10-05.md, 1.1).
# Forçar a flag project_bell_android_software_aec_enabled escolhe a rota "Software": fonte 6 + AEC3.
SOFTWARE_AEC_ORIGINAL = (
    '    const-string v6, "project_bell_android_software_aec_enabled"\n\n'
    "    invoke-interface {v0, v6}, Lqqf;->l(Ljava/lang/String;)Z\n\n"
    "    move-result v0\n\n"
    "    :goto_8\n"
    "    if-nez v0, :cond_11\n"
)
SOFTWARE_AEC_PATCHED = (
    '    const-string v6, "project_bell_android_software_aec_enabled"\n\n'
    "    invoke-interface {v0, v6}, Lqqf;->l(Ljava/lang/String;)Z\n\n"
    "    move-result v0\n\n"
    "    :goto_8\n"
    "    const/4 v0, 0x1\n\n"
    "    if-nez v0, :cond_11\n"
)
# Fonte de captura (pek.i: 1 -> VOICE_RECOGNITION 6, usado em VoiceIo.start e setRoute). A ponte do controle
# só assume gravações com fonte 6 e entrega o áudio do controle por ~30 s; cada entrada/saída recria a gravação
# (dead IAudioRecord 14:01:51 e 14:02:21) e depois a captura cai no mic da TV. Medido em 2026-10-06: mic da TV
# (chave ligada) capta a fala a -46..-54 dBFS e ficou estável 12 min sem troca. Fonte 1 (MIC) = só o mic da TV.
CAPTURE_PRESET_SMALI = Path("smali_classes3/pek.smali")
CAPTURE_PRESET_ORIGINAL = "    :cond_2\n    const/4 p0, 0x6\n\n    return p0\n.end method"
CAPTURE_PRESET_PATCHED = "    :cond_2\n    const/4 p0, 0x1\n\n    return p0\n.end method"
# SoftwareAecParams(noiseSuppressionLevel, highPassFilter, mobileMode, adaptiveDigitalGain, fixedDigitalGainDb),
# lidos da configuração remota (s100; padrão NS -1 = desligado, ganho fixo 0 dB). Fala no mic da TV chega a
# -46..-54 dBFS com fundo a -62..-68: +18 dB leva a fala a ~-30 dBFS e NS nível 2 contém o fundo que sobe junto.
SOFTWARE_AEC_PARAMS_ORIGINAL = (
    "    move/from16 v26, v12\n\n"
    "    invoke-direct/range {v22 .. v27}, Ls5v;-><init>(IZZZF)V\n"
)
SOFTWARE_AEC_PARAMS_PATCHED = (
    "    move/from16 v26, v12\n\n"
    "    const/16 v23, 0x2\n\n"
    "    const/high16 v27, 0x41900000    # 18.0f\n\n"
    "    invoke-direct/range {v22 .. v27}, Ls5v;-><init>(IZZZF)V\n"
)
# Pre-roll da reprodução (NativeIoParams.playbackPreRollMs = max(pre_roll_ms remoto 0..1000, padrão 40, ...)).
# Trace 2026-10-06 15:16–15:19 (fala engasgando durante pesquisa web/escrita): app com 37 s de CPU em 31 s,
# threads DefaultDispatcher esperando na fila tanto quanto rodam (até 60 ms), GC a cada 2–3 s, swap-in de 14 MB;
# a voz chega atrasada ao VoiceIo e 40 ms de folga não cobrem. 400 ms absorvem essas esperas.
PREROLL_ORIGINAL = (
    "    invoke-static {v9, v13, v12}, Lwp4;->o(III)I\n\n"
    "    move-result v9\n\n"
    "    iget v12, v0, Ls100;->f:I\n"
)
PREROLL_PATCHED = (
    "    invoke-static {v9, v13, v12}, Lwp4;->o(III)I\n\n"
    "    move-result v9\n\n"
    "    const/16 v9, 0x190\n\n"
    "    iget v12, v0, Ls100;->f:I\n"
)
# Telemetria Datadog RUM (skb.b(): liga só com a flag remota mobile_datadog_rum_enabled). No mesmo trace as
# threads datadog-* somaram ~2,5 s de CPU em 31 s disputando os 4 núcleos com a voz. Retornar false é o caminho
# do app quando a flag vem desligada.
DATADOG_SMALI = Path("smali/skb.smali")
DATADOG_ORIGINAL = ".method public final b()Z\n    .locals 8\n\n    iget-object v0, p0, Lskb;->d:Lf11;\n"
DATADOG_PATCHED = (
    ".method public final b()Z\n    .locals 8\n\n    const/4 v0, 0x0\n\n    return v0\n\n"
    "    iget-object v0, p0, Lskb;->d:Lf11;\n"
)
# MotionDurationScale do Compose (wdl.i0: lê animator_duration_scale global). Trace 2026-10-06 15:31–15:38: fase
# "animation" da thread principal somou 9,4 s em 201 quadros (um quadro de 9,7 s) com a TV a 3,5–4,0 núcleos.
# Escala 0 só neste app: animações Compose vão direto ao estado final, sem mudar a configuração global da TV.
MOTION_SCALE_SMALI = Path("smali/wdl.smali")
MOTION_SCALE_ORIGINAL = ".method public final i0()F\n    .locals 12\n\n    iget-object v0, p0, Lwdl;->z:Lgkv;\n"
MOTION_SCALE_PATCHED = (
    ".method public final i0()F\n    .locals 12\n\n    const/4 v0, 0x0\n\n    return v0\n\n"
    "    iget-object v0, p0, Lwdl;->z:Lgkv;\n"
)
# Visualizador GL do modo de voz (g6f.run): ~0,9 s de CPU + GPU Mali por 30 s mesmo após patch_visualizer.
# run() retorna na entrada; g6f.a() só sinaliza e faz join(1000), então encerrar cedo é seguro.
VIZ_OFF_ORIGINAL = ".method public final run()V\n    .locals 18\n\n    move-object/from16 v0, p0\n"
VIZ_OFF_PATCHED = ".method public final run()V\n    .locals 18\n\n    return-void\n\n    move-object/from16 v0, p0\n"
# Oboe na criação do stream de saída (VA 0x241d2, `movs r5,#12` = PerformanceMode::LowLatency). O patch
# 0x7a832 só troca o hint SL: mPerformanceMode segue 12 e o Oboe/OpenSL fica com burst 192 × 2 = 8 ms (Ghidra
# G 0x8a49c/0x8a5e4). Com None (10): burst 960 (20 ms), capacidade 1920 (40 ms), 5× menos callbacks.
OBOE_OUT_MODE_ORIGINAL = bytes.fromhex("f0600c251892")  # ldrb.w ... ; movs r5,#12 ; str r2,[sp,#0x60]
OBOE_OUT_MODE_PATCHED = bytes.fromhex("f0600a251892")  # movs r5,#10
# FFT de 1024 pontos por pacote de TTS (sml.r → fml) para alimentar o visualizador, já desligado (g6f), no
# mesmo coroutine que chama VoiceIo.write. Com fml ausente o fluxo segue o caminho normal (`:cond_d`).
TTS_FFT_SMALI = Path("smali_classes2/sml.smali")
TTS_FFT_ORIGINAL = "    iget-object v2, v0, Lsml;->d:Lfml;\n\n    if-eqz v2, :cond_d\n"
TTS_FFT_PATCHED = "    iget-object v2, v0, Lsml;->d:Lfml;\n\n    goto :cond_d\n"
# Poll de 10 ms (l8j) que copia o espectro para o visualizador; 40 ms basta para o gatilho do 1º quadro.
VIZ_POLL_SMALI = Path("smali_classes3/l8j.smali")
VIZ_POLL_ORIGINAL = "    const-wide/16 v9, 0xa\n\n    invoke-static {v9, v10, v5}, Lnn3;->K(JLa4a;)Ljava/lang/Object;\n"
VIZ_POLL_PATCHED = "    const-wide/16 v9, 0x28\n\n    invoke-static {v9, v10, v5}, Lnn3;->K(JLa4a;)Ljava/lang/Object;\n"
# Pré-aquecimento do WebView (ovb case 4: provider + startUpWebView/getDefaultUserAgent), ~5,8 s de CPU na
# janela de abertura (PERF 2026-10-06 §4) disputando com a 1ª interação de voz. O desvio vai ao ponto que posta
# a conclusão (n0 case 13), então quem aguarda o aquecimento não trava; o 1º uso real do WebView paga a carga.
WEBVIEW_WARMUP_SMALI = Path("smali/ovb.smali")
WEBVIEW_WARMUP_ORIGINAL = (
    "    check-cast p0, Landroid/content/Context;\n\n    invoke-static {}, Le4o;->L()Ljava/lang/ClassLoader;\n"
)
WEBVIEW_WARMUP_PATCHED = (
    "    check-cast p0, Landroid/content/Context;\n\n    goto :cond_15\n\n"
    "    invoke-static {}, Le4o;->L()Ljava/lang/ClassLoader;\n"
)
# start_in_session (s100.j): com false, BellModeService.g roda VoiceIo.nativeStart síncrono na thread principal
# (~1 s, PERF 2026-10-06 §3); com true o start ocorre em Dispatchers.IO (h83 → uzz.a → nnl.d), caminho do app.
NATIVE_START_ORIGINAL = "    :try_start_3\n    iget-boolean v0, v0, Ls100;->j:Z\n    :try_end_3\n"
NATIVE_START_PATCHED = "    :try_start_3\n    const/4 v0, 0x1\n    :try_end_3\n"
# Fase 2a (ADR-012): o helper guarda a instância do BellModeService para o painel de voz mínimo ler a sessão.
BELL_CREATE_ORIGINAL = "    invoke-super {p0}, Landroid/app/Service;->onCreate()V\n\n    const/4 v0, 0x0\n"
BELL_CREATE_PATCHED = (
    "    invoke-super {p0}, Landroid/app/Service;->onCreate()V\n\n"
    f"    invoke-static {{p0}}, {HELPER}->onBellCreate(Landroid/app/Service;)V\n\n"
    "    const/4 v0, 0x0\n"
)
BELL_DESTROY_ORIGINAL = ".method public final onDestroy()V\n    .locals 2\n\n    const/4 v0, 0x0\n"
BELL_DESTROY_PATCHED = (
    ".method public final onDestroy()V\n    .locals 2\n\n"
    f"    invoke-static {{p0}}, {HELPER}->onBellDestroy(Landroid/app/Service;)V\n\n"
    "    const/4 v0, 0x0\n"
)
# Transcrição em REVEAL em vez de KARAOKE (w83.L0): o karaokê (i4s.q) acorda a cada 16 ms e reconstrói e
# reparseia o texto inteiro a cada palavra; o painel mínimo mostra o texto sem pacing.
TEXT_PACING_SMALI = Path("smali_classes2/w83.smali")
TEXT_PACING_ORIGINAL = "    :cond_4\n    sget-object v0, Lw100;->x:Lw100;\n"
TEXT_PACING_PATCHED = "    :cond_4\n    sget-object v0, Lw100;->y:Lw100;\n"
# Suavizador de streaming do chat (vyv, flag android_chat_stream_smoothing): tick ≥ 16 ms copiando o texto de
# cada bloco. Sem ele o texto sai por chunk de rede, caminho do app quando a flag está ausente.
STREAM_SMOOTHING_SMALI = Path("smali_classes3/gv1.smali")
STREAM_SMOOTHING_ORIGINAL = "    check-cast v5, Lcyv;\n\n    if-eqz v5, :cond_4\n"
STREAM_SMOOTHING_PATCHED = "    check-cast v5, Lcyv;\n\n    goto :cond_4\n"
# Visualizador do modo de voz (AudioVisualizerGLThread, classes g6f/t42): shader de ruído com 4 random()
# baseados em sin() em highp por pixel, num laço de ~60 quadros/s fora do vsync. Medido (PERF_CLAUDE_2026-10-06):
# eglSwapBuffers do visualizador 194 ms/quadro em tela cheia e 83 ms no overlay; o RenderThread do app
# espera a GPU junto (quadros de 380–670 ms).
VIZ_SHADER_SMALI = Path("smali_classes2/t42.smali")
VIZ_SHADER_EDITS = (
    ("#define NOISE_ENABLED 1\\n", "#define NOISE_ENABLED 0\\n"),
    ("precision highp float;", "precision mediump float;"),
)
VIZ_THREAD_SMALI = Path("smali_classes2/g6f.smali")
VIZ_SLEEP_ORIGINAL = "    const-wide/16 v8, 0x10\n\n    invoke-static {v8, v9}, Ljava/lang/Thread;->sleep(J)V\n"
VIZ_SLEEP_PATCHED = "    const-wide/16 v8, 0x21\n\n    invoke-static {v8, v9}, Ljava/lang/Thread;->sleep(J)V\n"
# O Oboe embutido em libwebrtc_apm.so carrega o AAudio por dlopen("libaaudio.so"). No Android 11 um stream
# AAudio é desconectado a cada troca de rota; a ponte do controle troca a rota a cada start/stop do áudio BLE
# e o app entra em ciclo ErrorDisconnected/reabertura. Sem o AAudio, o Oboe usa OpenSL ES (libOpenSLES.so já
# é NEEDED), cuja captura usa AudioRecord e se recupera da troca de rota sem desconectar (restoreRecord_l).
APM_LIB = Path("lib/armeabi-v7a/libwebrtc_apm.so")
AAUDIO_DLOPEN_ORIGINAL = b"\x00libaaudio.so\x00AAudioStreamBuilder_"
AAUDIO_DLOPEN_PATCHED = b"\x00libaaudiq.so\x00AAudioStreamBuilder_"
# Oboe AudioStreamOpenSLES::configurePerformanceMode (VA 0x7a82a): LowLatency (0xc) pede ao OpenSL a trilha
# FAST, que na TV ficou com fila de 2×192 quadros (8 ms) e somou 640 e 256 underruns por sessão, concentrados
# nos GCs grandes do início (até 1,9 s). O `bne` vira `b`: só PowerSaving (0xb) mantém o modo; o resto pede
# SL_ANDROID_PERFORMANCE_NONE (trilha normal do mixer, buffer de dezenas de ms). A entrada já abria com None.
OUTPUT_PERF_ORIGINAL = bytes.fromhex("0c2808d1606d0130")  # cmp r0,#0xc; bne; ldr r0,[r4,#0x54]; adds r0,#1
OUTPUT_PERF_PATCHED = bytes.fromhex("0c2808e0606d0130")  # cmp r0,#0xc; b;   ...
SESSION_SMALI = Path("smali_classes2/s37.smali")
MANIFEST_XML = Path("AndroidManifest.xml")
CHAT_COMPOSER_SMALI = Path("smali_classes3/rx.smali")
NOTICE_SMALI = Path("smali_classes4/br10.smali")
BUTTON_SMALI = Path("smali/z4x.smali")
CHAT_INPUT_BAR_SMALI = Path("smali_classes4/w7h.smali")
CHAT_INPUT_ICON_SMALI = Path("smali_classes3/hc9.smali")
CHAT_INPUT_VU5_SMALI = Path("smali_classes3/vu5.smali")
CHAT_INPUT_VU5_ORIGINAL = (
    "    invoke-virtual {v14, v2, v6}, Lr6f;->Y(IZ)Z\n\n"
    "    move-result v1\n\n"
    "    if-eqz v1, :cond_77\n\n"
    "    const v1, 0x7f100641\n"
)
CHAT_INPUT_VU5_PATCHED = (
    "    invoke-virtual {v14, v2, v6}, Lr6f;->Y(IZ)Z\n\n"
    "    move-result v1\n\n"
    "    goto :cond_77\n\n"
    "    const v1, 0x7f100641\n"
)
CHAT_INPUT_ADD_ORIGINAL = (
    "    invoke-virtual {p1, v2, v1}, Lr6f;->Y(IZ)Z\n\n"
    "    move-result v1\n\n"
    "    if-eqz v1, :cond_5\n\n"
    "    sget-object v1, Ler10;->b:Lab9;\n"
)
CHAT_INPUT_ADD_PATCHED = (
    "    invoke-virtual {p1, v2, v1}, Lr6f;->Y(IZ)Z\n\n"
    "    move-result v1\n\n"
    "    goto :cond_5\n\n"
    "    sget-object v1, Ler10;->b:Lab9;\n"
)
CHAT_INPUT_NULL_P6_ORIGINAL = (
    ".method public static final b(ZZZLp9h;ZLe27;Lt4f;Lt4f;Lt4f;Lt4f;Lt4f;Lt4f;Lwbl;ZZZZLvzz;Lsi9;Lj5f;ZZLt4f;Lte9;IIII)V\n"
    "    .locals 65\n\n"
    "    move/from16 v1, p0\n"
)
CHAT_INPUT_NULL_P6_PATCHED = (
    ".method public static final b(ZZZLp9h;ZLe27;Lt4f;Lt4f;Lt4f;Lt4f;Lt4f;Lt4f;Lwbl;ZZZZLvzz;Lsi9;Lj5f;ZZLt4f;Lte9;IIII)V\n"
    "    .locals 65\n\n"
    "    const/4 p6, 0x0\n\n"
    "    move/from16 v1, p0\n"
)
CHAT_INPUT_ICON_ORIGINAL = (
    "    invoke-virtual {v8, v1, v14}, Lr6f;->Y(IZ)Z\n\n"
    "    move-result v0\n\n"
    "    if-eqz v0, :cond_2e\n"
)
CHAT_INPUT_ICON_PATCHED = (
    "    invoke-virtual {v8, v1, v14}, Lr6f;->Y(IZ)Z\n\n"
    "    move-result v0\n\n"
    "    goto :cond_2e\n"
)
BUTTON_ENTRY_ORIGINAL = (
    "    const v4, 0x1af5d886\n\n"
    "    invoke-virtual {v12, v4}, Lr6f;->l0(I)Lr6f;\n\n"
    "    and-int/lit8 v4, v2, 0x6\n"
)
BUTTON_ENTRY_PATCHED = (
    "    const v4, 0x1af5d886\n\n"
    "    invoke-virtual {v12, v4}, Lr6f;->l0(I)Lr6f;\n\n"
    f"    invoke-static {{v8}}, {HELPER}->shouldSuppressIconButton(Ljava/lang/String;)Z\n\n"
    "    move-result v4\n\n"
    "    if-eqz v4, :claude_tv_suppress_button\n\n"
    "    and-int/lit8 v4, v2, 0x6\n"
)
BUTTON_EXIT_ORIGINAL = (
    "    iput-object v0, v13, Lqhq;->d:Lj5f;\n\n"
    "    :cond_2c\n"
    "    return-void\n"
    ".end method"
)
BUTTON_EXIT_PATCHED = (
    "    iput-object v0, v13, Lqhq;->d:Lj5f;\n\n"
    "    :cond_2c\n"
    "    return-void\n\n"
    "    :claude_tv_suppress_button\n"
    "    invoke-virtual {v12}, Lr6f;->x()Lqhq;\n\n"
    "    return-void\n"
    ".end method"
)
OVERLAY_RESOURCES = (
    Path("anim/claude_tv_overlay_enter.xml"),
    Path("anim/claude_tv_overlay_exit.xml"),
    Path("values/claude_tv_overlay_animation.xml"),
)
VOICE_SELECTION_SITES = {
    Path("smali_classes2/com/anthropic/claude/bell/BellModeService.smali"): 1,
    Path("smali_classes2/w83.smali"): 2,
    Path("smali_classes2/y83.smali"): 1,
    Path("smali_classes2/o83.smali"): 1,
}
OVERLAY_DESTROY_HOOK = (
    ".method protected onDestroy()V\n"
    "    .locals 0\n\n"
    f"    invoke-static {{p0}}, {HELPER}->onOverlayDestroy(Landroid/app/Activity;)V\n\n"
    "    invoke-super {p0}, Lia9;->onDestroy()V\n\n"
    "    return-void\n"
    ".end method\n"
)

OVERLAY_OLD = (
    "    invoke-super {p0, p1}, Lia9;->onCreate(Landroid/os/Bundle;)V\n"
    "\n"
    f"    invoke-static {{p0}}, {HELPER}->onOverlayCreate(Landroid/app/Activity;)V\n"
    "\n"
    "    const/4 v0, 0x0\n"
)

OVERLAY_NEW = (
    "    invoke-super {p0, p1}, Lia9;->onCreate(Landroid/os/Bundle;)V\n"
    "\n"
    f"    invoke-static {{p0}}, {HELPER}->onOverlayCreate(Landroid/app/Activity;)Z\n"
    "\n"
    "    move-result v0\n"
    "\n"
    "    if-eqz v0, :claude_tv_overlay_continue\n"
    "\n"
    "    return-void\n"
    "\n"
    "    :claude_tv_overlay_continue\n"
    "    const/4 v0, 0x0\n"
)

MAIN_CREATE_HOOK = f"    invoke-static {{p0}}, {HELPER}->onActivityCreate(Landroid/app/Activity;)V\n"
MAIN_KEY_HOOK = (
    f"    invoke-static {{p0, p1, p2}}, {HELPER}->handleKeyDown(Landroid/app/Activity;ILandroid/view/KeyEvent;)Z\n"
)
ATTACHMENT_BRANCH = "    if-eqz v1, :cond_5e\n"
ATTACHMENT_END = "    :cond_5e\n"
NOTICE_OLD_FILTER = (
    "    move-result v1\n\n"
    "    move-object/from16 v13, p0\n\n"
    "    const-string v14, \"Limite semanal atingido\"\n\n"
    "    invoke-virtual {v13, v14}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z\n\n"
    "    move-result v15\n\n"
    "    if-nez v15, :claude_tv_suppress_weekly_limit_notice\n\n"
    "    const-string v14, \"weekly limit reached\"\n\n"
    "    invoke-virtual {v13, v14}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z\n\n"
    "    move-result v15\n\n"
    "    if-eqz v15, :claude_tv_keep_notice\n\n"
    "    :claude_tv_suppress_weekly_limit_notice\n\n"
    "    const/4 v1, 0x0\n\n"
    "    :claude_tv_keep_notice\n\n"
    "    if-eqz v1, :cond_12\n"
)
NOTICE_RENDER_ANCHOR = (
    "    invoke-static/range {v8 .. v20}, Lqew;->a(Lwbl;Lfcu;JJFFLjm3;Lj5f;Lte9;II)V\n\n"
    "    move-object v2, v6\n"
)
NOTICE_RENDER_FILTER = (
    "    move-object/from16 v14, p0\n\n"
    "    const-string v15, \"Limite semanal atingido\"\n\n"
    "    invoke-virtual {v14, v15}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z\n\n"
    "    move-result v15\n\n"
    "    if-nez v15, :claude_tv_suppress_weekly_limit_notice\n\n"
    "    const-string v15, \"weekly limit reached\"\n\n"
    "    invoke-virtual {v14, v15}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z\n\n"
    "    move-result v15\n\n"
    "    if-eqz v15, :claude_tv_keep_notice\n\n"
    "    :claude_tv_suppress_weekly_limit_notice\n\n"
    "    goto :claude_tv_skip_weekly_limit_notice\n\n"
    "    :claude_tv_keep_notice\n\n"
    "    const/4 v14, 0x0\n\n"
    "    const/high16 v15, 0x40000000    # 2.0f\n\n"
    "    invoke-static/range {v8 .. v20}, Lqew;->a(Lwbl;Lfcu;JJFFLjm3;Lj5f;Lte9;II)V\n\n"
    "    :claude_tv_skip_weekly_limit_notice\n\n"
    "    move-object v2, v6\n"
)
NOTICE_BROKEN_FILTER = (
    "    move-object/from16 v14, p0\n\n"
    "    const-string v15, \"Limite semanal atingido\"\n\n"
    "    invoke-virtual {v14, v15}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z\n\n"
    "    move-result v15\n\n"
    "    if-nez v15, :claude_tv_suppress_weekly_limit_notice\n\n"
    "    const-string v15, \"weekly limit reached\"\n\n"
    "    invoke-virtual {v14, v15}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z\n\n"
    "    move-result v15\n\n"
    "    if-eqz v15, :claude_tv_keep_notice\n\n"
    "    :claude_tv_suppress_weekly_limit_notice\n\n"
    "    goto :claude_tv_skip_weekly_limit_notice\n\n"
    "    :claude_tv_keep_notice\n\n"
    "    const/4 v14, 0x0\n\n"
    "    invoke-static/range {v8 .. v20}, Lqew;->a(Lwbl;Lfcu;JJFFLjm3;Lj5f;Lte9;II)V\n\n"
    "    :claude_tv_skip_weekly_limit_notice\n\n"
    "    move-object v2, v6\n"
)


def patch_overlay(root: Path, check_only: bool) -> int:
    path = root / OVERLAY_SMALI
    text = path.read_text(encoding="utf-8")
    if OVERLAY_NEW in text:
        print(f"[ok] overlay hook já aplicado: {OVERLAY_SMALI}")
        return 0
    if OVERLAY_OLD not in text:
        print(f"[erro] trecho original do overlay não encontrado em {OVERLAY_SMALI}")
        return 1
    if check_only:
        print(f"[pendente] overlay hook não aplicado: {OVERLAY_SMALI}")
        return 2
    path.write_text(text.replace(OVERLAY_OLD, OVERLAY_NEW, 1), encoding="utf-8")
    print(f"[aplicado] overlay hook: {OVERLAY_SMALI}")
    return 0


def verify_main(root: Path) -> int:
    path = root / MAIN_SMALI
    text = path.read_text(encoding="utf-8")
    rc = 0
    for label, hook in (("onCreate", MAIN_CREATE_HOOK), ("onKeyDown", MAIN_KEY_HOOK)):
        if hook in text:
            print(f"[ok] MainActivity.{label} hook presente")
        else:
            print(f"[erro] MainActivity.{label} hook ausente em {MAIN_SMALI}")
            rc = 1
    return rc


def patch_overlay_lifecycle(root: Path, check_only: bool) -> int:
    path = root / OVERLAY_SMALI
    text = path.read_text(encoding="utf-8")
    if OVERLAY_DESTROY_HOOK not in text:
        print("[ok] seleção de voz usa ciclo de vida via referência fraca")
        return 0
    if check_only:
        print("[pendente] remover hook de destruição redundante do overlay")
        return 2
    path.write_text(text.replace(OVERLAY_DESTROY_HOOK, "", 1), encoding="utf-8")
    print("[aplicado] removido hook redundante; referência fraca expira com a Activity")
    return 0


def patch_overlay_resources(root: Path, check_only: bool) -> int:
    source = Path(__file__).resolve().parent.parent / "res"
    rc = 0
    for resource in OVERLAY_RESOURCES:
        expected = (source / resource).read_text(encoding="utf-8")
        target = root / "res" / resource
        if target.is_file() and target.read_text(encoding="utf-8") == expected:
            continue
        if check_only:
            print(f"[pendente] recurso de animação: {resource}")
            rc = 2
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(expected, encoding="utf-8")
        print(f"[aplicado] recurso de animação: {resource}")
    if rc == 0:
        print("[ok] recursos de transição do overlay presentes")
    return rc


def patch_overlay_voice(root: Path, check_only: bool) -> int:
    pattern = re.compile(
        r"(    invoke-static(?:/range)? \{[^\n]+\}, Li000;->a\(Ljava/lang/String;\)Ljava/lang/String;\n"
        r"\n    move-result-object (v\d+)\n)"
    )
    rc = 0
    for relative, expected_count in VOICE_SELECTION_SITES.items():
        path = root / relative
        text = path.read_text(encoding="utf-8")
        matches = list(pattern.finditer(text))
        if len(matches) != expected_count:
            print(f"[erro] seleção de voz mudou em {relative}: {len(matches)}/{expected_count}")
            rc = 1
            continue
        edits = []
        for match in matches:
            register = match.group(2)
            hook = (
                f"\n    invoke-static/range {{{register} .. {register}}}, "
                f"{HELPER}->resolveOverlayVoice(Ljava/lang/String;)Ljava/lang/String;\n\n"
                f"    move-result-object {register}\n"
            )
            if text.startswith(hook, match.end()):
                continue
            edits.append((match.end(), hook))
        if not edits:
            print(f"[ok] voz Buttery do overlay: {relative}")
        elif check_only:
            print(f"[pendente] seleção de voz do overlay: {relative}")
            if rc == 0:
                rc = 2
        else:
            for offset, hook in reversed(edits):
                text = text[:offset] + hook + text[offset:]
            path.write_text(text, encoding="utf-8")
            print(f"[aplicado] voz Buttery do overlay: {relative}")
    return rc


def patch_chat_attachment_button(root: Path, check_only: bool) -> int:
    path = root / CHAT_COMPOSER_SMALI
    text = path.read_text(encoding="utf-8")
    applied = "    goto :cond_5e\n\n" + ATTACHMENT_END
    if applied in text:
        if "    :goto_34\n" not in text:
            text = text.replace("    :goto_35\n", "    :goto_34\n\n    :goto_35\n", 1)
            path.write_text(text, encoding="utf-8")
        print(f"[ok] botão de anexos removido do chat da TV: {CHAT_COMPOSER_SMALI}")
        return 0
    if text.count(ATTACHMENT_BRANCH) != 1:
        print(f"[erro] ponto único do botão de anexos não encontrado em {CHAT_COMPOSER_SMALI}")
        return 1
    start = text.index(ATTACHMENT_BRANCH)
    end = text.find(ATTACHMENT_END, start + len(ATTACHMENT_BRANCH))
    if end < 0:
        print(f"[erro] fim do bloco do botão de anexos não encontrado em {CHAT_COMPOSER_SMALI}")
        return 1
    if check_only:
        print(f"[pendente] botão de anexos ainda habilitado em {CHAT_COMPOSER_SMALI}")
        return 2
    patched = text[:start] + "    goto :cond_5e\n\n" + text[end:]
    if "    :goto_34\n" not in patched:
        patched = patched.replace("    :goto_35\n", "    :goto_34\n\n    :goto_35\n", 1)
    path.write_text(patched, encoding="utf-8")
    print(f"[aplicado] botão de anexos removido do chat da TV: {CHAT_COMPOSER_SMALI}")
    return 0


def patch_weekly_limit_notice(root: Path, check_only: bool) -> int:
    path = root / NOTICE_SMALI
    text = path.read_text(encoding="utf-8")
    method_start = text.find(".method public static final f(Ljava/lang/String;Ltr0;")
    method_end = text.find(".end method", method_start)
    if method_start < 0 or method_end < 0:
        print(f"[erro] composable de aviso não encontrado em {NOTICE_SMALI}")
        return 1
    method = text[method_start:method_end]
    if NOTICE_RENDER_FILTER in method:
        print(f"[ok] aviso de limite semanal filtrado: {NOTICE_SMALI}")
        return 0
    if NOTICE_BROKEN_FILTER in method:
        if check_only:
            print(f"[pendente] corrigir registrador v15 em {NOTICE_SMALI}")
            return 2
        method = method.replace(NOTICE_BROKEN_FILTER, NOTICE_RENDER_FILTER, 1)
        path.write_text(text[:method_start] + method + text[method_end:], encoding="utf-8")
        print(f"[aplicado] corrigido registrador v15 no aviso de limite semanal: {NOTICE_SMALI}")
        return 0
    if NOTICE_OLD_FILTER in method:
        method = method.replace(NOTICE_OLD_FILTER, "    move-result v1\n\n    if-eqz v1, :cond_12\n", 1)
    if method.count(NOTICE_RENDER_ANCHOR) != 1:
        print(f"[erro] ponto único de renderização do aviso não encontrado em {NOTICE_SMALI}")
        return 1
    if check_only:
        print(f"[pendente] aviso de limite semanal ainda visível em {NOTICE_SMALI}")
        return 2
    patched_method = method.replace(NOTICE_RENDER_ANCHOR, NOTICE_RENDER_FILTER, 1)
    path.write_text(text[:method_start] + patched_method + text[method_end:], encoding="utf-8")
    print(f"[aplicado] aviso de limite semanal filtrado: {NOTICE_SMALI}")
    return 0


def patch_attachment_icon_suppression(root: Path, check_only: bool) -> int:
    path = root / BUTTON_SMALI
    text = path.read_text(encoding="utf-8")
    if BUTTON_ENTRY_PATCHED in text and BUTTON_EXIT_PATCHED in text:
        print(f"[ok] supressão global de botão de anexos já aplicada: {BUTTON_SMALI}")
        return 0
    if BUTTON_ENTRY_ORIGINAL not in text or BUTTON_EXIT_ORIGINAL not in text:
        print(f"[erro] trecho original de z4x.N não encontrado em {BUTTON_SMALI}")
        return 1
    if check_only:
        print(f"[pendente] supressão global de botão de anexos não aplicada: {BUTTON_SMALI}")
        return 2
    text = text.replace(BUTTON_ENTRY_ORIGINAL, BUTTON_ENTRY_PATCHED, 1)
    text = text.replace(BUTTON_EXIT_ORIGINAL, BUTTON_EXIT_PATCHED, 1)
    path.write_text(text, encoding="utf-8")
    print(f"[aplicado] supressão global de botão de anexos: {BUTTON_SMALI}")
    return 0


def patch_chat_input_add_button(root: Path, check_only: bool) -> int:
    path_bar = root / CHAT_INPUT_BAR_SMALI
    path_icon = root / CHAT_INPUT_ICON_SMALI
    path_vu5 = root / CHAT_INPUT_VU5_SMALI
    rc = 0

    if path_vu5.exists():
        text_vu5 = path_vu5.read_text(encoding="utf-8")
        if CHAT_INPUT_VU5_PATCHED not in text_vu5 and CHAT_INPUT_VU5_ORIGINAL in text_vu5:
            if check_only:
                return 2
            text_vu5 = text_vu5.replace(CHAT_INPUT_VU5_ORIGINAL, CHAT_INPUT_VU5_PATCHED, 1)
            path_vu5.write_text(text_vu5, encoding="utf-8")
            print(f"[aplicado] composable do botão (+) suprimido em: {CHAT_INPUT_VU5_SMALI}")
        else:
            print(f"[ok] composable do botão (+) já suprimido: {CHAT_INPUT_VU5_SMALI}")

    if path_bar.exists():
        text_bar = path_bar.read_text(encoding="utf-8")
        dirty = False
        if CHAT_INPUT_ADD_PATCHED not in text_bar and CHAT_INPUT_ADD_ORIGINAL in text_bar:
            if check_only:
                return 2
            text_bar = text_bar.replace(CHAT_INPUT_ADD_ORIGINAL, CHAT_INPUT_ADD_PATCHED, 1)
            dirty = True
        if CHAT_INPUT_NULL_P6_PATCHED not in text_bar and CHAT_INPUT_NULL_P6_ORIGINAL in text_bar:
            if check_only:
                return 2
            text_bar = text_bar.replace(CHAT_INPUT_NULL_P6_ORIGINAL, CHAT_INPUT_NULL_P6_PATCHED, 1)
            dirty = True
        if dirty:
            path_bar.write_text(text_bar, encoding="utf-8")
            print(f"[aplicado] botão (+) removido da barra de chat: {CHAT_INPUT_BAR_SMALI}")
        else:
            print(f"[ok] botão (+) da barra de chat já removido: {CHAT_INPUT_BAR_SMALI}")

    if path_icon.exists():
        text_icon = path_icon.read_text(encoding="utf-8")
        if CHAT_INPUT_ICON_PATCHED not in text_icon and CHAT_INPUT_ICON_ORIGINAL in text_icon:
            if check_only:
                return 2
            text_icon = text_icon.replace(CHAT_INPUT_ICON_ORIGINAL, CHAT_INPUT_ICON_PATCHED, 1)
            path_icon.write_text(text_icon, encoding="utf-8")
            print(f"[aplicado] ícone do botão (+) suprimido em: {CHAT_INPUT_ICON_SMALI}")
        else:
            print(f"[ok] ícone do botão (+) já suprimido: {CHAT_INPUT_ICON_SMALI}")

    return rc


def patch_software_aec(root: Path, check_only: bool) -> int:
    path = root / BELL_SERVICE_SMALI
    text = path.read_text(encoding="utf-8")
    if SOFTWARE_AEC_PATCHED in text:
        print(f"[ok] modo de voz na rota Software (VOICE_RECOGNITION): {BELL_SERVICE_SMALI}")
        return 0
    if SOFTWARE_AEC_ORIGINAL not in text:
        print(f"[erro] leitura de project_bell_android_software_aec_enabled mudou em {BELL_SERVICE_SMALI}")
        return 1
    if check_only:
        print(f"[pendente] rota Software do modo de voz: {BELL_SERVICE_SMALI}")
        return 2
    path.write_text(text.replace(SOFTWARE_AEC_ORIGINAL, SOFTWARE_AEC_PATCHED, 1), encoding="utf-8")
    print(f"[aplicado] modo de voz na rota Software (VOICE_RECOGNITION): {BELL_SERVICE_SMALI}")
    return 0


def patch_capture_builtin_mic(root: Path, check_only: bool) -> int:
    path = root / CAPTURE_PRESET_SMALI
    text = path.read_text(encoding="utf-8")
    if CAPTURE_PRESET_PATCHED in text:
        print(f"[ok] captura só pelo mic da TV (fonte MIC): {CAPTURE_PRESET_SMALI}")
        return 0
    if text.count(CAPTURE_PRESET_ORIGINAL) != 1:
        print(f"[erro] mapeamento da fonte de captura mudou em {CAPTURE_PRESET_SMALI}")
        return 1
    if check_only:
        print(f"[pendente] captura só pelo mic da TV: {CAPTURE_PRESET_SMALI}")
        return 2
    path.write_text(text.replace(CAPTURE_PRESET_ORIGINAL, CAPTURE_PRESET_PATCHED, 1), encoding="utf-8")
    print(f"[aplicado] captura só pelo mic da TV (fonte MIC): {CAPTURE_PRESET_SMALI}")
    return 0


def patch_software_aec_params(root: Path, check_only: bool) -> int:
    path = root / BELL_SERVICE_SMALI
    text = path.read_text(encoding="utf-8")
    if SOFTWARE_AEC_PARAMS_PATCHED in text:
        print(f"[ok] AEC: ganho fixo +18 dB e supressão de ruído nível 2: {BELL_SERVICE_SMALI}")
        return 0
    if text.count(SOFTWARE_AEC_PARAMS_ORIGINAL) != 1:
        print(f"[erro] construção de SoftwareAecParams mudou em {BELL_SERVICE_SMALI}")
        return 1
    if check_only:
        print(f"[pendente] AEC: ganho e supressão de ruído: {BELL_SERVICE_SMALI}")
        return 2
    path.write_text(text.replace(SOFTWARE_AEC_PARAMS_ORIGINAL, SOFTWARE_AEC_PARAMS_PATCHED, 1), encoding="utf-8")
    print(f"[aplicado] AEC: ganho fixo +18 dB e supressão de ruído nível 2: {BELL_SERVICE_SMALI}")
    return 0


def _patch_text(root: Path, rel: Path, original: str, patched: str, label: str, check_only: bool) -> int:
    path = root / rel
    text = path.read_text(encoding="utf-8")
    if patched in text:
        print(f"[ok] {label}: {rel}")
        return 0
    if text.count(original) != 1:
        print(f"[erro] trecho original mudou ({label}) em {rel}")
        return 1
    if check_only:
        print(f"[pendente] {label}: {rel}")
        return 2
    path.write_text(text.replace(original, patched, 1), encoding="utf-8")
    print(f"[aplicado] {label}: {rel}")
    return 0


def patch_playback_preroll(root: Path, check_only: bool) -> int:
    return _patch_text(root, BELL_SERVICE_SMALI, PREROLL_ORIGINAL, PREROLL_PATCHED,
                       "pre-roll da voz em 400 ms", check_only)


def patch_disable_datadog(root: Path, check_only: bool) -> int:
    return _patch_text(root, DATADOG_SMALI, DATADOG_ORIGINAL, DATADOG_PATCHED,
                       "telemetria Datadog desligada", check_only)


def patch_startup_work(root: Path, check_only: bool) -> int:
    results = (
        _patch_text(root, WEBVIEW_WARMUP_SMALI, WEBVIEW_WARMUP_ORIGINAL, WEBVIEW_WARMUP_PATCHED,
                    "WebView sem pré-aquecimento", check_only),
        _patch_text(root, BELL_SERVICE_SMALI, NATIVE_START_ORIGINAL, NATIVE_START_PATCHED,
                    "VoiceIo.nativeStart fora da thread principal", check_only),
    )
    return 1 if 1 in results else max(results)


def patch_voice_panel(root: Path, check_only: bool) -> int:
    results = (
        _patch_text(root, BELL_SERVICE_SMALI, BELL_CREATE_ORIGINAL, BELL_CREATE_PATCHED,
                    "BellModeService.onCreate → painel de voz", check_only),
        _patch_text(root, BELL_SERVICE_SMALI, BELL_DESTROY_ORIGINAL, BELL_DESTROY_PATCHED,
                    "BellModeService.onDestroy → painel de voz", check_only),
        _patch_text(root, TEXT_PACING_SMALI, TEXT_PACING_ORIGINAL, TEXT_PACING_PATCHED,
                    "transcrição em REVEAL (sem karaokê)", check_only),
        _patch_text(root, STREAM_SMOOTHING_SMALI, STREAM_SMOOTHING_ORIGINAL, STREAM_SMOOTHING_PATCHED,
                    "suavizador de streaming desligado", check_only),
    )
    return 1 if 1 in results else max(results)


def patch_no_animations(root: Path, check_only: bool) -> int:
    return _patch_text(root, MOTION_SCALE_SMALI, MOTION_SCALE_ORIGINAL, MOTION_SCALE_PATCHED,
                       "animações Compose desligadas (escala 0)", check_only)


def patch_visualizer_off(root: Path, check_only: bool) -> int:
    return _patch_text(root, VIZ_THREAD_SMALI, VIZ_OFF_ORIGINAL, VIZ_OFF_PATCHED,
                       "visualizador GL do modo de voz desligado", check_only)


def patch_visualizer(root: Path, check_only: bool) -> int:
    shader_path = root / VIZ_SHADER_SMALI
    shader = shader_path.read_text(encoding="utf-8")
    thread_path = root / VIZ_THREAD_SMALI
    thread = thread_path.read_text(encoding="utf-8")
    shader_done = all(new in shader and old not in shader for old, new in VIZ_SHADER_EDITS)
    sleep_done = VIZ_SLEEP_PATCHED in thread
    if shader_done and sleep_done:
        print("[ok] visualizador de voz leve (sem ruído, mediump, ~30 quadros/s)")
        return 0
    if not shader_done and any(shader.count(old) != 1 for old, _ in VIZ_SHADER_EDITS):
        print(f"[erro] shader do visualizador mudou em {VIZ_SHADER_SMALI}")
        return 1
    if not sleep_done and VIZ_SLEEP_ORIGINAL not in thread:
        print(f"[erro] laço do visualizador mudou em {VIZ_THREAD_SMALI}")
        return 1
    if check_only:
        print("[pendente] visualizador de voz leve")
        return 2
    if not shader_done:
        for old, new in VIZ_SHADER_EDITS:
            shader = shader.replace(old, new, 1)
        shader_path.write_text(shader, encoding="utf-8")
    if not sleep_done:
        thread_path.write_text(thread.replace(VIZ_SLEEP_ORIGINAL, VIZ_SLEEP_PATCHED, 1), encoding="utf-8")
    print("[aplicado] visualizador de voz leve (sem ruído, mediump, ~30 quadros/s)")
    return 0


def patch_audio_opensl(root: Path, check_only: bool) -> int:
    path = root / APM_LIB
    data = path.read_bytes()
    if data.count(AAUDIO_DLOPEN_PATCHED) == 1 and AAUDIO_DLOPEN_ORIGINAL not in data:
        print(f"[ok] áudio do modo de voz via OpenSL ES: {APM_LIB}")
        return 0
    if data.count(AAUDIO_DLOPEN_ORIGINAL) != 1:
        print(f"[erro] nome do dlopen do AAudio não encontrado (1x) em {APM_LIB}")
        return 1
    if check_only:
        print(f"[pendente] áudio do modo de voz via OpenSL ES: {APM_LIB}")
        return 2
    path.write_bytes(data.replace(AAUDIO_DLOPEN_ORIGINAL, AAUDIO_DLOPEN_PATCHED, 1))
    print(f"[aplicado] áudio do modo de voz via OpenSL ES: {APM_LIB}")
    return 0


def patch_audio_output_buffer(root: Path, check_only: bool) -> int:
    path = root / APM_LIB
    data = path.read_bytes()
    if data.count(OUTPUT_PERF_PATCHED) == 1 and OUTPUT_PERF_ORIGINAL not in data:
        print(f"[ok] saída de voz sem trilha FAST (buffer do mixer): {APM_LIB}")
        return 0
    if data.count(OUTPUT_PERF_ORIGINAL) != 1:
        print(f"[erro] configurePerformanceMode do Oboe não encontrado (1x) em {APM_LIB}")
        return 1
    if check_only:
        print(f"[pendente] saída de voz sem trilha FAST: {APM_LIB}")
        return 2
    path.write_bytes(data.replace(OUTPUT_PERF_ORIGINAL, OUTPUT_PERF_PATCHED, 1))
    print(f"[aplicado] saída de voz sem trilha FAST (buffer do mixer): {APM_LIB}")
    return 0


def patch_oboe_output_mode(root: Path, check_only: bool) -> int:
    path = root / APM_LIB
    data = path.read_bytes()
    if data.count(OBOE_OUT_MODE_PATCHED) == 1 and OBOE_OUT_MODE_ORIGINAL not in data:
        print(f"[ok] stream de saída do Oboe em PerformanceMode::None: {APM_LIB}")
        return 0
    if data.count(OBOE_OUT_MODE_ORIGINAL) != 1:
        print(f"[erro] modo do stream de saída do Oboe não encontrado (1x) em {APM_LIB}")
        return 1
    if check_only:
        print(f"[pendente] stream de saída do Oboe em None: {APM_LIB}")
        return 2
    path.write_bytes(data.replace(OBOE_OUT_MODE_ORIGINAL, OBOE_OUT_MODE_PATCHED, 1))
    print(f"[aplicado] stream de saída do Oboe em PerformanceMode::None: {APM_LIB}")
    return 0


def patch_tts_fft_off(root: Path, check_only: bool) -> int:
    results = (
        _patch_text(root, TTS_FFT_SMALI, TTS_FFT_ORIGINAL, TTS_FFT_PATCHED,
                    "FFT do visualizador desligada no TTS", check_only),
        _patch_text(root, VIZ_POLL_SMALI, VIZ_POLL_ORIGINAL, VIZ_POLL_PATCHED,
                    "poll do visualizador em 40 ms", check_only),
    )
    return 1 if 1 in results else max(results)


def patch_voice_session_persistence(root: Path, check_only: bool) -> int:
    path = root / SESSION_SMALI
    if not path.exists():
        print(f"[erro] {SESSION_SMALI} não encontrado")
        return 1
    text = path.read_text(encoding="utf-8")
    call_finish = "invoke-virtual {p0}, Landroid/service/voice/VoiceInteractionSession;->finish()V"
    if call_finish not in text:
        print(f"[ok] VoiceInteractionSession persistente sem finish() (lógica Katniss): {SESSION_SMALI}")
        return 0
    if check_only:
        print(f"[pendente] VoiceInteractionSession autodestrutiva com finish(): {SESSION_SMALI}")
        return 2
    pattern = re.compile(
        r'(\s+invoke-virtual \{p2, p1\}, Landroid/content/Context;->startActivity\(Landroid/content/Intent;\)V\s*\n)'
        r'(?:\s+iget-boolean p1, p0, Ls37;->B:Z\s*\n\s+if-nez p1, :cond_1\s*\n\s+invoke-virtual \{p0\}, Landroid/service/voice/VoiceInteractionSession;->finish\(\)V\s*\n\s+:cond_1\s*\n)'
    )
    if pattern.search(text):
        new_text = pattern.sub(r'\1', text, count=1)
        path.write_text(new_text, encoding="utf-8")
        print(f"[aplicado] VoiceInteractionSession tornada persistente sem finish(): {SESSION_SMALI}")
        return 0
    print(f"[erro] bloco de finish() em {SESSION_SMALI} em formato inesperado")
    return 1


def patch_manifest_voice_process(root: Path, check_only: bool) -> int:
    path = root / MANIFEST_XML
    if not path.exists():
        print(f"[erro] {MANIFEST_XML} não encontrado")
        return 1
    text = path.read_text(encoding="utf-8")
    has_process = 'ClaudeVoiceInteractionService" android:permission="android.permission.BIND_VOICE_INTERACTION" android:process=":voice"' in text
    has_overlay_warm = 'android:launchMode="singleInstance" android:name="com.anthropic.claude.mainactivity.AssistantOverlayActivity" android:noHistory="false"' in text
    if has_process and has_overlay_warm:
        print("[ok] manifesto configurado para processo :voice e overlay warm (lógica Katniss)")
        return 0
    if check_only:
        print("[pendente] configuração de processo :voice e overlay warm no manifesto")
        return 2
    if not has_process:
        text = text.replace(
            'ClaudeVoiceInteractionService" android:permission="android.permission.BIND_VOICE_INTERACTION"',
            'ClaudeVoiceInteractionService" android:permission="android.permission.BIND_VOICE_INTERACTION" android:process=":voice"',
        )
        text = text.replace(
            'ClaudeVoiceInteractionSessionService" android:permission="android.permission.BIND_VOICE_INTERACTION"/>',
            'ClaudeVoiceInteractionSessionService" android:permission="android.permission.BIND_VOICE_INTERACTION" android:process=":voice"/>',
        )
        text = text.replace(
            'ClaudeRecognitionService" android:permission="android.permission.BIND_RECOGNITION_SERVICE">',
            'ClaudeRecognitionService" android:permission="android.permission.BIND_RECOGNITION_SERVICE" android:process=":voice">',
        )
    if not has_overlay_warm:
        text = text.replace(
            'android:finishOnTaskLaunch="true" android:launchMode="singleTask" android:name="com.anthropic.claude.mainactivity.AssistantOverlayActivity" android:noHistory="true"',
            'android:finishOnTaskLaunch="false" android:launchMode="singleInstance" android:name="com.anthropic.claude.mainactivity.AssistantOverlayActivity" android:noHistory="false"',
        )
    path.write_text(text, encoding="utf-8")
    print("[aplicado] manifesto configurado para processo :voice e overlay warm (lógica Katniss)")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 1
    root = Path(argv[1]).resolve()
    check_only = "--check" in argv[2:]
    if not (root / "apktool.yml").exists():
        print(f"[erro] {root} não parece ser um projeto apktool (apktool.yml ausente)")
        return 1
    results = (
        patch_overlay(root, check_only),
        patch_overlay_lifecycle(root, check_only),
        patch_overlay_resources(root, check_only),
        patch_overlay_voice(root, check_only),
        patch_chat_attachment_button(root, check_only),
        patch_chat_input_add_button(root, check_only),
        patch_attachment_icon_suppression(root, check_only),
        patch_weekly_limit_notice(root, check_only),
        patch_software_aec(root, check_only),
        patch_capture_builtin_mic(root, check_only),
        patch_software_aec_params(root, check_only),
        patch_playback_preroll(root, check_only),
        patch_disable_datadog(root, check_only),
        patch_visualizer(root, check_only),
        patch_visualizer_off(root, check_only),
        patch_no_animations(root, check_only),
        patch_startup_work(root, check_only),
        patch_voice_panel(root, check_only),
        patch_audio_opensl(root, check_only),
        patch_audio_output_buffer(root, check_only),
        patch_oboe_output_mode(root, check_only),
        patch_tts_fft_off(root, check_only),
        patch_voice_session_persistence(root, check_only),
        patch_manifest_voice_process(root, check_only),
        verify_main(root),
    )
    # 1 (inconsistência) tem prioridade sobre 2 (pendente), que tem prioridade sobre 0.
    if 1 in results:
        return 1
    if 2 in results:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
