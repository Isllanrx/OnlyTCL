import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import subprocess
import os
import sys
from pathlib import Path

from load_env import ADB, DEVICE, TV, DEV, PROJECT_ROOT, OUTPUT_DIR
# TV loaded from load_env
OUT_BASE = OUTPUT_DIR / "tv_system_dump"

def adb_cmd(*args):
    return subprocess.run([ADB, "-s", TV, *args], capture_output=True, text=True, timeout=30)

def adb_pull(remote, local):
    local.parent.mkdir(parents=True, exist_ok=True)
    res = subprocess.run([ADB, "-s", TV, "pull", remote, str(local)], capture_output=True, text=True, timeout=60)
    return res.returncode == 0

def main():
    print(f"=== Conectando à TV {TV} ===")
    subprocess.run([ADB, "connect", TV], timeout=10)

    # 1. Media Codecs XMLs
    print("\n=== 1. Buscando e extraindo media_codecs.xml e media_codecs_performance.xml ===")
    codecs_dir = OUT_BASE / "codecs"
    codecs_dir.mkdir(parents=True, exist_ok=True)

    find_codecs = adb_cmd("shell", "find /etc /vendor/etc /system/etc /odm/etc -name '*media_codecs*' 2>/dev/null")
    codec_paths = [p.strip() for p in find_codecs.stdout.splitlines() if p.strip()]
    print(f"Encontrados {len(codec_paths)} arquivos de configuração de codecs:")
    for cp in codec_paths:
        dest_name = cp.replace("/", "_").lstrip("_")
        dest = codecs_dir / dest_name
        if adb_pull(cp, dest):
            print(f"  [OK] {cp} -> {dest.name} ({dest.stat().st_size} bytes)")
        else:
            print(f"  [FALHA] {cp}")

    # 2. com.tcl.tvmanager & Frameworks TCL
    print("\n=== 2. Buscando arquivos/JARs/APKs de com.tcl.tvmanager e frameworks TCL ===")
    tcl_dir = OUT_BASE / "tcl_tvmanager"
    tcl_dir.mkdir(parents=True, exist_ok=True)

    pm_path = adb_cmd("shell", "pm path com.tcl.tvmanager 2>/dev/null")
    print(f"pm path com.tcl.tvmanager: {pm_path.stdout.strip()}")
    for line in pm_path.stdout.splitlines():
        if line.startswith("package:"):
            apk_remote = line.replace("package:", "").strip()
            dest = tcl_dir / Path(apk_remote).name
            if adb_pull(apk_remote, dest):
                print(f"  [OK APK] {apk_remote} -> {dest.name}")

    find_tcl = adb_cmd("shell", "find /system /vendor /product /system_ext -name '*tvmanager*' -o -name '*tcl*framework*' -o -name '*tcl*manager*' 2>/dev/null")
    tcl_files = [p.strip() for p in find_tcl.stdout.splitlines() if p.strip() and (p.endswith('.jar') or p.endswith('.apk') or p.endswith('.so'))]
    print(f"Encontrados {len(tcl_files)} binários/JARs do ecossistema TCL:")
    for tf in tcl_files:
        dest = tcl_dir / Path(tf).name
        if not dest.exists():
            if adb_pull(tf, dest):
                print(f"  [OK] {tf} -> {dest.name} ({dest.stat().st_size} bytes)")

    # 3. Bibliotecas Realtek em /vendor/lib e /vendor/lib64
    print("\n=== 3. Buscando bibliotecas Realtek em /vendor/lib e /vendor/lib64 ===")
    vlibs_dir = OUT_BASE / "vendor_libs"
    vlibs_dir.mkdir(parents=True, exist_ok=True)

    patterns = ["rtk", "realtek", "vdec", "codec", "omx", "media", "hwc"]
    find_cmd = "find /vendor/lib /vendor/lib64 -type f -name '*.so' 2>/dev/null"
    res_libs = adb_cmd("shell", find_cmd)
    candidate_libs = []
    for line in res_libs.stdout.splitlines():
        line = line.strip()
        name_lower = Path(line).name.lower()
        if any(p in name_lower for p in patterns):
            candidate_libs.append(line)

    print(f"Encontradas {len(candidate_libs)} bibliotecas candidatas Realtek/Media/HWC:")
    for lib in candidate_libs:
        sub = "lib64" if "/lib64" in lib else "lib"
        target_dir = vlibs_dir / sub
        target_dir.mkdir(parents=True, exist_ok=True)
        dest = target_dir / Path(lib).name
        if adb_pull(lib, dest):
            print(f"  [OK] [{sub}] {Path(lib).name} ({dest.stat().st_size} bytes)")

    # 4. Outputs de runtime: dumpsys media.codec e dumpsys SurfaceFlinger
    print("\n=== 4. Coletando dumps de runtime (dumpsys media.codec e dumpsys SurfaceFlinger) ===")
    dumps_dir = OUT_BASE / "dumps"
    dumps_dir.mkdir(parents=True, exist_ok=True)

    for svc in ["media.codec", "SurfaceFlinger"]:
        out_file = dumps_dir / f"dumpsys_{svc.replace('.', '_')}.txt"
        print(f"Coletando dumpsys {svc}...")
        res = adb_cmd("shell", f"dumpsys {svc}")
        with open(out_file, "w", encoding="utf-8", errors="replace") as f:
            f.write(res.stdout)
        print(f"  [OK] dumpsys {svc} salvo em {out_file.name} ({out_file.stat().st_size} bytes)")

    print(f"\n[SUCESSO] Todos os backups foram concluídos com sucesso em {OUT_BASE}!")

if __name__ == "__main__":
    main()
