# Hardware Architecture and Video Pipeline - TCL BeyondTV4 (Realtek RTD2851M)

Technical specifications, hardware constraints, and display composer details of the TCL Smart TV.

---

## 1. Platform Specifications

* Device: TCL Smart TV BeyondTV4 (`Smart_TV_Pro` / `BeyondTV4`).
* SoC: Realtek RTD2851M (`rtd288o`).
* CPU: Quad-Core ARM Cortex-A55 @ 1.3 GHz (32-bit `armeabi-v7a` Android userland).
* GPU: ARM Mali-G31 MP2.
* RAM: 1.5 GB physical RAM + 768 MB Swap ZRAM.
* Display: 1920x1080 @ 60 Hz.
* Media Decoder: `OMX.realtek.video.decoder` (hardware support for AVC, HEVC, VP9, AV1).
* OS: Android TV 11 (Linux Kernel 4.19).

---

## 2. The GPU Composition Bottleneck (CLIENT Layer)

In standard Android TV applications and Chromium WebView players:
1. Video decoded by MediaCodec passes to an `ImageReader` or OpenGL texture.
2. The Mali-G31 GPU renders the scene to an intermediate framebuffer object (FBO).
3. `SurfaceFlinger` triggers software/GPU composition (`CLIENT` composition type).
4. Outcome on Entry-Level SoCs: At 1080p60, Mali-G31 fill rate saturates at 100%, causing decoding latency to spike to 119 ms, dropping up to 10 frames per second.

---

## 3. The Solution: Direct Video Tunneling via Realtek VSC (DEVICE Layer)

The Realtek RTD2851M features a dedicated hardware Video Surface Composer (VSC / HWC2).

When an application outputs MediaCodec directly to a `SurfaceView`:
1. SurfaceFlinger promotes the layer to `DEVICE (2)`.
2. Decoded YUV buffers flow directly to the display controller plane.
3. The Mali-G31 GPU is bypassed for video, remaining dedicated solely to 2D UI elements.
4. Measured Metrics:
   - Frame Rate: Steady 59.988 FPS.
   - Decoding Latency: < 4 ms.
   - Frame Drops: 0.00%.
   - CPU Overhead: Decreased by over 40%.
