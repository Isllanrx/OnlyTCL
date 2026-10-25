#!/usr/bin/env python3
"""Valida o candidato local contra Android 11/ARMv7, sem acessar dispositivos."""
from __future__ import annotations

import argparse
import re
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def audit_helper_api(root: Path, api_versions: Path) -> None:
    classes = {item.attrib["name"]: item for item in ET.parse(api_versions).getroot().findall("class")}

    def since(owner: str, signature: str, visited: frozenset[str] = frozenset()) -> int | None:
        if owner in visited or owner not in classes:
            return None
        node = classes[owner]
        versions = [
            max(int(node.get("since", "1")), int(method.get("since", node.get("since", "1"))))
            for method in node.findall("method") if method.get("name") == signature
        ]
        for parent in (*node.findall("extends"), *node.findall("implements")):
            version = since(parent.attrib["name"], signature, visited | {owner})
            if version is not None:
                versions.append(max(version, int(node.get("since", "1"))))
        return min(versions) if versions else None

    references = set()
    helper_dir = root / "smali/com/anthropic/claude/tv"
    paths = list(helper_dir.glob("ClaudeTvHelper*.smali"))
    if not paths:
        raise ValueError("Helper compilado ausente")
    for path in paths:
        references.update(re.findall(
            r"invoke-[^\n]+, L(android/[^;]+);->([^\s]+)", path.read_text(encoding="utf-8")
        ))
    unsupported = []
    for owner, signature in sorted(references):
        version = since(owner, signature)
        if version is None or version > 30:
            unsupported.append(f"{owner}->{signature}: API {version}")
    if unsupported:
        raise ValueError("APIs do helper incompatíveis ou não resolvidas: " + "; ".join(unsupported))
    print(f"[ok] {len(references)} chamadas Android do helper disponíveis na API 30")


def audit_apk(apk: Path, aapt2: Path) -> None:
    result = subprocess.run([str(aapt2), "dump", "badging", str(apk)],
                            check=True, capture_output=True, text=True, encoding="utf-8")
    sdk = re.search(r"^(?:minSdkVersion|sdkVersion):'(\d+)'", result.stdout, re.MULTILINE)
    if sdk is None or int(sdk.group(1)) > 30:
        raise ValueError("minSdk do APK é incompatível com API 30")
    print(f"[ok] minSdk do APK: {sdk.group(1)}")
    with zipfile.ZipFile(apk) as archive:
        libs = [name for name in archive.namelist() if name.startswith("lib/") and name.endswith(".so")]
        if not libs:
            raise ValueError("APK sem bibliotecas nativas")
        for name in libs:
            with archive.open(name) as file:
                header = file.read(52)
            if (not name.startswith("lib/armeabi-v7a/") or header[:6] != b"\x7fELF\x01\x01"
                    or struct.unpack_from("<H", header, 18)[0] != 40):
                raise ValueError(f"Biblioteca incompatível com ARMv7/32 bits: {name}")
        print(f"[ok] {len(libs)} bibliotecas ELF ARM de 32 bits")
        for name in sorted(archive.namelist()):
            if not re.fullmatch(r"classes(?:\d+)?\.dex", name):
                continue
            with archive.open(name) as file:
                header = file.read(112)
            if header[:4] != b"dex\n":
                raise ValueError(f"DEX inválido: {name}")
            method_count = struct.unpack_from("<I", header, 88)[0]
            print(f"[ok] {name}: {method_count}/65536 referências de métodos")
            if method_count > 65536:
                raise ValueError(f"Limite DEX excedido: {name}")
        for name in ("res/anim/claude_tv_overlay_enter.xml", "res/anim/claude_tv_overlay_exit.xml"):
            if name not in archive.namelist():
                raise ValueError(f"Animação ausente do APK: {name}")
        print("[ok] transições do overlay empacotadas")
    result = subprocess.run([str(aapt2), "dump", "resources", str(apk)],
                            check=True, capture_output=True, text=True, encoding="utf-8")
    if "style/ClaudeTvOverlayAnimation" not in result.stdout:
        raise ValueError("Estilo de animação ausente da tabela de recursos")
    print("[ok] estilo de animação disponível para getIdentifier")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parent.parent / "claude_full_decompiled")
    parser.add_argument("--api-versions", type=Path, required=True)
    parser.add_argument("--aapt2", type=Path, required=True)
    args = parser.parse_args()
    try:
        audit_helper_api(args.project, args.api_versions)
        audit_apk(args.apk, args.aapt2)
    except (OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile) as error:
        print(f"[erro] {error}", file=sys.stderr)
        return 1
    print("[limite] Checagem estrutural; não mede FPS, foco D-pad nem estabilidade do áudio na TV")
    return 0


if __name__ == "__main__":
    sys.exit(main())
