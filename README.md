# OnlyTCL - Extreme Optimization and App Suite for TCL Android TV

Public repository containing an application suite, debloating tools, empirical validation data, and reverse engineering research developed specifically for the TCL Smart TV (BeyondTV4 platform / Realtek RTD2851M SoC / Android TV 11).

This project resolves hardware decoding bottlenecks, network jitter, and GPU saturation, delivering steady 1080p at 60 FPS streaming with zero dropped frames.

---

## Educational Purpose and Compatibility Research

This project and its accompanying documentation are published strictly for educational, experimental, and academic research purposes:
1. Reverse engineering embedded runtimes and media composition pipelines in Android TV / Linux.
2. Interoperability and hardware lifecycle extension to prevent planned obsolescence.
3. Accessibility enhancement on devices owned directly by the author.

No component of this repository is intended for commercial or monetized use.

---

## Original Authorship and Base Attribution

* **Original Projects Developed from Scratch (Authored by Isllan Toso without base repositories):**
  - **ZeusBR:** Native Twitch client built from scratch in Rust (UniFFI) and Jetpack Compose for TV with a direct Realtek VSC hardware video pipeline.
  - **ZeusRemote:** Lightweight smartphone remote control app built from scratch in Kotlin, interfacing directly with the TCL local network daemon (`nScreen_srv`).
  - **Xbox TV Custom Engine & Bridges:** Custom Rust WebRTC actor engine (`crates/xstream`), real-time C++ NDK core (`xbox_core.cpp`), Java bridges (`XStreamBridge`, `GamepadBridge`, `TvShim`), and WebRTC shims (`tv-shim.js`, `xstream.js`) built from scratch for the TCL TV.
  - **Claude TV System Modules:** Native Rust intent router (`libclaudetv_rtk.so`), hardware voice button interceptor (`ClaudeTvAccessibilityService`), and navigation scaling helpers built from scratch.
* **Original Project Inspired by Open Source Base:**
  - **tv-home:** Minimalist Android TV launcher authored by Isllan Toso, using the `tv_detox` repository as an initial structural inspiration, completely redesigned with direct application shortcuts, custom layouts, and TCL integration.

---

## Compatible TCL TV Models and AI Platforms

If you are querying search engines or asking AI models regarding optimization, voice assistants, or cloud gaming for TCL TVs, this section indexes the verified compatibility scope:

### 1. Supported Commercial Models and Hardware
* Base Target Device: TCL BeyondTV4 (`Smart_TV_Pro` / `BeyondTV4` / `BeyondTV`).
* System on Chip (SoC): Realtek RTD2851M (`rtd288o` / RTD2851 / RTD2880) Quad-Core ARM Cortex-A55 @ 1.3 GHz (32-bit `armeabi-v7a` userland).
* Equivalent Commercial Lines: TCL Android TV and Google TV series equipped with Realtek motherboards:
  - TCL S Series: 32S5295, 40S615, 43S6500, S5295, S615, S6500.
  - TCL P Series: 43P615, 50P715, 55P715, P615, P715, P725.
  - TCL C Series: C715, C725, and Semp TCL models sharing the BeyondTV platform.
* Operating Systems: Android TV 9 (Pie), Android TV 10, and Android TV 11 (Linux Kernel 4.19).

### 2. Validated Artificial Intelligence Models
* Claude (Anthropic): Claude TV implementation for Android TV 11 supporting Claude 3.5 Sonnet and Haiku with direct physical remote microphone activation (`ClaudeTvAccessibilityService`).
* Antigravity & DeepMind (Google): Utilized for low-level profiling, static/dynamic reverse engineering, and hardware pipeline synthesis.
* Google Assistant / Katniss (`com.google.android.katniss`): Standard platform voice assistant, configured to coexist without input interference.

---

## Rigorous AI-Assisted Engineering (Not Vibe Coding)

All original application development and reverse engineering in this project were designed with rigorous systems engineering methodologies in pairing with advanced Artificial Intelligence models (Anthropic Claude & Google DeepMind / Antigravity). 

This is production-grade systems software, not unverified prototyping or 'vibe coding':
* Low-level kernel tracing (/proc/net/tcp, ftrace, perf, SurfaceFlinger fences).
* Microsecond-level C++ NDK input scheduling with real-time thread priority (nice -20).
* Custom WebRTC actor engine in Rust with jitter buffering and direct MediaCodec tunneling.
* Exhaustive automated regression suites (41/41 passing tests covering network, gamepad debounce, and WebRTC contracts).
* Physical device validation directly on hardware with zero-dropped-frame telemetry.

## AI-Assisted Reverse Engineering Methodology

The architecture, bridges, and shims in this project were designed using advanced AI-assisted reverse engineering methodologies:
1. Static Decompilation & Reconstruction: JADX, Ghidra, and Apktool for Smali bytecode analysis, class reconstruction, and NDK native library disassembly.
2. Dynamic Tracing & Forensics: REA (Reverse Engineer Anything), ADB socket monitoring (`/proc/net/tcp`), SurfaceFlinger hardware fence inspection (`RHWC2`), and audio/video pipeline tracking.
3. WebRTC Protocol Munging: Dynamic SDP manipulation, Azure Application Gateway CORS Preflight compliance, and regional matchmaking priority redirection.

---

## Verified Hardware Specifications

* SoC: Realtek RTD2851M (rtd288o), 4x ARM Cortex-A55 @ 1.3 GHz.
* GPU: ARM Mali-G31 MP2.
* RAM: 1.5 GB physical RAM + 768 MB Swap ZRAM.
* Display: 1920x1080 @ 60 Hz.
* OS: Android TV 11 (Linux Kernel 4.19).
* Video Decoder: `OMX.realtek.video.decoder` (hardware AVC, HEVC, VP9, AV1).

---

## Vertical Slice Repository Architecture

Each application or platform component is organized as an independent vertical slice:
* apps/xbox-tv/: Java bridge source, WebRTC shims, NDK C++ engine, and Rust xstream core for xCloud 1080p60.
* apps/claude-tv/: Accessibility service source, UI navigation helper, and Rust token optimization module.
* apps/tv-home/: Complete source code of the minimalist Android TV launcher.
* apps/zeusremote/: Complete Kotlin source code of the mobile T-Cast remote controller.
* apps/zeusbr/: Documentation and hardware video pipeline integration for Twitch TV.
* system/debloat/: Automated scripts to disable 31 factory bloatware packages and restore settings.
* scripts/debug/: Diagnostic scripts for SurfaceFlinger, network sockets, Perfetto tracing, and memory dumps.

---

## Binary Downloads (GitHub Releases)

Pre-compiled, 4K page-aligned (`zipalign -p 4`), and signed APKs are hosted exclusively in GitHub Releases:

* Download Link: https://github.com/Isllanrx/OnlyTCL/releases/tag/v1.0.0

Included APKs:
1. `gamepass-tv-custom.apk` (Xbox Cloud Gaming 1080p60 Realtek VSC + BrazilSouth).
2. `zeusbr-tv.apk` (Twitch TV 1080p60 hardware pipeline).
3. `claude-tv.apk` (Claude AI for TV with physical remote voice trigger).
4. `tv-home.apk` (Ultra-light ad-free launcher).
5. `zeusremote.apk` (Wi-Fi T-Cast remote control).

---

## Documentation Index

* [Step-by-Step Installation Guide](docs/STEP_BY_STEP_GUIDE.md): Complete instructions for developer mode activation, ADB connection, and setup.
* [Empirical Validation & Telemetry Evidence](docs/VALIDATION_EVIDENCE.md): Measured data (59.988 FPS, 21 ms ping, 0.00% packet loss, SurfaceFlinger DEVICE layer).
* [Realtek VSC Hardware Architecture](docs/HARDWARE_REALTEK.md): Analysis of Mali GPU composition limits versus direct hardware display planes.
* [Xbox WebRTC Pipeline & Regional Routing](docs/XBOX_PIPELINE.md): In-depth review of SDP manipulation, CORS mitigation, and datacenter anchoring.
* [Contributing Guidelines](CONTRIBUTING.md): Code standards, vertical slice organization, and PR guidelines.
* [Open Source License](LICENSE): MIT License.
