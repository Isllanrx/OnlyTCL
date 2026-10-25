"""Capture Android logs, remote input events, and Claude CPU/memory samples."""
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time

ADB = r"E:\Android\Sdk\platform-tools\adb.exe"
TV = "192.168.76.209:5555"
PACKAGE = "com.anthropic.claude"
SAMPLE_SECONDS = 5


def require_device():
    subprocess.run([ADB, "connect", TV], capture_output=True, text=True, timeout=10)
    result = subprocess.run(
        [ADB, "-s", TV, "get-state"], capture_output=True, text=True, timeout=10
    )
    if result.returncode or result.stdout.strip() != "device":
        raise RuntimeError(f"TV indisponível: {result.stdout.strip()} {result.stderr.strip()}")


def stream_to_file(command, destination, label):
    with destination.open("w", encoding="utf-8", errors="replace") as output:
        output.write(f"Capture started: {datetime.now().astimezone().isoformat()}\n")
        output.flush()
        proc = subprocess.Popen(
            command, stdout=output, stderr=subprocess.STDOUT, text=True, bufsize=1
        )
        print(f"[{label}] PID local {proc.pid}; arquivo {destination}", flush=True)
        return proc


def main():
    require_device()
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    if len(sys.argv) > 1:
        out_dir = Path(sys.argv[1])
    else:
        out_dir = Path(__file__).resolve().parent.parent / "logs" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    logcat = stream_to_file(
        [ADB, "-s", TV, "logcat", "-b", "all", "-v", "threadtime", "-T", "1"],
        out_dir / "logcat-all.txt",
        "LOGCAT",
    )
    input_events = stream_to_file(
        [ADB, "-s", TV, "shell", "getevent", "-lt"],
        out_dir / "remote-input.txt",
        "INPUT",
    )
    telemetry_path = out_dir / "telemetry.txt"
    print(f"[READY] Captura passiva ativa. Dados em {out_dir}", flush=True)
    print("[READY] Inicie seu teste na TV; pare o monitor com Ctrl+C nesta sessão.", flush=True)

    try:
        with telemetry_path.open("w", encoding="utf-8") as telemetry:
            while True:
                if logcat.poll() is not None:
                    raise RuntimeError("O stream do logcat encerrou inesperadamente.")
                now = datetime.now().astimezone().isoformat()
                telemetry.write(f"\n===== {now} =====\n")
                for label, args in (
                    ("CPU", ["shell", "dumpsys", "cpuinfo"]),
                    ("MEMORY", ["shell", "dumpsys", "meminfo", PACKAGE]),
                ):
                    result = subprocess.run(
                        [ADB, "-s", TV, *args],
                        capture_output=True,
                        text=True,
                        timeout=15,
                    )
                    telemetry.write(f"--- {label} rc={result.returncode} ---\n")
                    telemetry.write(result.stdout)
                    if result.stderr:
                        telemetry.write(f"\nSTDERR: {result.stderr}")
                    telemetry.write("\n")
                telemetry.flush()
                print(f"[SAMPLE] {now} CPU e memória coletados", flush=True)
                time.sleep(SAMPLE_SECONDS)
    except KeyboardInterrupt:
        print("[STOP] Encerrando captura...", flush=True)
    finally:
        for proc in (logcat, input_events):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        print(f"[DONE] Capturas salvas em {out_dir}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
