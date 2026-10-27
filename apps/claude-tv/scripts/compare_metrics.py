import json
import statistics

BASE_FILE = str(Path(__file__).resolve().parent / "profiling_raw_results.json")
OPT_FILE = str(Path(__file__).resolve().parent / "profiling_otimizado_results.json")

b = json.load(open(BASE_FILE, encoding="utf-8"))
o = json.load(open(OPT_FILE, encoding="utf-8"))

print("=" * 70)
print("RELATÓRIO COMPARATIVO: BASELINE vs OTIMIZADO NA TV REAL")
print("=" * 70)

# 1. JNI / Broadcast Roundtrip
b_jni = b["jni_benchmark"]["avg_ms"]
o_jni = o["jni_benchmark"]["avg_ms"]
delta_jni = o_jni - b_jni
pct_jni = (delta_jni / b_jni) * 100
print(f"\n1. Latência Roundtrip JNI / Broadcast:")
print(f"   Baseline : {b_jni:.1f} ms")
print(f"   Otimizado: {o_jni:.1f} ms")
print(f"   Delta    : {delta_jni:+.1f} ms ({pct_jni:+.1f}%)")

# 2. Warm Start MainActivity
b_warm = [r['am_start']['total_time'] for r in b['warm_start_main'] if r['am_start']['total_time'] is not None]
o_warm = [r['am_start']['total_time'] for r in o['warm_start_main'] if r['am_start']['total_time'] is not None]
b_warm_avg = statistics.mean(b_warm)
o_warm_avg = statistics.mean(o_warm)
delta_warm = o_warm_avg - b_warm_avg
pct_warm = (delta_warm / b_warm_avg) * 100
print(f"\n2. Warm Start MainActivity:")
print(f"   Baseline : {b_warm_avg:.1f} ms (p50: {statistics.median(b_warm):.1f} ms)")
print(f"   Otimizado: {o_warm_avg:.1f} ms (p50: {statistics.median(o_warm):.1f} ms)")
print(f"   Delta    : {delta_warm:+.1f} ms ({pct_warm:+.1f}%)")

# 3. 1ª Abertura do Overlay (Warm)
b_ov1 = b['overlay_warm_start'][0]['am_start']['total_time']
o_ov1 = o['overlay_warm_start'][0]['am_start']['total_time']
delta_ov1 = o_ov1 - b_ov1
pct_ov1 = (delta_ov1 / b_ov1) * 100
print(f"\n3. Primeira Abertura do Overlay (Warm):")
print(f"   Baseline : {b_ov1} ms")
print(f"   Otimizado: {o_ov1} ms")
print(f"   Delta    : {delta_ov1:+} ms ({pct_ov1:+.1f}%) -> REDUÇÃO DE {b_ov1 - o_ov1} ms!")

# 4. Reaberturas do Overlay
b_ov_re = [r['am_start']['total_time'] for r in b['overlay_warm_start'][1:] if r['am_start']['total_time'] is not None]
o_ov_re = [r['am_start']['total_time'] for r in o['overlay_warm_start'][1:] if r['am_start']['total_time'] is not None]
b_ov_re_avg = statistics.mean(b_ov_re)
o_ov_re_avg = statistics.mean(o_ov_re)
delta_ov_re = o_ov_re_avg - b_ov_re_avg
pct_ov_re = (delta_ov_re / b_ov_re_avg) * 100
print(f"\n4. Reaberturas do Overlay (Cache Ativo):")
print(f"   Baseline : {b_ov_re_avg:.1f} ms (amostras: {b_ov_re})")
print(f"   Otimizado: {o_ov_re_avg:.1f} ms (amostras: {o_ov_re})")
print(f"   Delta    : {delta_ov_re:+.1f} ms ({pct_ov_re:+.1f}%)")

# 5. Cold Start Overlay
b_ov_c = [r['am_start']['total_time'] for r in b['overlay_cold_start'] if r['am_start']['total_time'] is not None]
o_ov_c = [r['am_start']['total_time'] for r in o['overlay_cold_start'] if r['am_start']['total_time'] is not None]
b_ov_c_avg = statistics.mean(b_ov_c)
o_ov_c_avg = statistics.mean(o_ov_c)
delta_ov_c = o_ov_c_avg - b_ov_c_avg
pct_ov_c = (delta_ov_c / b_ov_c_avg) * 100
print(f"\n5. Cold Start do Overlay (Processo Morto):")
print(f"   Baseline : {b_ov_c_avg:.1f} ms (amostras: {b_ov_c})")
print(f"   Otimizado: {o_ov_c_avg:.1f} ms (amostras: {o_ov_c})")
print(f"   Delta    : {delta_ov_c:+.1f} ms ({pct_ov_c:+.1f}%) -> REDUÇÃO DE {b_ov_c_avg - o_ov_c_avg:.1f} ms!")

# 6. Task Switch Resume Time
b_res = [r['resume_time_ms'] for r in b['task_switching']]
o_res = [r['resume_time_ms'] for r in o['task_switching']]
b_res_avg = statistics.mean(b_res)
o_res_avg = statistics.mean(o_res)
delta_res = o_res_avg - b_res_avg
pct_res = (delta_res / b_res_avg) * 100
print(f"\n6. Retomada de Alternância de Tarefas (App Switch):")
print(f"   Baseline : {b_res_avg:.1f} ms")
print(f"   Otimizado: {o_res_avg:.1f} ms")
print(f"   Delta    : {delta_res:+.1f} ms ({pct_res:+.1f}%) -> REDUÇÃO DE {b_res_avg - o_res_avg:.1f} ms!")

# 7. Memória em Alternância de Tarefas (PSS)
b_pss = [r['pss_after_kb']//1024 for r in b['task_switching']]
o_pss = [r['pss_after_kb']//1024 for r in o['task_switching']]
b_pss_avg = statistics.mean(b_pss)
o_pss_avg = statistics.mean(o_pss)
print(f"\n7. Memória PSS em Background (Retenção):")
print(f"   Baseline : {b_pss_avg:.1f} MB")
print(f"   Otimizado: {o_pss_avg:.1f} MB")
print(f"   Delta    : {o_pss_avg - b_pss_avg:+.1f} MB ({(o_pss_avg - b_pss_avg)/b_pss_avg*100:+.1f}%)")

# 8. Jank na Navegação D-Pad
b_jank = [r['gfx']['jank_pct'] for r in b['ui_dpad_navigation'][1:]]
o_jank = [r['gfx']['jank_pct'] for r in o['ui_dpad_navigation'][1:]]
print(f"\n8. Jank Médio na Navegação D-Pad (Amostras 2 a 5):")
print(f"   Baseline : {statistics.mean(b_jank):.2f}%")
print(f"   Otimizado: {statistics.mean(o_jank):.2f}%")

print("=" * 70)
