import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import subprocess
import threading
import time
import sys
import re

from load_env import ADB, DEVICE, TV, DEV, PROJECT_ROOT, OUTPUT_DIR
# TV loaded from load_env

def run_adb(*args):
    return subprocess.run([ADB, "-s", TV, *args], capture_output=True, text=True, timeout=10)

def connect():
    subprocess.run([ADB, "connect", TV], capture_output=True, text=True, timeout=10)

def monitor_events(stop_event):
    cmd = [ADB, "-s", TV, "shell", "getevent", "-lt"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    try:
        for line in iter(p.stdout.readline, ''):
            if stop_event.is_set():
                break
            line_str = line.strip()
            if any(k in line_str for k in ['KEY_ENTER', 'KEY_OK', 'BTN_MOUSE', 'BTN_TOUCH', 'DOWN', 'UP', '014a', '001c']):
                print(f"[INPUT_EVENT] {line_str}", flush=True)
    finally:
        p.terminate()

def monitor_logcat(stop_event):
    cmd = [ADB, "-s", TV, "logcat", "-v", "time", "-T", "1"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    patterns = [
        re.compile(r'com\.anthropic\.claude', re.IGNORECASE),
        re.compile(r'ActivityTaskManager', re.IGNORECASE),
        re.compile(r'START u0', re.IGNORECASE),
        re.compile(r'ClaudeTvHelper', re.IGNORECASE),
        re.compile(r'chat', re.IGNORECASE),
        re.compile(r'attach', re.IGNORECASE),
        re.compile(r'chooser', re.IGNORECASE),
        re.compile(r'document', re.IGNORECASE)
    ]
    try:
        for line in iter(p.stdout.readline, ''):
            if stop_event.is_set():
                break
            line_str = line.strip()
            if any(pat.search(line_str) for pat in patterns):
                # Ignore noisy datadog trace or heartbeat logs unless relevant
                if "datadog" in line_str.lower() and "trace" in line_str.lower():
                    continue
                print(f"[LOGCAT] {line_str}", flush=True)
    finally:
        p.terminate()

def main():
    print("[INFO] Conectando a TV...", flush=True)
    connect()
    # Limpa logcat
    run_adb("logcat", "-c")
    print("[READY] Monitor de cliques ativo!", flush=True)
    print("[READY] O monitor está escutando eventos de controle remoto e logcat na TV.", flush=True)
    print("[READY] Você pode clicar no botão (+) no controle para registrar a ação real.", flush=True)

    stop_event = threading.Event()
    t_input = threading.Thread(target=monitor_events, args=(stop_event,), daemon=True)
    t_logcat = threading.Thread(target=monitor_logcat, args=(stop_event,), daemon=True)
    t_input.start()
    t_logcat.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[INFO] Encerrando monitor...", flush=True)
        stop_event.set()

if __name__ == "__main__":
    main()
