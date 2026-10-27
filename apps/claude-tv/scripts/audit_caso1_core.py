import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import subprocess
import time
import re
import json
import statistics
from datetime import datetime

from load_env import ADB, DEVICE, TV, DEV, PROJECT_ROOT, OUTPUT_DIR
# DEVICE loaded from load_env
PKG = "com.anthropic.claude"
OVERLAY_ACT = "com.anthropic.claude/.mainactivity.AssistantOverlayActivity"
MAIN_ACT = "com.anthropic.claude/.mainactivity.MainActivity"

def adb(args, timeout=20):
    cmd = [ADB, "-s", DEVICE] + args
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
    return res.stdout.strip()

subprocess.run([ADB, "connect", DEVICE], capture_output=True)

def parse_time(ts_str):
    # Formato: 10-04 10:05:12.345
    # Retorna segundos float dentro do dia
    try:
        parts = ts_str.split()
        time_part = parts[1] # 10:05:12.345
        h, m, s_ms = time_part.split(":")
        s, ms = s_ms.split(".")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
    except Exception:
        return None

def run_single_key219_test():
    adb(["logcat", "-c"])
    time.sleep(0.3)
    
    t_start = time.time()
    adb(["shell", "input", "keyevent", "219"])
    time.sleep(2.5)
    
    log = adb(["logcat", "-d", "-v", "threadtime"])
    
    t0_ts, t1_ts, t2_ts, t3_ts, t4_ts, t5_ts, t6_ts, t7_ts = [None]*8
    t0_raw, t1_raw, t2_raw, t3_raw, t4_raw, t5_raw, t6_raw, t7_raw = [""]*8
    
    for line in log.splitlines():
        # T0: primeiro evento observavel no pipeline de input
        if "handleKeyBeforeQueueing, key = 219, down = true" in line and not t0_raw:
            t0_raw = line[:18]
            t0_ts = parse_time(t0_raw)
            
        # T1: entrada no TclPhoneWindowManager
        if "handleKeyBeforeQueueing" in line and "219" in line and not t1_raw:
            t1_raw = line[:18]
            t1_ts = parse_time(t1_raw)
            
        # T2: saida/decisao do TclPhoneWindowManager (startAssistLongPressFunction ou handleKeyBeforeDispatching)
        if ("startAssistLongPressFunction" in line or "handleKeyBeforeDispatching, key = 219" in line) and not t2_raw:
            t2_raw = line[:18]
            t2_ts = parse_time(t2_raw)
            
        # T3: resolucao / disparo do Assist Intent / broadcast
        if ("sendBroadcast: com.anthropic.claude" in line or "showSessionFromSessionService" in line or "startVoiceInteraction" in line or "startAssistActivity" in line) and not t3_raw:
            t3_raw = line[:18]
            t3_ts = parse_time(t3_raw)
            
        # T4: ActivityTaskManager START
        if ("START u0" in line and "AssistantOverlayActivity" in line) and not t4_raw:
            t4_raw = line[:18]
            t4_ts = parse_time(t4_raw)
            
        # T5: onCreate
        if ("ClaudeTV: Overlay configurado" in line or "onOverlayCreate" in line or "AssistantOverlay: Starting" in line) and not t5_raw:
            t5_raw = line[:18]
            t5_ts = parse_time(t5_raw)
            
        # T6: onResume
        if ("onResumeTopActivity com.anthropic.claude" in line and "AssistantOverlayActivity" in line) and not t6_raw:
            t6_raw = line[:18]
            t6_ts = parse_time(t6_raw)
            
        # T7: primeiro frame util / Displayed
        if ("Displayed com.anthropic.claude/.mainactivity.AssistantOverlayActivity" in line) and not t7_raw:
            t7_raw = line[:18]
            t7_ts = parse_time(t7_raw)

    # Fechar overlay para próxima execução
    adb(["shell", "input", "keyevent", "4"])
    time.sleep(1)
    
    return {
        "raw": {"T0": t0_raw, "T1": t1_raw, "T2": t2_raw, "T3": t3_raw, "T4": t4_raw, "T5": t5_raw, "T6": t6_raw, "T7": t7_raw},
        "ts": {"T0": t0_ts, "T1": t1_ts, "T2": t2_ts, "T3": t3_ts, "T4": t4_ts, "T5": t5_ts, "T6": t6_ts, "T7": t7_ts}
    }

def compute_deltas(test_res):
    ts = test_res["ts"]
    t0 = ts["T0"]
    if not t0: return {}
    
    d = {}
    if ts["T1"] is not None: d["T0_T1_ms"] = (ts["T1"] - t0) * 1000.0
    if ts["T2"] is not None: d["T0_T2_ms"] = (ts["T2"] - t0) * 1000.0
    if ts["T4"] is not None: d["T0_T4_ms"] = (ts["T4"] - t0) * 1000.0
    if ts["T5"] is not None: d["T4_T5_ms"] = (ts["T5"] - ts["T4"]) * 1000.0
    if ts["T7"] is not None:
        d["T0_T7_total_ms"] = (ts["T7"] - t0) * 1000.0
        if ts["T4"] is not None: d["T4_T7_ms"] = (ts["T7"] - ts["T4"]) * 1000.0
    return d

print("Helper de auditoria do Caso 1 carregado.")
