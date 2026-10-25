# Claude TV - Reverse Engineering Modifications and Smali Patches

This document logs structural modifications applied to the official Claude APK (`1.260930.20`) to enable native compatibility with Android TV 11 on the Realtek RTD2851M SoC (`armeabi-v7a`).

---

## 1. Android Platform Compatibility (`minSdkVersion`)

- **Stock APK**: `minSdkVersion: 32` (Android 12L).
  *Symptom on TV*: `INSTALL_FAILED_OLDER_SDK` on Android TV 11 (API 30).
- **Modification**: Lowered `minSdkVersion` to `30` in `AndroidManifest.xml` and `apktool.yml`.
- **Validation**: Installed with `Success` on Android TV 11.

---

## 2. Remote Voice Button Interception (`ClaudeTvAccessibilityService`)

- **Objective**: Intercept physical remote microphone buttons (`KEYCODE_VOICE_ASSIST`, `KEYCODE_SEARCH`) and route directly to the voice assistant overlay without invoking stock platform assistants.
- **Implementation**: Dedicated `AccessibilityService` registered with `android:canRetrieveWindowContent="false"` and `android:accessibilityFeedbackType="feedbackGeneric"`.
- **Latency**: Voice overlay dispatched in < 200 ms.

---

## 3. Remote D-Pad Navigation and Focus Scaling (`ClaudeTvHelper`)

- **Objective**: Ensure seamless 5-way D-Pad remote navigation on screens originally developed for touchscreens.
- **Implementation**: Injected bytecode in activity lifecycle hooks ensuring persistent focus rings, directional traversal, and soft input suppression on TV displays.

---

## 4. Native Rust Intent Router (`libclaudetv_rtk.so`)

- **Objective**: Local processing of system intents, reducing token overhead and latency.
- **Compilation**: Compiled via Android NDK for `armeabi-v7a` with LTO and size optimization flags.
