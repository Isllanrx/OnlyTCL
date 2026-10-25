import subprocess
import time
import json
import re

ADB = r"E:\Android\Sdk\platform-tools\adb.exe"
DEVICE = "192.168.76.209:5555"

def adb(args):
    return subprocess.run([ADB, "-s", DEVICE] + args, capture_output=True, text=True, errors="replace").stdout.strip()

subprocess.run([ADB, "connect", DEVICE], capture_output=True)

# 1. Garantir role e servico de voz
adb(["shell", "cmd", "role", "add-role-holder", "--user", "0", "android.app.role.ASSISTANT", "com.anthropic.claude"])
adb(["shell", "settings", "put", "secure", "assistant", "com.anthropic.claude/.bell.assist.ClaudeVoiceInteractionService"])
adb(["shell", "settings", "put", "secure", "voice_interaction_service", "com.anthropic.claude/.bell.assist.ClaudeVoiceInteractionService"])

voice_dump = adb(["shell", "dumpsys", "voiceinteraction"])
print("Voice interaction state:")
for line in voice_dump.splitlines():
    if any(k in line for k in ["mCurUser", "mCurService", "mCurSession", "mEnableService", "active"]):
        print("  ", line.strip())

# 2. Testar tecla 219 (KEYCODE_ASSIST)
print("\n--- Testando disparo via Keyevent 219 (KEYCODE_ASSIST) ---")
adb(["logcat", "-c"])
t0 = time.time()
adb(["shell", "input", "keyevent", "219"])
time.sleep(2)
t_end = time.time()

log_out = adb(["logcat", "-d", "-v", "threadtime"])
key_events = []
for l in log_out.splitlines():
    if any(k in l for k in ["TclPhoneWindowManager", "VoiceInteractionManager", "AssistantOverlayActivity", "AudioRecord", "Puremic", "AtvRemote", "ErrorDisconnected", "ClaudeTV"]):
        key_events.append(l)

print(f"Logcat de eventos de voz (Key 219) - total {len(key_events)} linhas:")
for l in key_events[:25]:
    print("  ", l)

# Fechar se abriu
adb(["shell", "input", "keyevent", "4"])
time.sleep(1)

# 3. Testar tecla 231 (KEYCODE_VOICE_ASSIST)
print("\n--- Testando disparo via Keyevent 231 (KEYCODE_VOICE_ASSIST) ---")
adb(["logcat", "-c"])
adb(["shell", "input", "keyevent", "231"])
time.sleep(2)

log_out2 = adb(["logcat", "-d", "-v", "threadtime"])
key_events2 = []
for l in log_out2.splitlines():
    if any(k in l for k in ["TclPhoneWindowManager", "VoiceInteractionManager", "AssistantOverlayActivity", "AudioRecord", "Puremic", "AtvRemote", "ErrorDisconnected", "ClaudeTV"]):
        key_events2.append(l)

print(f"Logcat de eventos de voz (Key 231) - total {len(key_events2)} linhas:")
for l in key_events2[:25]:
    print("  ", l)

adb(["shell", "input", "keyevent", "4"])
