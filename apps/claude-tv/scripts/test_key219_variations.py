import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import subprocess
import time
import re
import json

from load_env import ADB, DEVICE, TV, DEV, PROJECT_ROOT, OUTPUT_DIR
# DEVICE loaded from load_env

def adb(args):
    return subprocess.run([ADB, "-s", DEVICE] + args, capture_output=True, text=True, errors="replace").stdout.strip()

subprocess.run([ADB, "connect", DEVICE], capture_output=True)

def parse_time(ts_str):
    try:
        parts = ts_str.split()
        time_part = parts[1]
        h, m, s_ms = time_part.split(":")
        s, ms = s_ms.split(".")
        return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0
    except Exception:
        return None

results = []

print("=== TESTANDO 10 PRESSÕES SUCESSIVAS DA TECLA 219 ===")

for i in range(10):
    adb(["shell", "input", "keyevent", "4"]) # Fecha overlay se aberto
    time.sleep(1)
    adb(["logcat", "-c"])
    time.sleep(0.3)
    
    adb(["shell", "input", "keyevent", "219"])
    time.sleep(2)
    
    log = adb(["logcat", "-d", "-v", "threadtime"])
    t0_raw, t2_raw, t4_raw, t6_raw, t7_raw = None, None, None, None, None
    
    for l in log.splitlines():
        if "handleKeyBeforeQueueing, key = 219, down = true" in l and not t0_raw:
            t0_raw = l[:18]
        if "startAssistLongPressFunction" in l and not t2_raw:
            t2_raw = l[:18]
        if "START u0" in l and "AssistantOverlayActivity" in l and not t4_raw:
            t4_raw = l[:18]
        if "onResumeTopActivity" in l and "AssistantOverlayActivity" in l and not t6_raw:
            t6_raw = l[:18]
        if "Displayed com.anthropic.claude/.mainactivity.AssistantOverlayActivity" in l and not t7_raw:
            t7_raw = l[:18]
            
    t0 = parse_time(t0_raw) if t0_raw else None
    t2 = parse_time(t2_raw) if t2_raw else None
    t4 = parse_time(t4_raw) if t4_raw else None
    t6 = parse_time(t6_raw) if t6_raw else None
    t7 = parse_time(t7_raw) if t7_raw else None
    
    d_T0_T2 = (t2 - t0)*1000 if (t0 and t2) else None
    d_T2_T4 = (t4 - t2)*1000 if (t2 and t4) else None
    d_T0_T4 = (t4 - t0)*1000 if (t0 and t4) else None
    d_T4_T7 = (t7 - t4)*1000 if (t4 and t7) else None
    d_total = (t7 - t0)*1000 if (t0 and t7) else None
    
    sample = {
        "press": i + 1,
        "t0": t0_raw, "t2": t2_raw, "t4": t4_raw, "t7": t7_raw,
        "T0_T2_ms (TCL Debounce)": d_T0_T2,
        "T2_T4_ms (Broadcast->ATM)": d_T2_T4,
        "T0_T4_ms (Input->ATM START)": d_T0_T4,
        "T4_T7_ms (ATM->Displayed)": d_T4_T7,
        "Total_T0_T7_ms": d_total
    }
    results.append(sample)
    print(f"Press {i+1}: T0->T2 (Debounce): {d_T0_T2}ms | T2->T4 (Intent): {d_T2_T4}ms | T0->T4 (Total Input->START): {d_T0_T4}ms | T4->T7: {d_T4_T7}ms")

with open(str(Path(__file__).resolve().parent / "audit_caso1_10runs.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nConcluído!")
