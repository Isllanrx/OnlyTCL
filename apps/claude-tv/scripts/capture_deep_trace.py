import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import subprocess
import time
import os

from load_env import ADB, DEVICE, TV, DEV, PROJECT_ROOT, OUTPUT_DIR
# DEVICE loaded from load_env

def adb(args, timeout=30):
    return subprocess.run([ADB, "-s", DEVICE] + args, capture_output=True, text=True, timeout=timeout, errors="replace").stdout

subprocess.run([ADB, "connect", DEVICE], capture_output=True)

# 1. Fechar tudo e ir para HOME
adb(["shell", "input", "keyevent", "3"])
time.sleep(2)

print("Iniciando captura com atrace (categorias: gfx view wm am sched binder_driver dalvik)...")
# Iniciar atrace em background no device
trace_cmd = "atrace --async_start -b 16384 gfx view wm am sched binder_driver dalvik"
adb(["shell", trace_cmd])

time.sleep(0.5)

# Disparar abertura do overlay
t0 = time.time()
print("Disparando AssistantOverlayActivity...")
start_out = adb(["shell", "am", "start-activity", "-W", "-n", "com.anthropic.claude/.mainactivity.AssistantOverlayActivity", "-a", "android.intent.action.VOICE_ASSIST", "-f", "0x34000000"])
print(f"am start retornou em {(time.time()-t0)*1000:.1f}ms:\n{start_out.strip()}")

time.sleep(2)

# Parar atrace e coletar
print("Parando e salvando atrace...")
trace_raw = adb(["shell", "atrace", "--async_stop"], timeout=60)
trace_path = str(Path(__file__).resolve().parent / "overlay_atrace.txt")
with open(trace_path, "w", encoding="utf-8", errors="replace") as f:
    f.write(trace_raw)

print(f"Trace salvo com sucesso em: {trace_path} (Tamanho: {len(trace_raw)//1024} KB)")

# Fechar overlay
adb(["shell", "input", "keyevent", "4"])
