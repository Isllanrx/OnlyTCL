# Claude TV (Android TV 11 Port & Remote Voice Integration)

Vertical slice containing source code and hooks adapted for running Claude AI on Android TV 11.

---

## Implemented Components

* Remote Voice Button Interception: `ClaudeTvAccessibilityService` intercepts physical remote microphone keys (`KEYCODE_VOICE_ASSIST` / `KEYCODE_SEARCH`) and triggers the voice overlay in < 200 ms.
* D-Pad Focus Scaling: Bytecode injection via `ClaudeTvHelper` ensuring remote navigation across chats, buttons, and text fields.
* 1080p Dark Theme: High-contrast palette designed for TV viewing distances.
* Native Rust Module: `libclaudetv_rtk.so` for local intent routing and network token optimization.

Binary releases are hosted at:
https://github.com/Isllanrx/OnlyTCL/releases/tag/v1.0.0
