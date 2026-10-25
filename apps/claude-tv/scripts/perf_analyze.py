"""Decompõe um trace Perfetto do Claude na TV. Uso: python perf_analyze.py <trace.pftrace> [--window-s N]

Imprime: estados da thread principal, fatias mais longas (main e RenderThread), binder síncrono,
GC, CPU por processo na janela, swap/faltas de página e o caminho da abertura (bindApplication → 1º quadro).
Ver .claude/skills/claude-tv-perf/SKILL.md.
"""
from __future__ import annotations

import sys
from perfetto.trace_processor import TraceProcessor

PKG = "com.anthropic.claude"


def q(tp: TraceProcessor, sql: str) -> list:
    return list(tp.query(sql))


def ms(ns: float | None) -> str:
    return "-" if ns is None else f"{ns / 1e6:.1f}"


def main(path: str) -> None:
    tp = TraceProcessor(trace=path)
    tp.query("INCLUDE PERFETTO MODULE android.binder")
    procs = q(tp, f"select upid, pid from process where name = '{PKG}' order by start_ts desc")
    if not procs:
        print("processo do Claude não encontrado no trace")
        return
    upid = procs[0].upid
    span = q(tp, "select start_ts, end_ts from trace_bounds")[0]
    t0, t1 = span.start_ts, span.end_ts
    main_utid = q(tp, f"select utid from thread where upid={upid} and is_main_thread=1")
    main_utid = main_utid[0].utid if main_utid else q(tp, f"select utid from thread where tid={procs[0].pid}")[0].utid
    rt = q(tp, f"select utid from thread where upid={upid} and name='RenderThread'")
    rt_utid = rt[0].utid if rt else None
    print(f"trace {ms(t1 - t0)} ms; pid {procs[0].pid}")

    print("\n## Thread principal: estados (ms)")
    for r in q(tp, f"""select state, sum(dur) d, count(*) n from thread_state
                     where utid={main_utid} group by state order by d desc"""):
        print(f"  {r.state:<4} {ms(r.d):>9}  ({r.n} intervalos)")
    for r in q(tp, f"""select blocked_function f, sum(dur) d, count(*) n from thread_state
                     where utid={main_utid} and state in ('D','DK') and blocked_function is not null
                     group by f order by d desc limit 8"""):
        print(f"  D em {r.f}: {ms(r.d)} ms ({r.n})")

    print("\n## Abertura: marcos na thread principal")
    for name in ("bindApplication", "activityStart", "activityResume", "Choreographer#doFrame",
                 "inflate", "ResourcesManager#getResources", "OpenDexFilesFromOat*", "Lock contention*"):
        r = q(tp, f"""select min(s.ts) ts, sum(s.dur) d, count(*) n from slice s join thread_track tt on s.track_id=tt.id
                    where tt.utid={main_utid} and s.name glob '{name}'""")[0]
        if r.n:
            print(f"  {name:<34} 1º em +{ms(r.ts - t0):>8} ms  total {ms(r.d):>8} ms  n={r.n}")

    print("\n## Thread principal: 25 fatias mais longas (depth 0..2)")
    for r in q(tp, f"""select s.name, s.dur, s.ts, s.depth from slice s join thread_track tt on s.track_id=tt.id
                     where tt.utid={main_utid} and s.depth<=2 order by s.dur desc limit 25"""):
        print(f"  {ms(r.dur):>8} ms  +{ms(r.ts - t0):>8}  d{r.depth}  {r.name[:110]}")

    print("\n## Thread principal: tempo por nome de fatia (top 20, depth>=1)")
    for r in q(tp, f"""select s.name n, sum(s.dur) d, count(*) c, max(s.dur) m from slice s join thread_track tt on s.track_id=tt.id
                     where tt.utid={main_utid} and s.depth>=1 group by s.name order by d desc limit 20"""):
        print(f"  {ms(r.d):>8} ms  n={r.c:<5} máx {ms(r.m):>7}  {r.n[:100]}")

    if rt_utid is not None:
        print("\n## RenderThread: tempo por fatia (top 15)")
        for r in q(tp, f"""select s.name n, sum(s.dur) d, count(*) c, max(s.dur) m from slice s join thread_track tt on s.track_id=tt.id
                         where tt.utid={rt_utid} group by s.name order by d desc limit 15"""):
            print(f"  {ms(r.d):>8} ms  n={r.c:<5} máx {ms(r.m):>7}  {r.n[:100]}")
        for r in q(tp, f"""select state, sum(dur) d from thread_state where utid={rt_utid} group by state order by d desc"""):
            print(f"  estado {r.state:<4} {ms(r.d)} ms")

    print("\n## Binder síncrono saindo da thread principal (top 12)")
    for r in q(tp, f"""select coalesce(p.name,'?') dst, count(*) n, sum(b.client_dur) d, max(b.client_dur) m
                     from android_binder_txns b left join process p on p.upid=b.server_upid
                     where b.client_utid={main_utid} and b.is_sync group by dst order by d desc limit 12"""):
        print(f"  {ms(r.d):>8} ms  n={r.n:<4} máx {ms(r.m):>7}  -> {r.dst}")

    print("\n## Threads do app por CPU (top 15)")
    for r in q(tp, f"""select t.name n, sum(ss.dur) d from sched_slice ss join thread t using(utid)
                     where t.upid={upid} group by t.utid order by d desc limit 15"""):
        print(f"  {ms(r.d):>8} ms  {r.n}")

    print("\n## Processos por CPU na janela (top 15)")
    for r in q(tp, """select coalesce(p.name, t.name) n, sum(ss.dur) d from sched_slice ss join thread t using(utid)
                    left join process p using(upid) where ss.utid != 0 group by n order by d desc limit 15"""):
        print(f"  {ms(r.d):>8} ms  {r.n}")

    print("\n## Memória do sistema (início -> fim)")
    for name in ("mem.available", "mem.swap.free", "vmstat.pgmajfault", "vmstat.pswpin", "vmstat.pswpout"):
        r = q(tp, f"""select min(c.ts) a, max(c.ts) b from counter c join counter_track t on c.track_id=t.id where t.name='{name}'""")[0]
        if r.a is None:
            continue
        v = q(tp, f"""select (select value from counter c join counter_track t on c.track_id=t.id where t.name='{name}' order by ts limit 1) v0,
                             (select value from counter c join counter_track t on c.track_id=t.id where t.name='{name}' order by ts desc limit 1) v1""")[0]
        scale = 1 / 1048576 if name.startswith("mem.") else 1
        print(f"  {name:<20} {v.v0 * scale:,.0f} -> {v.v1 * scale:,.0f}{' MB' if scale != 1 else ''}")

    print("\n## GC e JIT do app")
    for r in q(tp, f"""select s.name n, count(*) c, sum(s.dur) d from slice s join thread_track tt on s.track_id=tt.id
                     join thread t using(utid) where t.upid={upid} and (s.name glob '*GC*' or s.name glob 'JIT*' or s.name glob '*Compil*')
                     group by s.name order by d desc limit 10"""):
        print(f"  {ms(r.d):>8} ms  n={r.c:<4} {r.n[:90]}")


if __name__ == "__main__":
    main(sys.argv[1])
