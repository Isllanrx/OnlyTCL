import re
import json

TRACE_FILE = r"E:\projeto_twitchlit\claude-tv\scripts\overlay_atrace.txt"

print("Analisando trace do overlay...")

claude_pid = None
# Encontrar PID do Claude no trace
with open(TRACE_FILE, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        if "com.anthropic.claude" in line:
            # ex: <...>-2121  ( 2121) [002] ...: ...
            m = re.search(r"-(\d+)\s+\(\s*(\d+)\)", line)
            if m:
                claude_pid = m.group(2)
                print(f"Detectado PID do Claude no trace: {claude_pid}")
                break

if not claude_pid:
    print("PID do Claude nao encontrado pelo nome do processo, procurando por pacote...")
    with open(TRACE_FILE, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if "anthropic" in line:
                print("Linha:", line[:120])
                break

slices = {}
binder_calls = []
sched_runnable_ns = 0
sched_running_ns = 0

# Expressao para rastrear começo e fim de slices Atrace:
# B|pid|nome_do_slice
# E|pid
slice_stack = {} # tid -> [(name, start_ts)]

with open(TRACE_FILE, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        # 1. Binder transactions
        if "binder_transaction" in line and (claude_pid and claude_pid in line):
            binder_calls.append(line.strip())
            
        # 2. Atrace slices
        # formato: task-pid [cpu] ts: tracing_mark_write: B|pid|name ou E|pid
        if "tracing_mark_write:" in line:
            m_ts = re.search(r"(\d+\.\d+): tracing_mark_write:\s*([BE])\|(\d+)(?:\|(.*))?", line)
            if m_ts:
                ts = float(m_ts.group(1))
                action = m_ts.group(2)
                pid = m_ts.group(3)
                
                if claude_pid and pid != claude_pid:
                    continue
                    
                tid_match = re.search(r"-(\d+)\s+\[", line)
                tid = tid_match.group(1) if tid_match else pid
                
                if action == "B":
                    name = m_ts.group(4) if m_ts.group(4) else "unknown"
                    if tid not in slice_stack:
                        slice_stack[tid] = []
                    slice_stack[tid].append((name, ts))
                elif action == "E":
                    if tid in slice_stack and slice_stack[tid]:
                        name, start_ts = slice_stack[tid].pop()
                        duration_ms = (ts - start_ts) * 1000.0
                        if name not in slices:
                            slices[name] = {"count": 0, "total_ms": 0.0, "max_ms": 0.0}
                        slices[name]["count"] += 1
                        slices[name]["total_ms"] += duration_ms
                        if duration_ms > slices[name]["max_ms"]:
                            slices[name]["max_ms"] = duration_ms

print(f"\nTop 25 Slices mais demorados dentro do processo Claude (PID {claude_pid}):")
sorted_slices = sorted(slices.items(), key=lambda x: x[1]["total_ms"], reverse=True)
for name, data in sorted_slices[:25]:
    avg = data["total_ms"] / data["count"] if data["count"] > 0 else 0
    print(f"  {name[:45]:<45} | Total: {data['total_ms']:>8.2f} ms | Max: {data['max_ms']:>7.2f} ms | Count: {data['count']:>4} | Avg: {avg:>6.2f} ms")

print(f"\nTotal de transacoes Binder registradas do Claude: {len(binder_calls)}")
