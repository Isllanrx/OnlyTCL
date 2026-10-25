import subprocess
import time
import json
import re
import os
import sys
import numpy as np
import scipy.stats as stats

ADB = r"E:\Android\Sdk\platform-tools\adb.exe"
DEV = "192.168.76.209:5555"
PKG = "com.anthropic.claude"
MAIN_ACT = f"{PKG}/.mainactivity.MainActivity"

APK_A = r"claude-tv\release\claude-tv-1.260930-20-candidate.apk"
APK_B = r"claude-tv\release\claude-tv-1.260930-20-otimizado.apk"

OUTPUT_JSON = r"claude-tv\scripts\audit_caso2_ab_results.json"

def run_adb(args, timeout=30):
    cmd = [ADB, "-s", DEV] + args
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return res.stdout.strip()
    except Exception as e:
        # Tentar reconectar se der erro
        subprocess.run([ADB, "connect", DEV], capture_output=True, timeout=10)
        return ""

def connect():
    subprocess.run([ADB, "connect", DEV], capture_output=True, timeout=10)
    # Manter tela ligada e desativar screensaver da TV
    run_adb(["shell", "settings", "put", "global", "stay_on_while_plugged_in", "3"])
    run_adb(["shell", "settings", "put", "system", "screen_off_timeout", "3600000"])
    run_adb(["shell", "input", "keyevent", "3"]) # HOME

def ensure_killed():
    run_adb(["shell", "am", "force-stop", PKG])
    run_adb(["shell", "input", "keyevent", "3"]) # HOME
    for _ in range(5):
        pid = run_adb(["shell", "pidof", PKG]).strip()
        if not pid:
            return True
        run_adb(["shell", "kill", "-9", pid])
        time.sleep(0.5)
    return False

def wait_for_idle(cooldown_s=6):
    time.sleep(cooldown_s)
    # Medir CPU usage por 0.5s para confirmar idle
    for _ in range(5):
        s1 = run_adb(["shell", "cat", "/proc/stat"])
        time.sleep(0.5)
        s2 = run_adb(["shell", "cat", "/proc/stat"])
        try:
            p1 = [int(x) for x in s1.splitlines()[0].split()[1:]]
            p2 = [int(x) for x in s2.splitlines()[0].split()[1:]]
            idle = p2[3] - p1[3]
            total = sum(p2) - sum(p1)
            usage = 100.0 * (1.0 - (idle / total))
            if usage < 30.0:
                break
        except Exception:
            break

def install_and_compile(apk_path, label):
    print(f"\n=======================================================")
    print(f"[*] Instalando {label}: {os.path.basename(apk_path)}")
    print(f"=======================================================")
    ensure_killed()
    t0 = time.time()
    res_inst = subprocess.run([ADB, "-s", DEV, "install", "-r", apk_path], capture_output=True, text=True, timeout=60)
    t_inst = time.time() - t0
    print(f"    -> Instalação concluída em {t_inst:.1f}s (Output: {res_inst.stdout.strip()})")

    print(f"[*] Compilando Dexopt AOT (speed)...")
    t1 = time.time()
    res_comp = run_adb(["shell", "cmd", "package", "compile", "-m", "speed", "-f", PKG], timeout=240)
    t_comp = time.time() - t1
    print(f"    -> Compilação speed concluída em {t_comp:.1f}s (Output: {res_comp})")

    # Verificar estado de dexopt
    dump = run_adb(["shell", "dumpsys", "package", PKG])
    is_speed = False
    for l in dump.splitlines():
        if "status=speed" in l:
            is_speed = True
            print(f"    -> Dexopt verificado: {l.strip()}")
            break
    if not is_speed:
        print(f"    [AVISO] Não foi encontrado status=speed no dump do package!")

    print(f"[*] Aguardando 15s de cooldown pós-compilação para estabilizar clock e temperatura...")
    time.sleep(15)

def parse_am_start(raw):
    data = {}
    for line in raw.splitlines():
        if ":" in line:
            parts = line.split(":", 1)
            key = parts[0].strip()
            val = parts[1].strip()
            data[key] = val
    return data

def parse_gc_logcat(raw_log):
    gc_count = 0
    total_pause_ms = 0.0
    for line in raw_log.splitlines():
        if "art" in line.lower() or "dalvikvm" in line.lower():
            if "gc" in line.lower() or "freed" in line.lower() or "concurrent" in line.lower():
                gc_count += 1
                # Procurar tempo de pause (ex: paused 1.234ms ou paused 500us)
                m = re.search(r"paused\s+([\d\.]+)(ms|us)", line)
                if m:
                    val = float(m.group(1))
                    unit = m.group(2)
                    if unit == "us":
                        val /= 1000.0
                    total_pause_ms += val
    return gc_count, total_pause_ms

def measure_one_cold_start(run_id, apk_label):
    ensure_killed()
    wait_for_idle(cooldown_s=6)
    
    run_adb(["shell", "logcat", "-c"])
    run_adb(["shell", "dumpsys", "gfxinfo", PKG, "reset"])
    
    t_before = time.time()
    am_out = run_adb(["shell", "am", "start-activity", "-W", "-n", MAIN_ACT], timeout=20)
    t_after = time.time()
    
    parsed = parse_am_start(am_out)
    total_time_ms = int(parsed.get("TotalTime", 0))
    wait_time_ms = int(parsed.get("WaitTime", 0))
    launch_state = parsed.get("LaunchState", "UNKNOWN")
    
    # Obter PID do processo vivo
    pid = run_adb(["shell", "pidof", PKG]).strip()
    
    minflt = 0
    majflt = 0
    utime = 0
    stime = 0
    if pid:
        stat_raw = run_adb(["shell", f"cat /proc/{pid}/stat"])
        try:
            rparen = stat_raw.rfind(")")
            if rparen != -1:
                after = stat_raw[rparen + 2:].split()
                minflt = int(after[7])
                majflt = int(after[9])
                utime = int(after[11])
                stime = int(after[12])
        except Exception as e:
            pass

    # Obter PSS de memória
    pss_kb = 0
    rss_kb = 0
    swap_kb = 0
    if pid:
        mem_raw = run_adb(["shell", f"dumpsys meminfo {PKG}"])
        for l in mem_raw.splitlines():
            if "TOTAL PSS:" in l:
                # TOTAL PSS:   149941            TOTAL RSS:   245224       TOTAL SWAP PSS:     1399
                m = re.search(r"TOTAL PSS:\s+(\d+)\s+TOTAL RSS:\s+(\d+)\s+TOTAL SWAP PSS:\s+(\d+)", l)
                if m:
                    pss_kb = int(m.group(1))
                    rss_kb = int(m.group(2))
                    swap_kb = int(m.group(3))
                break

    # Obter GC de logcat
    logcat_raw = run_adb(["shell", "logcat", "-d", "-s", "ActivityTaskManager:I", "art:I", "dalvikvm:I"])
    gc_count, gc_pause_ms = parse_gc_logcat(logcat_raw)

    result = {
        "run_id": run_id,
        "variant": apk_label,
        "total_time_ms": total_time_ms,
        "wait_time_ms": wait_time_ms,
        "launch_state": launch_state,
        "pid": pid,
        "page_faults_majflt": majflt,
        "page_faults_minflt": minflt,
        "cpu_utime_ticks": utime,
        "cpu_stime_ticks": stime,
        "mem_pss_kb": pss_kb,
        "mem_rss_kb": rss_kb,
        "mem_swap_kb": swap_kb,
        "gc_count": gc_count,
        "gc_pause_ms": round(gc_pause_ms, 2)
    }
    
    print(f"  [{apk_label} #{run_id:02d}] TotalTime: {total_time_ms} ms | State: {launch_state} | "
          f"MajFlt (Disk I/O): {majflt} | MinFlt: {minflt} | CPU u+s: {utime}+{stime} ticks | "
          f"PSS: {pss_kb // 1024} MB | GC: {gc_count} pauses ({gc_pause_ms:.1f}ms)")
    
    ensure_killed()
    return result

def compute_stats(series):
    arr = np.array(series, dtype=float)
    n = len(arr)
    mean = float(np.mean(arr))
    median = float(np.median(arr))
    std = float(np.std(arr, ddof=1)) if n > 1 else 0.0
    p50 = float(np.percentile(arr, 50))
    p90 = float(np.percentile(arr, 90))
    p95 = float(np.percentile(arr, 95))
    min_v = float(np.min(arr))
    max_v = float(np.max(arr))
    ci95 = float(stats.t.ppf(0.975, df=n - 1) * (std / np.sqrt(n))) if n > 1 and std > 0 else 0.0
    return {
        "n": n,
        "mean": round(mean, 2),
        "median": round(median, 2),
        "std": round(std, 2),
        "p50": round(p50, 2),
        "p90": round(p90, 2),
        "p95": round(p95, 2),
        "min": round(min_v, 2),
        "max": round(max_v, 2),
        "ci95_low": round(mean - ci95, 2),
        "ci95_high": round(mean + ci95, 2)
    }

def main():
    print("=================================================================")
    print(" AUDITORIA RIGOROSA CASO 2: COLD START MAINACTIVITY (A/B TEST)")
    print(" A = Candidate (claude-tv-1.260930-20-candidate.apk)")
    print(" B = Otimizado (claude-tv-1.260930-20-otimizado.apk)")
    print(" Protocolo: 3 Rounds Intercalados x 5 Runs Cada (15 Runs A vs 15 Runs B)")
    print("=================================================================")
    
    connect()
    
    results_A = []
    results_B = []

    # Verificar estado inicial: se A já estiver instalado com status=speed, aproveitamos
    dump = run_adb(["shell", "dumpsys", "package", PKG])
    a_already_ready = "status=speed" in dump
    
    for round_num in range(1, 4):
        print(f"\n=======================================================")
        print(f">>>>> INICIANDO ROUND {round_num}/3 DO PROTOCOLO A/B <<<<<")
        print(f"=======================================================")

        # --- FASE A: Candidate ---
        if round_num == 1 and a_already_ready:
            print("[*] Round 1: Candidate (A) já instalado e compilado com speed. Iniciando testes...")
        else:
            install_and_compile(APK_A, f"Candidate (A) [Round {round_num}]")
        
        for i in range(1, 6):
            run_id = (round_num - 1) * 5 + i
            res = measure_one_cold_start(run_id, "Candidate_A")
            results_A.append(res)
            time.sleep(2)

        # --- FASE B: Otimizado ---
        install_and_compile(APK_B, f"Otimizado (B) [Round {round_num}]")
        for i in range(1, 6):
            run_id = (round_num - 1) * 5 + i
            res = measure_one_cold_start(run_id, "Otimizado_B")
            results_B.append(res)
            time.sleep(2)

    # -------------------------------------------------------------
    # ANÁLISE ESTATÍSTICA E TESTE DE HIPÓTESES
    # -------------------------------------------------------------
    tt_A = [r["total_time_ms"] for r in results_A]
    tt_B = [r["total_time_ms"] for r in results_B]
    
    maj_A = [r["page_faults_majflt"] for r in results_A]
    maj_B = [r["page_faults_majflt"] for r in results_B]

    min_A = [r["page_faults_minflt"] for r in results_A]
    min_B = [r["page_faults_minflt"] for r in results_B]

    cpu_A = [r["cpu_utime_ticks"] + r["cpu_stime_ticks"] for r in results_A]
    cpu_B = [r["cpu_utime_ticks"] + r["cpu_stime_ticks"] for r in results_B]

    pss_A = [r["mem_pss_kb"] for r in results_A]
    pss_B = [r["mem_pss_kb"] for r in results_B]

    stats_tt_A = compute_stats(tt_A)
    stats_tt_B = compute_stats(tt_B)

    # Testes estatísticos
    # Welch's t-test (não assume variâncias iguais)
    t_stat, p_welch = stats.ttest_ind(tt_A, tt_B, equal_var=False)
    # Mann-Whitney U test (não paramétrico)
    u_stat, p_mann = stats.mannwhitneyu(tt_A, tt_B, alternative='two-sided')

    delta_ms = stats_tt_B["mean"] - stats_tt_A["mean"]
    delta_pct = (delta_ms / stats_tt_A["mean"]) * 100.0

    # Veredito formal
    # Critério: se p_welch >= 0.05 e p_mann >= 0.05, não há diferença estatística significativa.
    if p_welch >= 0.05 and p_mann >= 0.05:
        veredicto = "NEUTRO / VARIAÇÃO ESTATÍSTICA"
        justificativa = (
            f"O delta entre Candidate ({stats_tt_A['mean']:.1f} ms) e Otimizado ({stats_tt_B['mean']:.1f} ms) "
            f"é de {delta_ms:+.1f} ms ({delta_pct:+.2f}%), com p-value Welch={p_welch:.4f} e Mann-Whitney={p_mann:.4f} (ambos > 0.05). "
            f"A hipótese nula H0 não é rejeitada. Não existe evidência estatística de regressão no código."
        )
    elif delta_ms > 0:
        veredicto = "REGRESSÃO REAL"
        justificativa = (
            f"Otimizado apresentou tempo superior estatisticamente significante ({delta_ms:+.1f} ms / {delta_pct:+.2f}%), "
            f"com p-value Welch={p_welch:.4f} < 0.05."
        )
    else:
        veredicto = "MELHORIA"
        justificativa = (
            f"Otimizado apresentou tempo inferior estatisticamente significante ({delta_ms:+.1f} ms / {delta_pct:+.2f}%), "
            f"com p-value Welch={p_welch:.4f} < 0.05."
        )

    summary = {
        "protocol": "A/B Intercalado (3 blocos x 5 runs)",
        "sample_size": {"A": len(results_A), "B": len(results_B)},
        "total_time_stats": {
            "Candidate_A": stats_tt_A,
            "Otimizado_B": stats_tt_B,
            "delta_ms": round(delta_ms, 2),
            "delta_pct": round(delta_pct, 2),
            "welch_t_test": {
                "t_statistic": round(float(t_stat), 4),
                "p_value": round(float(p_welch), 4),
                "significant_at_0_05": bool(p_welch < 0.05)
            },
            "mann_whitney_u_test": {
                "u_statistic": round(float(u_stat), 4),
                "p_value": round(float(p_mann), 4),
                "significant_at_0_05": bool(p_mann < 0.05)
            }
        },
        "decomposition_stats": {
            "major_page_faults_io": {
                "Candidate_A": compute_stats(maj_A),
                "Otimizado_B": compute_stats(maj_B)
            },
            "minor_page_faults": {
                "Candidate_A": compute_stats(min_A),
                "Otimizado_B": compute_stats(min_B)
            },
            "cpu_total_ticks": {
                "Candidate_A": compute_stats(cpu_A),
                "Otimizado_B": compute_stats(cpu_B)
            },
            "memory_pss_kb": {
                "Candidate_A": compute_stats(pss_A),
                "Otimizado_B": compute_stats(pss_B)
            }
        },
        "veredicto_final": veredicto,
        "justificativa": justificativa,
        "raw_samples": {
            "Candidate_A": results_A,
            "Otimizado_B": results_B
        }
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print("\n=======================================================")
    print(" RELATÓRIO FINAL DA AUDITORIA DO CASO 2 (COLD START)")
    print("=======================================================")
    print(f"Candidate (A) : Média = {stats_tt_A['mean']} ms | Mediana = {stats_tt_A['median']} ms | DP = {stats_tt_A['std']} ms | IC95% = [{stats_tt_A['ci95_low']}, {stats_tt_A['ci95_high']}]")
    print(f"Otimizado (B) : Média = {stats_tt_B['mean']} ms | Mediana = {stats_tt_B['median']} ms | DP = {stats_tt_B['std']} ms | IC95% = [{stats_tt_B['ci95_low']}, {stats_tt_B['ci95_high']}]")
    print(f"Delta Absoluto: {delta_ms:+.2f} ms ({delta_pct:+.2f}%)")
    print(f"Welch's t-test: t = {t_stat:.4f}, p = {p_welch:.4f} (Significante? {p_welch < 0.05})")
    print(f"Mann-Whitney U: U = {u_stat:.4f}, p = {p_mann:.4f} (Significante? {p_mann < 0.05})")
    print(f"\nVEREDITO FORMAL: {veredicto}")
    print(f"JUSTIFICATIVA  : {justificativa}")
    print(f"Arquivo de resultados salvo em: {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
