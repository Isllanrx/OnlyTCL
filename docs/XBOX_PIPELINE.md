# Reverse Engineering and Architecture: Xbox Cloud Gaming TV Custom

Technical documentation of modifications applied to the official Xbox Game Pass client (`gamepass.fire.tv`) for Realtek-based Smart TVs.

---

## 1. Architectural Challenges in the Stock App

1. WebView GPU Bottleneck: WebRTC decoding was handled inside the Chromium WebView and rendered through the Mali-G31 GPU, causing heavy stuttering and input lag.
2. Intercontinental Matchmaking: Sessions were frequently routed to North American datacenters (Boydton/Virginia), yielding 150 ms RTT, triggering aggressive BWE bitrate throttling down to 4 Mbps, and causing SRTP packet duplication.
3. Bluetooth Gamepad Input Dropping on Android 11: Active accessibility services suppress W3C Gamepad API events inside Blink.

---

## 2. Implemented Architecture and Reverse Engineering

### A. Custom Rust WebRTC Engine (`crates/xstream`)
* Standalone WebRTC actor engine written in Rust and C++.
* H.264 streams are depacketized and fed asynchronously to `MediaCodec` rendered on a native `SurfaceView`.
* SurfaceFlinger promotes the surface to `DEVICE` composition.

### B. Strict Regional Matchmaking Anchoring (`BrazilSouth`)
* Interception of `/v2/login/user` via JavaScript shim (`tv-shim.js`).
* The `BrazilSouth` region (`https://brs.core.gssv-play-prod.xboxlive.com`) is placed at index 0 with `fallbackPriority = 0` and `isDefault = true`.
* Other global regions remain as secondary fallbacks to avoid connection drops during server capacity limits.
* Ping stabilized at 21 ms with 0.00% packet loss.

### C. Low-Latency Real-Time Input Bridge
* Java bridge with real-time thread scheduling (`nice -20`) exposing gamepad state with 4 ms debounce.
* In-game state isolation (`sIsInGame`): DOM key dispatching is halted during gameplay, eliminating synthetic navigation repaints.
