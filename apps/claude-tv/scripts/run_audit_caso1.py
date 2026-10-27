import subprocess
import time
import json
import statistics
from audit_caso1_core import (
    adb, run_single_key219_test, compute_deltas, PKG, MAIN_ACT, OVERLAY_ACT
)

OUTPUT_FILE = str(Path(__file__).resolve().parent / "audit_caso1_results.json")

results = {
    "scenario_A_cold_process": [],
    "scenario_B_warm_process": [],
    "scenario_C_D_first_vs_subsequent": [],
    "scenario_E_F_overlay_state": []
}

print("=" * 70)
print("AUDITORIA EMPÍRICA CASO 1: KEYCODE 219 (T0 -> T7)")
print("=" * 70)

# -----------------------------------------------------------------
# CENÁRIO A: Processo Claude Morto / Cold (10 Amostras)
# -----------------------------------------------------------------
print("\n--- [CENÁRIO A] Processo Claude Morto (Force-Stop) - 10 Execuções ---")
for i in range(10):
    print(f"  > Execução {i+1}/10...")
    adb(["shell", "am", "force-stop", PKG])
    time.sleep(2)
    # Garante Home
    adb(["shell", "input", "keyevent", "3"])
    time.sleep(1)
    
    res = run_single_key219_test()
    deltas = compute_deltas(res)
    res["deltas"] = deltas
    results["scenario_A_cold_process"].append(res)
    print(f"    T0->T4 (Input->START): {deltas.get('T0_T4_ms', 'N/A')} ms | T4->T7 (START->Disp): {deltas.get('T4_T7_ms', 'N/A')} ms | Total T0->T7: {deltas.get('T0_T7_total_ms', 'N/A')} ms")

# -----------------------------------------------------------------
# CENÁRIO B: Processo Claude Residente / Warm (10 Amostras)
# -----------------------------------------------------------------
print("\n--- [CENÁRIO B] Processo Claude Residente / Warm - 10 Execuções ---")
# Iniciar Claude primeiro para garantir processo residente
adb(["shell", "am", "start-activity", "-W", "-n", MAIN_ACT])
time.sleep(3)
adb(["shell", "input", "keyevent", "3"]) # Home
time.sleep(2)

for i in range(10):
    print(f"  > Execução {i+1}/10...")
    res = run_single_key219_test()
    deltas = compute_deltas(res)
    res["deltas"] = deltas
    results["scenario_B_warm_process"].append(res)
    print(f"    T0->T4 (Input->START): {deltas.get('T0_T4_ms', 'N/A')} ms | T4->T7 (START->Disp): {deltas.get('T4_T7_ms', 'N/A')} ms | Total T0->T7: {deltas.get('T0_T7_total_ms', 'N/A')} ms")

# Salvar resultados brutos
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\nResultados brutos gravados em: {OUTPUT_FILE}")
