import subprocess
import json

ADB = r"E:\Android\Sdk\platform-tools\adb.exe"
DEVICE = "192.168.76.209:5555"

def adb_cmd(cmd_list, timeout=15):
    full_cmd = [ADB, "-s", DEVICE] + cmd_list
    try:
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def connect():
    subprocess.run([ADB, "connect", DEVICE], capture_output=True, text=True)

connect()

checks = {
    "model": ["shell", "getprop", "ro.product.model"],
    "android_version": ["shell", "getprop", "ro.build.version.release"],
    "sdk": ["shell", "getprop", "ro.build.version.sdk"],
    "cpu_abi": ["shell", "getprop", "ro.product.cpu.abi"],
    "cpu_present": ["shell", "cat", "/sys/devices/system/cpu/present"],
    "cpu_cur_freq": ["shell", "cat", "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"],
    "cpu_gov": ["shell", "cat", "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"],
    "meminfo": ["shell", "cat", "/proc/meminfo"],
    "psi_cpu": ["shell", "cat", "/proc/pressure/cpu"],
    "psi_memory": ["shell", "cat", "/proc/pressure/memory"],
    "psi_io": ["shell", "cat", "/proc/pressure/io"],
    "perfetto": ["shell", "which", "perfetto"],
    "atrace": ["shell", "which", "atrace"],
    "simpleperf": ["shell", "which", "simpleperf"],
    "gfxinfo": ["shell", "dumpsys", "gfxinfo", "-h"],
    "dexopt_state": ["shell", "dumpsys", "package", "com.anthropic.claude"]
}

results = {}
for k, v in checks.items():
    if k == "dexopt_state":
        out = adb_cmd(v)
        # extract Dexopt state lines
        dex_lines = [l for l in out.splitlines() if "dexopt" in l.lower() or "status=" in l.lower() or "compilation" in l.lower()]
        results[k] = dex_lines[:10]
    elif k == "meminfo":
        out = adb_cmd(v)
        results[k] = "\n".join(out.splitlines()[:8])
    else:
        results[k] = adb_cmd(v)

print(json.dumps(results, indent=2))
