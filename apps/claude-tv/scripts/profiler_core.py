import subprocess
import time
import json
import re
import os
import statistics

ADB = r"E:\Android\Sdk\platform-tools\adb.exe"
DEVICE = "192.168.76.209:5555"
PKG = "com.anthropic.claude"
MAIN_ACT = "com.anthropic.claude/.mainactivity.MainActivity"
OVERLAY_ACT = "com.anthropic.claude/.mainactivity.AssistantOverlayActivity"

def run_adb(args, timeout=25):
    full_cmd = [ADB, "-s", DEVICE] + args
    try:
        res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return res.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def connect():
    subprocess.run([ADB, "connect", DEVICE], capture_output=True, text=True)

def force_stop():
    run_adb(["shell", "am", "force-stop", PKG])
    time.sleep(1)

def go_home():
    run_adb(["shell", "input", "keyevent", "3"]) # KEYCODE_HOME
    time.sleep(2)

def clear_logcat():
    run_adb(["logcat", "-c"])

def get_pid():
    out = run_adb(["shell", "pidof", PKG])
    pids = out.split()
    return int(pids[0]) if pids else None

def get_meminfo():
    out = run_adb(["shell", "dumpsys", "meminfo", PKG])
    data = {}
    for line in out.splitlines():
        line_str = line.strip()
        if "TOTAL PSS:" in line:
            # TOTAL PSS:   174531            TOTAL RSS:   262632       TOTAL SWAP PSS:     1393
            m = re.search(r"TOTAL PSS:\s+(\d+)\s+TOTAL RSS:\s+(\d+)\s+TOTAL SWAP PSS:\s+(\d+)", line)
            if m:
                data["total_pss_kb"] = int(m.group(1))
                data["total_rss_kb"] = int(m.group(2))
                data["swap_pss_kb"] = int(m.group(3))
        elif "Java Heap:" in line_str and "Pss" not in line_str:
            m = re.findall(r"\d+", line_str)
            if m: data["java_heap_pss_kb"] = int(m[0])
        elif "Native Heap:" in line_str and "Pss" not in line_str:
            m = re.findall(r"\d+", line_str)
            if m: data["native_heap_pss_kb"] = int(m[0])
        elif "Code:" in line_str:
            m = re.findall(r"\d+", line_str)
            if m: data["code_pss_kb"] = int(m[0])
        elif "Graphics:" in line_str:
            m = re.findall(r"\d+", line_str)
            if m: data["graphics_pss_kb"] = int(m[0])
    return data

def parse_gfxinfo(out):
    data = {
        "total_frames": 0, "janky_frames": 0, "jank_pct": 0.0,
        "p50_ms": 0, "p90_ms": 0, "p95_ms": 0, "p99_ms": 0,
        "slow_ui_thread": 0, "slow_draw_cmds": 0, "missed_vsync": 0,
        "high_input_lat": 0, "deadline_missed": 0, "gpu_p50_ms": 0, "gpu_p90_ms": 0
    }
    for line in out.splitlines():
        l = line.strip()
        if "Total frames rendered:" in l:
            m = re.search(r"Total frames rendered:\s+(\d+)", l)
            if m: data["total_frames"] = int(m.group(1))
        elif "Janky frames:" in l:
            m = re.search(r"Janky frames:\s+(\d+)\s+\(([\d\.]+)%\)", l)
            if m:
                data["janky_frames"] = int(m.group(1))
                data["jank_pct"] = float(m.group(2))
        elif "50th percentile:" in l:
            m = re.search(r"50th percentile:\s+(\d+)ms", l)
            if m: data["p50_ms"] = int(m.group(1))
        elif "90th percentile:" in l:
            m = re.search(r"90th percentile:\s+(\d+)ms", l)
            if m: data["p90_ms"] = int(m.group(1))
        elif "95th percentile:" in l:
            m = re.search(r"95th percentile:\s+(\d+)ms", l)
            if m: data["p95_ms"] = int(m.group(1))
        elif "99th percentile:" in l:
            m = re.search(r"99th percentile:\s+(\d+)ms", l)
            if m: data["p99_ms"] = int(m.group(1))
        elif "50th gpu percentile:" in l:
            m = re.search(r"50th gpu percentile:\s+(\d+)ms", l)
            if m: data["gpu_p50_ms"] = int(m.group(1))
        elif "90th gpu percentile:" in l:
            m = re.search(r"90th gpu percentile:\s+(\d+)ms", l)
            if m: data["gpu_p90_ms"] = int(m.group(1))
        elif "Number Slow UI thread:" in l:
            m = re.search(r"Number Slow UI thread:\s+(\d+)", l)
            if m: data["slow_ui_thread"] = int(m.group(1))
        elif "Number Slow issue draw commands:" in l:
            m = re.search(r"Number Slow issue draw commands:\s+(\d+)", l)
            if m: data["slow_draw_cmds"] = int(m.group(1))
        elif "Number Missed Vsync:" in l:
            m = re.search(r"Number Missed Vsync:\s+(\d+)", l)
            if m: data["missed_vsync"] = int(m.group(1))
        elif "Number High input latency:" in l:
            m = re.search(r"Number High input latency:\s+(\d+)", l)
            if m: data["high_input_lat"] = int(m.group(1))
        elif "Number Frame deadline missed:" in l:
            m = re.search(r"Number Frame deadline missed:\s+(\d+)", l)
            if m: data["deadline_missed"] = int(m.group(1))
    return data

def reset_gfxinfo():
    run_adb(["shell", "dumpsys", "gfxinfo", PKG, "reset"])

def get_gfxinfo():
    out = run_adb(["shell", "dumpsys", "gfxinfo", PKG])
    return parse_gfxinfo(out)

def parse_am_start(out):
    res = {"this_time": None, "total_time": None, "wait_time": None, "launch_state": "UNKNOWN"}
    for line in out.splitlines():
        l = line.strip()
        if l.startswith("ThisTime:"):
            res["this_time"] = int(l.split(":")[1].strip())
        elif l.startswith("TotalTime:"):
            res["total_time"] = int(l.split(":")[1].strip())
        elif l.startswith("WaitTime:"):
            res["wait_time"] = int(l.split(":")[1].strip())
        elif l.startswith("LaunchState:"):
            res["launch_state"] = l.split(":")[1].strip()
    return res

def parse_davey_and_gc(log_lines):
    daveys = []
    gcs = []
    choreographer_skipped = []
    
    for line in log_lines:
        if "Davey! duration=" in line:
            m = re.search(r"duration=(\d+)ms;.*IntendedVsync=(\d+), Vsync=(\d+).*HandleInputStart=(\d+), AnimationStart=(\d+), PerformTraversalsStart=(\d+), DrawStart=(\d+), SyncQueued=(\d+), SyncStart=(\d+), IssueDrawCommandsStart=(\d+), SwapBuffers=(\d+), FrameCompleted=(\d+)", line)
            if m:
                d = {
                    "duration_ms": int(m.group(1)),
                    "intended_vsync": int(m.group(2)),
                    "vsync": int(m.group(3)),
                    "handle_input": int(m.group(4)),
                    "anim_start": int(m.group(5)),
                    "traversals_start": int(m.group(6)),
                    "draw_start": int(m.group(7)),
                    "sync_queued": int(m.group(8)),
                    "sync_start": int(m.group(9)),
                    "issue_draw_cmds": int(m.group(10)),
                    "swap_buffers": int(m.group(11)),
                    "frame_completed": int(m.group(12)),
                }
                # derived breakdown in ms
                d["vsync_delay_ms"] = (d["vsync"] - d["intended_vsync"]) / 1e6
                d["ui_traversal_ms"] = (d["sync_queued"] - d["traversals_start"]) / 1e6
                d["renderthread_sync_ms"] = (d["issue_draw_cmds"] - d["sync_start"]) / 1e6
                d["renderthread_draw_ms"] = (d["swap_buffers"] - d["issue_draw_cmds"]) / 1e6
                d["swap_to_complete_ms"] = (d["frame_completed"] - d["swap_buffers"]) / 1e6
                daveys.append(d)
        elif "Skipped" in line and "frames!" in line:
            m = re.search(r"Skipped (\d+) frames!", line)
            if m:
                choreographer_skipped.append(int(m.group(1)))
        elif "art" in line.lower() and ("gc" in line.lower() or "pause" in line.lower()):
            gcs.append(line.strip())
            
    return {
        "daveys": daveys,
        "gcs": gcs,
        "skipped_frames": choreographer_skipped
    }

print("Profiler helper module loaded successfully.")
