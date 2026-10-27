import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import subprocess

from load_env import ADB, DEVICE, TV, DEV, PROJECT_ROOT, OUTPUT_DIR
# DEVICE loaded from load_env

def adb(args):
    return subprocess.run([ADB, "-s", DEVICE] + args, capture_output=True, text=True, errors="replace").stdout.strip()

subprocess.run([ADB, "connect", DEVICE], capture_output=True)

print("Current Focus:")
w_dump = adb(["shell", "dumpsys", "window"])
for line in w_dump.splitlines():
    if any(k in line for k in ["mCurrentFocus", "mFocusedApp", "mFocusedWindow"]):
        print("  ", line.strip())

print("\nTop Activities:")
act_dump = adb(["shell", "dumpsys", "activity", "activities"])
for line in act_dump.splitlines():
    if any(k in line for k in ["mResumedActivity", "topResumedActivity", "ResumedActivity"]):
        print("  ", line.strip())
