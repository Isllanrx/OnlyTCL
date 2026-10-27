import re

TRACE_FILE = str(Path(__file__).resolve().parent / "overlay_atrace.txt")

print("Calculando tempo de CPU e agendamento dos threads do Claude (TGID 2121)...")

# Dicionario para rastrear estado de cada thread:
# tid -> {"comm": str, "state": "running"/"runnable"/"sleeping", "last_state_ts": float, "running_ms": float, "runnable_ms": float}
threads = {}

sched_switch_re = re.compile(r"(\d+\.\d+):\s+sched_switch:\s+prev_comm=(.*?)\s+prev_pid=(\d+)\s+prev_prio=\d+\s+prev_state=(\S+)\s+==>\s+next_comm=(.*?)\s+next_pid=(\d+)")
sched_wakeup_re = re.compile(r"(\d+\.\d+):\s+sched_wakeup:\s+comm=(.*?)\s+pid=(\d+)")

with open(TRACE_FILE, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        # Check sched_wakeup
        m_wake = sched_wakeup_re.search(line)
        if m_wake:
            ts = float(m_wake.group(1))
            comm = m_wake.group(2)
            pid = m_wake.group(3)
            
            if pid not in threads:
                threads[pid] = {"comm": comm, "state": "runnable", "last_ts": ts, "running_ms": 0.0, "runnable_ms": 0.0}
            else:
                threads[pid]["comm"] = comm
                threads[pid]["state"] = "runnable"
                threads[pid]["last_ts"] = ts
            continue
            
        # Check sched_switch
        m_sw = sched_switch_re.search(line)
        if m_sw:
            ts = float(m_sw.group(1))
            prev_comm = m_sw.group(2)
            prev_pid = m_sw.group(3)
            prev_state = m_sw.group(4)
            next_comm = m_sw.group(5)
            next_pid = m_sw.group(6)
            
            # Atualizar prev_pid (que estava executando)
            if prev_pid in threads:
                t = threads[prev_pid]
                if t["state"] == "running":
                    t["running_ms"] += (ts - t["last_ts"]) * 1000.0
                t["comm"] = prev_comm
                t["state"] = "runnable" if prev_state.startswith("R") else "sleeping"
                t["last_ts"] = ts
                
            # Atualizar next_pid (que vai comecar a executar)
            if next_pid in threads:
                t = threads[next_pid]
                if t["state"] == "runnable":
                    t["runnable_ms"] += (ts - t["last_ts"]) * 1000.0
                t["comm"] = next_comm
                t["state"] = "running"
                t["last_ts"] = ts

# Filtrar apenas threads que acumularam tempo relevante (> 10 ms)
sorted_threads = sorted(threads.items(), key=lambda x: x[1]["running_ms"] + x[1]["runnable_ms"], reverse=True)

print(f"\nTop Threads por consumo de CPU e Fila de Espera (Runnable Delay):")
print(f"{'TID':<8} | {'COMM':<22} | {'Running (CPU) ms':>16} | {'Runnable (Fila) ms':>18} | {'Proporção Fila/CPU'}")
print("-" * 80)
for tid, data in sorted_threads[:30]:
    ratio = data["runnable_ms"] / data["running_ms"] if data["running_ms"] > 0 else 0
    print(f"{tid:<8} | {data['comm'][:22]:<22} | {data['running_ms']:>16.2f} | {data['runnable_ms']:>18.2f} | {ratio:>15.2f}x")
