"""
Systematic Validation & Compatibility Test Suite for Claude TV APK
Dispositivo-Alvo: Smart TV TCL Pro (RTD2851M, Android TV 11, armeabi-v7a)
"""
import subprocess
import zipfile
import sys
import os

APK_PATH = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else r"E:\projeto_twitchlit\claude-tv\release\claude-tv-1.260930-20-candidate.apk"
AAPT = r"E:\Android\Sdk\build-tools\36.0.0\aapt.exe"
ZIPALIGN = r"E:\Android\Sdk\build-tools\36.0.0\zipalign.exe"
APKSIGNER = r"E:\Android\Sdk\build-tools\36.0.0\apksigner.bat"
DEXDUMP = r"E:\Android\Sdk\build-tools\36.0.0\dexdump.exe"
READELF = r"E:\Android\Sdk\ndk\30.0.16248370\toolchains\llvm\prebuilt\windows-x86_64\bin\llvm-readelf.exe"

results = []

def record(test_name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append((test_name, status, detail))
    print(f"[{status}] {test_name}: {detail}")

print("=" * 60)
print("CLAUDE TV — BATERIA DE TESTES SISTEMÁTICOS DE COMPATIBILIDADE")
print("=" * 60)

# ----------------------------------------------------
# TESTE 1: Integridade do Pacote e Manifesto (AAPT)
# ----------------------------------------------------
print("\n--- TESTE 1: Validação de Manifesto e Android TV Leanback ---")
try:
    badging = subprocess.check_output([AAPT, "dump", "badging", APK_PATH], text=True, encoding="utf-8")
    record("1.1 minSdkVersion = 30 (Android 11 TCL)", "sdkVersion:'30'" in badging, "minSdkVersion 30 confirmado")
    record("1.2 Leanback Launcher Activity", "leanback-launchable-activity" in badging, "MainActivity registrada para a Home da TV")
    record("1.3 Banner de TV (16:9)", "banner='res/drawable/tv_banner.png'" in badging, "Banner 16:9 associado ao Leanback Launcher")
    record("1.4 Touchscreen não-obrigatório", "uses-feature-not-required: name='android.hardware.touchscreen'" in badging, "TV sem tela touch suportada")
    record("1.5 Leanback software declarado", "uses-feature-not-required: name='android.software.leanback'" in badging, "Compatibilidade de TV declarada")
    record("1.6 Microfone de áudio permitido", "uses-permission: name='android.permission.RECORD_AUDIO'" in badging, "RECORD_AUDIO presente no manifesto")
    record("1.7 Idioma Português incluso", "'pt'" in badging, "pt e pt-PT compilados no resources.arsc")
except Exception as e:
    record("1.0 Execução do AAPT", False, str(e))

# ----------------------------------------------------
# TESTE 2: Bytecode Dalvik e Hook do Microfone (DEXDUMP)
# ----------------------------------------------------
print("\n--- TESTE 2: Bytecode Dalvik e Injeção do ClaudeTvHelper ---")
try:
    with zipfile.ZipFile(APK_PATH) as z:
        dex_files = [n for n in z.namelist() if n.endswith(".dex")]
        record("2.1 Presença dos 4 arquivos DEX", len(dex_files) == 4, f"Encontrados: {len(dex_files)} DEXs")
        
        # Inspecionar classes.dex
        classes_data = z.read("classes.dex")
        has_helper = b"Lcom/anthropic/claude/tv/ClaudeTvHelper;" in classes_data
        record("2.2 Presença da classe ClaudeTvHelper em DEX", has_helper, "ClaudeTvHelper localizado no bytecode")

        has_on_key_hook = b"handleKeyDown" in classes_data
        record("2.3 Hook de tecla de voz em MainActivity", has_on_key_hook, "handleKeyDown referenciado no DEX")

        has_on_create_hook = b"onActivityCreate" in classes_data
        record("2.4 Hook de onCreate em MainActivity", has_on_create_hook, "onActivityCreate referenciado no DEX")

        has_a11y_service = b"Lcom/anthropic/claude/tv/ClaudeTvAccessibilityService;" in classes_data
        record("2.5 Presença de ClaudeTvAccessibilityService em DEX", has_a11y_service, "ClaudeTvAccessibilityService presente em classes.dex")

        # O helper exporta onOverlayCreate(Activity)Z; um call site antigo (...)V causaria
        # NoSuchMethodError a cada toque no botão de assistente. Descritores de método não ficam
        # contíguos no dex, então a verificação usa dexdump -d sobre todos os classes*.dex.
        import tempfile
        sig_new = sig_old = 0
        if os.path.exists(DEXDUMP):
            with tempfile.TemporaryDirectory() as tmp:
                for n in dex_files:
                    path = os.path.join(tmp, n)
                    with open(path, "wb") as fh:
                        fh.write(z.read(n))
                    out = subprocess.run([DEXDUMP, "-d", path], capture_output=True, text=True, errors="replace").stdout
                    sig_new += out.count("ClaudeTvHelper;.onOverlayCreate:(Landroid/app/Activity;)Z")
                    sig_old += out.count("ClaudeTvHelper;.onOverlayCreate:(Landroid/app/Activity;)V")
            record("2.6 Hook onOverlayCreate(Activity)Z sem call site antigo (...)V", sig_new >= 1 and sig_old == 0,
                   f"chamadas Z={sig_new}, chamadas V={sig_old}")
        else:
            record("2.6 Hook onOverlayCreate(Activity)Z sem call site antigo (...)V", False, f"dexdump ausente em {DEXDUMP}")

        no_dead_router = b"handleVoiceTvCommand" not in classes_data and b"ClaudeTvRtk" not in classes_data
        record("2.7 Sem roteador RTK morto no DEX", no_dead_router, "handleVoiceTvCommand/ClaudeTvRtk ausentes")
except Exception as e:
    record("2.0 Validação do Bytecode", False, str(e))

# ----------------------------------------------------
# TESTE 3: Bibliotecas Nativas C++ (32-bit armeabi-v7a)
# ----------------------------------------------------
print("\n--- TESTE 3: Bibliotecas Nativas de Voz e ABI armeabi-v7a ---")
required_libs = [
    "libvoiceclient.so",
    "libwebrtc_apm.so",
    "libopus_jni.so",
    "libsqliteJni.so",
    "libsentry.so",
    "libsentry-android.so",
    "libandroidmath.so",
    "libandroidx.graphics.path.so",
    "libdatastore_shared_counter.so"
]

try:
    with zipfile.ZipFile(APK_PATH) as z:
        apk_libs = [os.path.basename(n) for n in z.namelist() if n.startswith("lib/armeabi-v7a/")]
        missing = [lib for lib in required_libs if lib not in apk_libs]
        record("3.1 Todas as 9 bibliotecas nativas presentes", len(missing) == 0, f"Faltando: {missing}" if missing else "9/9 bibliotecas em lib/armeabi-v7a/")
        
        # Testar ELF de libvoiceclient.so
        lib_data = z.read("lib/armeabi-v7a/libvoiceclient.so")
        is_elf = lib_data[:4] == b"\x7fELF"
        is_32bit = lib_data[4] == 1  # 1 = ELFCLASS32
        is_arm = lib_data[18] == 0x28 # 0x28 = 40 (EM_ARM)
        record("3.2 libvoiceclient.so é ELF 32-bit ARM (armeabi-v7a)", is_elf and is_32bit and is_arm, "Compatível com CPU Cortex-A55 32-bit")
        
        # Testar ELF de libwebrtc_apm.so
        webrtc_data = z.read("lib/armeabi-v7a/libwebrtc_apm.so")
        webrtc_ok = (webrtc_data[:4] == b"\x7fELF") and (webrtc_data[4] == 1) and (webrtc_data[18] == 0x28)
        record("3.3 libwebrtc_apm.so é ELF 32-bit ARM (Echo Cancellation)", webrtc_ok, "Cancelamento de eco acústico pronto")
except Exception as e:
    record("3.0 Validação de Bibliotecas Nativas", False, str(e))

# ----------------------------------------------------
# TESTE 4: Alinhamento de Memória (Zipalign)
# ----------------------------------------------------
print("\n--- TESTE 4: Alinhamento de Mapeamento Direto em Memória (Zipalign) ---")
try:
    cmd = [ZIPALIGN, "-c", "-v", "4", APK_PATH]
    out = subprocess.run(cmd, capture_output=True, text=True)
    record("4.1 Verificação de alinhamento em 4 bytes (zipalign)", out.returncode == 0, "Alinhamento mmap verificado com sucesso")
except Exception as e:
    record("4.0 Validação Zipalign", False, str(e))

# ----------------------------------------------------
# TESTE 5: Assinatura Criptográfica (Apksigner)
# ----------------------------------------------------
print("\n--- TESTE 5: Assinatura Criptográfica do APK ---")
try:
    cmd = [APKSIGNER, "verify", "--verbose", APK_PATH]
    out = subprocess.run(cmd, capture_output=True, text=True)
    is_valid = "Verifies" in out.stdout and out.returncode == 0
    has_v3 = "Verified using v3 scheme (APK Signature Scheme v3): true" in out.stdout
    record("5.1 Assinatura Criptográfica Válida", is_valid, "Assinatura reconhecida pelo Android")
    record("5.2 APK Signature Scheme v3 Ativo", has_v3, "Suportado pelo Android 11+")
except Exception as e:
    record("5.0 Validação Apksigner", False, str(e))

print("\n" + "=" * 60)
passed_count = sum(1 for _, st, _ in results if st == "PASS")
total_count = len(results)
print(f"RESUMO FINAL: {passed_count}/{total_count} TESTES APROVADOS")
print("=" * 60)

if passed_count == total_count:
    print("\n>>> Empacotamento estático aprovado. Validação funcional e de desempenho na TV ainda pendente. <<<")
    sys.exit(0)
else:
    sys.exit(1)
