import subprocess

ADB = r"E:\Android\Sdk\platform-tools\adb.exe"
DEVICE = "192.168.76.209:5555"

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
