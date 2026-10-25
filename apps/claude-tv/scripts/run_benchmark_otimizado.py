import subprocess
import time
import json
import re
import os
import statistics
from profiler_core import (
    run_adb, connect, force_stop, go_home, clear_logcat,
    get_pid, get_meminfo, get_gfxinfo, reset_gfxinfo,
    parse_am_start, parse_davey_and_gc, PKG, MAIN_ACT, OVERLAY_ACT
)

OUTPUT_FILE = r"E:\projeto_twitchlit\claude-tv\scripts\profiling_otimizado_results.json"

results = {
    "device_info": {},
    "aot_status": {},
    "jni_benchmark": {},
    "cold_start_main": [],
    "warm_start_main": [],
    "overlay_warm_start": [],
    "overlay_cold_start": [],
    "voice_key_trigger": [],
    "ui_dpad_navigation": [],
    "task_switching": [],
    "atrace_summary": {}
}

print("=== CONECTANDO E INICIANDO BATERIA DE PROFILING EMPÍRICO NO APK OTIMIZADO ===")
connect()

# -------------------------------------------------------------
# 0. Informações de Hardware e Sistema
# -------------------------------------------------------------
print("\n[FASE 0] Coletando Informações de Hardware, CPU e Sistema...")
cpu_cur_freq = run_adb(["shell", "cat", "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"])
cpu_gov = run_adb(["shell", "cat", "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"])
mem_info_raw = run_adb(["shell", "cat", "/proc/meminfo"])
kernel_version = run_adb(["shell", "uname", "-a"])

mem_dict = {}
for line in mem_info_raw.splitlines()[:12]:
    parts = line.split(":")
    if len(parts) == 2:
        mem_dict[parts[0].strip()] = parts[1].strip()

results["device_info"] = {
    "model": run_adb(["shell", "getprop", "ro.product.model"]),
    "android_version": run_adb(["shell", "getprop", "ro.build.version.release"]),
    "sdk": run_adb(["shell", "getprop", "ro.build.version.sdk"]),
    "abi": run_adb(["shell", "getprop", "ro.product.cpu.abi"]),
    "cpu_freq_khz": cpu_cur_freq,
    "cpu_governor": cpu_gov,
    "kernel": kernel_version,
    "meminfo": mem_dict
}

# -------------------------------------------------------------
# 1. Verificação AOT / Dexopt
# -------------------------------------------------------------
print("\n[FASE 1] Verificando Estado Real de Compilação AOT (Dexopt)...")
pkg_dump = run_adb(["shell", "dumpsys", "package", PKG])
dexopt_lines = [l.strip() for l in pkg_dump.splitlines() if "dexopt" in l.lower() or "status=" in l.lower() or "compilation" in l.lower()]
results["aot_status"] = {
    "dexopt_state": dexopt_lines[:10],
    "is_speed": any("status=speed" in l for l in dexopt_lines)
}
print(f"Status Dexopt: {results['aot_status']}")

# -------------------------------------------------------------
# 2. Benchmark JNI / Rust RTK Boundary
# -------------------------------------------------------------
print("\n[FASE 2] Medindo Custo da Fronteira JNI / Rust (RTK)...")
jni_latencies_ms = []
force_stop()
run_adb(["shell", "am", "start-activity", "-W", "-n", MAIN_ACT])
time.sleep(3)

for i in range(5):
    t0 = time.time()
    res = run_adb(["shell", "am", "broadcast", "-a", "com.anthropic.claude.tv.VOICE_COMMAND", "--es", "query", f"teste_comando_{i}"])
    dt_ms = (time.time() - t0) * 1000.0
    jni_latencies_ms.append(dt_ms)

results["jni_benchmark"] = {
    "command_roundtrip_ms": jni_latencies_ms,
    "avg_ms": statistics.mean(jni_latencies_ms),
    "min_ms": min(jni_latencies_ms),
    "max_ms": max(jni_latencies_ms)
}
print(f"JNI / Broadcast Roundtrip (ms): {results['jni_benchmark']}")

# -------------------------------------------------------------
# 3. Cenário 1: Cold Start da MainActivity (5 Amostras)
# -------------------------------------------------------------
print("\n[FASE 3] Executando 5 Amostras de COLD START da MainActivity (OTIMIZADO)...")
for run_idx in range(5):
    print(f"  > Execução {run_idx + 1}/5...")
    force_stop()
    time.sleep(1)
    clear_logcat()
    reset_gfxinfo()
    
    t_start = time.time()
    out = run_adb(["shell", "am", "start-activity", "-W", "-n", MAIN_ACT])
    t_end = time.time()
    
    parsed_am = parse_am_start(out)
    time.sleep(2)
    
    pid = get_pid()
    log_raw = run_adb(["logcat", "-d", "-v", "threadtime"])
    log_lines = log_raw.splitlines()
    davey_gc = parse_davey_and_gc(log_lines)
    gfx = get_gfxinfo()
    mem = get_meminfo()
    
    top_out = run_adb(["shell", "top", "-b", "-n", "1", "-H", "-p", str(pid) if pid else "0"])
    
    sample = {
        "run": run_idx + 1,
        "pid": pid,
        "wall_time_ms": (t_end - t_start) * 1000.0,
        "am_start": parsed_am,
        "meminfo": mem,
        "gfxinfo": gfx,
        "davey_breakdown": davey_gc["daveys"][:3],
        "gc_events_count": len(davey_gc["gcs"]),
        "skipped_frames_total": sum(davey_gc["skipped_frames"]),
        "top_threads": [l.strip() for l in top_out.splitlines()[:10] if l.strip()]
    }
    results["cold_start_main"].append(sample)
    print(f"    TotalTime: {parsed_am['total_time']} ms | PSS: {mem.get('total_pss_kb', 0)//1024} MB | Jank: {gfx['jank_pct']}% | Skipped: {sample['skipped_frames_total']}")

# -------------------------------------------------------------
# 4. Cenário 2: Warm Start da MainActivity (5 Amostras)
# -------------------------------------------------------------
print("\n[FASE 4] Executando 5 Amostras de WARM START da MainActivity (OTIMIZADO)...")
for run_idx in range(5):
    print(f"  > Execução {run_idx + 1}/5...")
    go_home()
    time.sleep(2)
    clear_logcat()
    reset_gfxinfo()
    
    t_start = time.time()
    out = run_adb(["shell", "am", "start-activity", "-W", "-n", MAIN_ACT])
    t_end = time.time()
    
    parsed_am = parse_am_start(out)
    time.sleep(2)
    
    pid = get_pid()
    log_raw = run_adb(["logcat", "-d", "-v", "threadtime"])
    log_lines = log_raw.splitlines()
    davey_gc = parse_davey_and_gc(log_lines)
    gfx = get_gfxinfo()
    mem = get_meminfo()
    
    sample = {
        "run": run_idx + 1,
        "pid": pid,
        "wall_time_ms": (t_end - t_start) * 1000.0,
        "am_start": parsed_am,
        "meminfo": mem,
        "gfxinfo": gfx,
        "davey_breakdown": davey_gc["daveys"][:3],
        "gc_events_count": len(davey_gc["gcs"]),
        "skipped_frames_total": sum(davey_gc["skipped_frames"])
    }
    results["warm_start_main"].append(sample)
    print(f"    TotalTime: {parsed_am['total_time']} ms | PSS: {mem.get('total_pss_kb', 0)//1024} MB | Jank: {gfx['jank_pct']}% | Skipped: {sample['skipped_frames_total']}")

# -------------------------------------------------------------
# 5. Cenário 3 & 4: Overlay Warm Start & Close/Reopen (5 Amostras)
# -------------------------------------------------------------
print("\n[FASE 5] Executando 5 Amostras de WARM START do ASSISTANT OVERLAY (OTIMIZADO)...")
for run_idx in range(5):
    print(f"  > Execução {run_idx + 1}/5...")
    go_home()
    time.sleep(2)
    clear_logcat()
    reset_gfxinfo()
    
    t_start = time.time()
    out = run_adb(["shell", "am", "start-activity", "-W", "-n", OVERLAY_ACT, "-a", "android.intent.action.VOICE_ASSIST", "-f", "0x34000000"])
    t_end = time.time()
    
    parsed_am = parse_am_start(out)
    time.sleep(2)
    
    pid = get_pid()
    log_raw = run_adb(["logcat", "-d", "-v", "threadtime"])
    log_lines = log_raw.splitlines()
    davey_gc = parse_davey_and_gc(log_lines)
    gfx = get_gfxinfo()
    mem = get_meminfo()
    
    t_close_start = time.time()
    run_adb(["shell", "input", "keyevent", "4"]) # KEYCODE_BACK
    time.sleep(1)
    close_duration_ms = (time.time() - t_close_start) * 1000.0
    
    sample = {
        "run": run_idx + 1,
        "pid": pid,
        "wall_time_ms": (t_end - t_start) * 1000.0,
        "close_duration_ms": close_duration_ms,
        "am_start": parsed_am,
        "meminfo": mem,
        "gfxinfo": gfx,
        "davey_breakdown": davey_gc["daveys"][:3],
        "gc_events_count": len(davey_gc["gcs"]),
        "skipped_frames_total": sum(davey_gc["skipped_frames"])
    }
    results["overlay_warm_start"].append(sample)
    print(f"    TotalTime: {parsed_am['total_time']} ms | PSS: {mem.get('total_pss_kb', 0)//1024} MB | Jank: {gfx['jank_pct']}% | Close: {close_duration_ms:.0f} ms")

# -------------------------------------------------------------
# 6. Cenário 4B: Overlay Cold Start (Processo Morto) (3 Amostras)
# -------------------------------------------------------------
print("\n[FASE 6] Executando 3 Amostras de COLD START do ASSISTANT OVERLAY (OTIMIZADO)...")
for run_idx in range(3):
    print(f"  > Execução {run_idx + 1}/3...")
    force_stop()
    time.sleep(1)
    clear_logcat()
    reset_gfxinfo()
    
    t_start = time.time()
    out = run_adb(["shell", "am", "start-activity", "-W", "-n", OVERLAY_ACT, "-a", "android.intent.action.VOICE_ASSIST", "-f", "0x34000000"])
    t_end = time.time()
    
    parsed_am = parse_am_start(out)
    time.sleep(2)
    
    pid = get_pid()
    log_raw = run_adb(["logcat", "-d", "-v", "threadtime"])
    log_lines = log_raw.splitlines()
    davey_gc = parse_davey_and_gc(log_lines)
    gfx = get_gfxinfo()
    mem = get_meminfo()
    
    run_adb(["shell", "input", "keyevent", "4"])
    time.sleep(1)
    
    sample = {
        "run": run_idx + 1,
        "pid": pid,
        "wall_time_ms": (t_end - t_start) * 1000.0,
        "am_start": parsed_am,
        "meminfo": mem,
        "gfxinfo": gfx,
        "davey_breakdown": davey_gc["daveys"][:3],
        "gc_events_count": len(davey_gc["gcs"]),
        "skipped_frames_total": sum(davey_gc["skipped_frames"])
    }
    results["overlay_cold_start"].append(sample)
    print(f"    Cold Overlay TotalTime: {parsed_am['total_time']} ms | PSS: {mem.get('total_pss_kb', 0)//1024} MB | Jank: {gfx['jank_pct']}%")

# -------------------------------------------------------------
# 7. Cenário 5: Gatilho Tecla de Voz (219) (3 Amostras)
# -------------------------------------------------------------
print("\n[FASE 7] Medindo Gatilho por Tecla de Voz Física (219)...")
for run_idx in range(3):
    print(f"  > Execução {run_idx + 1}/3...")
    go_home()
    time.sleep(2)
    clear_logcat()
    
    t_inject = time.time()
    run_adb(["shell", "input", "keyevent", "219"])
    time.sleep(3)
    
    log_raw = run_adb(["logcat", "-d", "-v", "threadtime"])
    log_lines = log_raw.splitlines()
    
    ts_key = None
    ts_act_start = None
    ts_displayed = None
    ts_audio_init = None
    audio_error = None
    
    for l in log_lines:
        if "interceptKeyBeforeQueueing" in l or "injectKeyEvent" in l or "219" in l:
            if not ts_key: ts_key = l[:18]
        if "START u0" in l and "AssistantOverlayActivity" in l:
            if not ts_act_start: ts_act_start = l[:18]
        if "Displayed com.anthropic.claude" in l and "AssistantOverlayActivity" in l:
            if not ts_displayed: ts_displayed = l[:18]
        if "AudioRecord" in l or "Puremic" in l or "AudioBridgeX" in l:
            if not ts_audio_init: ts_audio_init = l[:18]
        if "ErrorDisconnected" in l or "dead IAudioRecord" in l:
            audio_error = l.strip()
            
    run_adb(["shell", "input", "keyevent", "4"])
    time.sleep(1)
    
    sample = {
        "run": run_idx + 1,
        "ts_key": ts_key,
        "ts_act_start": ts_act_start,
        "ts_displayed": ts_displayed,
        "ts_audio_init": ts_audio_init,
        "audio_error": audio_error
    }
    results["voice_key_trigger"].append(sample)
    print(f"    Trigger Key -> Act: {ts_act_start} | Displayed: {ts_displayed} | Error: {bool(audio_error)}")

# -------------------------------------------------------------
# 8. Cenário 6: Navegação UI via D-Pad (5 Amostras)
# -------------------------------------------------------------
print("\n[FASE 8] Medindo Interação na UI / Navegação D-Pad (OTIMIZADO)...")
run_adb(["shell", "am", "start-activity", "-W", "-n", MAIN_ACT])
time.sleep(3)

for run_idx in range(5):
    print(f"  > Execução {run_idx + 1}/5 (D-Pad sequence)...")
    reset_gfxinfo()
    
    for key in ["20", "20", "22", "19", "21"]:
        run_adb(["shell", "input", "keyevent", key])
        time.sleep(0.15)
        
    time.sleep(1)
    gfx = get_gfxinfo()
    results["ui_dpad_navigation"].append({
        "run": run_idx + 1,
        "gfx": gfx
    })
    print(f"    Frames: {gfx['total_frames']} | Jank: {gfx['jank_pct']}% | p50: {gfx['p50_ms']}ms | p90: {gfx['p90_ms']}ms | UI Slow: {gfx['slow_ui_thread']} | Missed Vsync: {gfx['missed_vsync']}")

# -------------------------------------------------------------
# 9. Cenário 7: Alternância de Tarefas (App Switch)
# -------------------------------------------------------------
print("\n[FASE 9] Testando Alternância entre Apps e Retenção de Memória (OTIMIZADO)...")
for run_idx in range(3):
    print(f"  > Execução {run_idx + 1}/3...")
    run_adb(["shell", "am", "start-activity", "-W", "-n", MAIN_ACT])
    time.sleep(2)
    pid_before = get_pid()
    mem_before = get_meminfo()
    
    run_adb(["shell", "am", "start-activity", "-a", "android.settings.SETTINGS"])
    time.sleep(3)
    
    pid_during = get_pid()
    
    t_start = time.time()
    out = run_adb(["shell", "am", "start-activity", "-W", "-n", MAIN_ACT])
    t_resume = (time.time() - t_start) * 1000.0
    parsed_am = parse_am_start(out)
    mem_after = get_meminfo()
    
    sample = {
        "run": run_idx + 1,
        "pid_before": pid_before,
        "pid_during": pid_during,
        "pid_survived": (pid_before == pid_during and pid_before is not None),
        "resume_time_ms": t_resume,
        "am_start": parsed_am,
        "pss_before_kb": mem_before.get("total_pss_kb", 0),
        "pss_after_kb": mem_after.get("total_pss_kb", 0)
    }
    results["task_switching"].append(sample)
    print(f"    Survived: {sample['pid_survived']} | Resume Time: {parsed_am['total_time']} ms | PSS: {mem_after.get('total_pss_kb', 0)//1024} MB")

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n=== BATERIA DE BENCHMARK NO APK OTIMIZADO CONCLUÍDA COM SUCESSO! ===")
print(f"Resultados gravados em: {OUTPUT_FILE}")
