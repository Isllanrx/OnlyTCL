# ZeusBR (Native Twitch TV Client for Android TV)

High-performance Twitch TV client authored from scratch in Rust (UniFFI) and Jetpack Compose for TV.

---

## Features

* Direct Hardware Tunnel: HLS/H.264 decoded directly to `SurfaceView` with Realtek VSC enabled (`DEVICE` layer).
* 60 FPS playback with zero dropped frames.
* CPU utilization < 45% (compared to 85% on the stock app).
* Full D-Pad remote navigation, dynamic stream quality selection, and live chat display.

Binary releases are hosted at:
https://github.com/Isllanrx/OnlyTCL/releases/tag/v1.0.0
