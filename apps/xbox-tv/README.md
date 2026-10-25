# Xbox Game Pass TV Custom (1080p60 Hardware Pipeline Realtek)

Vertical slice containing source code, native bridges, and shims developed for running xCloud on Realtek RTD2851M Smart TVs.

---

## Architecture Components

* `src/bridge/`: Java bridge sources (`XStreamBridge`, `GamepadBridge`, `TvShim`, `VideoSink`, `AudioSink`) handling hardware SurfaceView allocation and controller input.
* `src/www/`: Shims injected at document start:
  - `tv-shim.js`: Forces `BrazilSouth` datacenter at index 0, handles CORS compliance, and removes conflicting custom headers.
  - `xstream.js` & `xstream-lib.js`: Intercepts `RTCPeerConnection` and delegates session handling to the native engine without requiring legacy `sdpSemantics`.
* `src/native/`: C++ core (`xbox_core.cpp`) with real-time thread scheduling (`nice -20`) and zero allocations in the game loop.
* `src/xstream/`: Custom Rust WebRTC engine (`crates/xstream`) handling depacketization, jitter buffering, and direct MediaCodec delivery.

Binary releases are hosted at:
https://github.com/Isllanrx/OnlyTCL/releases/tag/v1.0.0
