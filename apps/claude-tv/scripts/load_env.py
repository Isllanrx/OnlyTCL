import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent

def load_env():
    env_paths = [
        REPO_ROOT / ".env",
        SCRIPT_DIR / ".env",
        REPO_ROOT / "exemplo.env",
    ]
    for env_path in env_paths:
        if env_path.is_file():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
            break

    if "TV_IP" not in os.environ:
        os.environ["TV_IP"] = "192.168.1.100"
    if "TV_PORT" not in os.environ:
        os.environ["TV_PORT"] = "5555"
    if "TV_DEVICE" not in os.environ:
        os.environ["TV_DEVICE"] = f"{os.environ['TV_IP']}:{os.environ['TV_PORT']}"
    if "PROJECT_ROOT" not in os.environ:
        os.environ["PROJECT_ROOT"] = str(REPO_ROOT)
    if "OUTPUT_DIR" not in os.environ:
        os.environ["OUTPUT_DIR"] = str(REPO_ROOT / "output")
    if "ADB_PATH" not in os.environ:
        sdk = os.environ.get("ANDROID_HOME", os.environ.get("ANDROID_SDK_ROOT"))
        if sdk and (Path(sdk) / "platform-tools" / "adb.exe").is_file():
            os.environ["ADB_PATH"] = str(Path(sdk) / "platform-tools" / "adb.exe")
        else:
            os.environ["ADB_PATH"] = "adb"

load_env()

TV_IP = os.environ["TV_IP"]
TV_PORT = os.environ["TV_PORT"]
TV_DEVICE = os.environ["TV_DEVICE"]
DEVICE = TV_DEVICE
TV = TV_DEVICE
DEV = TV_DEVICE
ADB = os.environ["ADB_PATH"]
PROJECT_ROOT = Path(os.environ["PROJECT_ROOT"])
OUTPUT_DIR = Path(os.environ["OUTPUT_DIR"])
