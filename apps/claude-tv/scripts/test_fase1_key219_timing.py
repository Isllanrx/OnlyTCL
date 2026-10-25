import subprocess
import time
import re

ADB = r"E:\Android\Sdk\platform-tools\adb.exe"
DEVICE = "192.168.76.209:5555"

def adb(args, timeout=15):
    res = subprocess.run([ADB, "-s", DEVICE] + args, capture_output=True, text=True, timeout=timeout, errors="replace")
    return res.stdout.strip()

subprocess.run([ADB, "connect", DEVICE], capture_output=True)

# 1. Habilitar servico de acessibilidade do Claude TV
print("Configurando AccessibilityService...")
adb(["shell", "settings", "put", "secure", "enabled_accessibility_services", "com.anthropic.claude/com.anthropic.claude.tv.ClaudeTvAccessibilityService"])
adb(["shell", "settings", "put", "secure", "accessibility_enabled", "1"])
time.sleep(1)

# Verificar se esta vinculado
a11y_dump = adb(["shell", "dumpsys", "accessibility"])
bound = "ClaudeTvAccessibilityService" in a11y_dump
print(f"ClaudeTvAccessibilityService vinculado: {bound}")

# 2. Iniciar MainActivity para garantir processo acordado
adb(["shell", "am", "start-activity", "-W", "-n", "com.anthropic.claude/.mainactivity.MainActivity"])
time.sleep(2)
adb(["shell", "input", "keyevent", "3"]) # Home
time.sleep(2)

print("\n--- INICIANDO TESTE DO CAMINHO DE KEYCODE 219 (5 AMOSTRAS) ---")

samples = []

for run_idx in range(5):
    adb(["logcat", "-c"])
    time.sleep(0.5)
    
    t_inject = time.time()
    adb(["shell", "input", "keyevent", "219"])
    time.sleep(3)
    
    log = adb(["logcat", "-d", "-v", "threadtime"])
    
    t0_str, t1_str, t2_str, t3_str, t4_str, t5_str = None, None, None, None, None, None
    
    for line in log.splitlines():
        # T0: Evento mais baixo de input
        if ("handleKeyBeforeQueueing, key = 219, down = true" in line or "interceptKeyBeforeQueueing" in line) and not t0_str:
            t0_str = line[:18]
            
        # T1: AccessibilityService.onKeyEvent
        if ("ClaudeTvA11y" in line or "Overlay do Claude iniciado pela acessibilidade" in line) and not t1_str:
            t1_str = line[:18]
            
        # T2: TclPhoneWindowManager politica / long-press
        if ("startAssistLongPressFunction" in line or "handleKeyBeforeDispatching, key = 219" in line) and not t2_str:
            t2_str = line[:18]
            
        # T3: Início do Intent
        if ("AssistantOverlayActivity aberto" in line or "sendBroadcast: com.anthropic.claude" in line) and not t3_str:
            t3_str = line[:18]
            
        # T4: ActivityTaskManager START
        if ("START u0" in line and "AssistantOverlayActivity" in line) and not t4_str:
            t4_str = line[:18]
            
        # T5: Primeiro frame util / Displayed
        if ("Displayed com.anthropic.claude" in line and "AssistantOverlayActivity" in line) and not t5_str:
            t5_str = line[:18]

    # Fechar se abriu
    adb(["shell", "input", "keyevent", "4"])
    time.sleep(1)
    
    sample = {
        "run": run_idx + 1,
        "T0_input": t0_str,
        "T1_a11y": t1_str,
        "T2_policy": t2_str,
        "T3_intent": t3_str,
        "T4_start": t4_str,
        "T5_displayed": t5_str
    }
    samples.append(sample)
    print(f"Run {run_idx+1}:")
    print(f"  T0 (Input Queue) : {t0_str}")
    print(f"  T1 (A11y onKey)  : {t1_str}")
    print(f"  T2 (TCL Policy)  : {t2_str}")
    print(f"  T3 (Intent Open) : {t3_str}")
    print(f"  T4 (ATM START)   : {t4_str}")
    print(f"  T5 (Displayed)   : {t5_str}")

# Desabilitar acessibilidade após teste para não afetar baseline
# adb(["shell", "settings", "put", "secure", "accessibility_enabled", "0"])
