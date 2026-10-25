# Arquitetura de Hardware e Pipeline de Vídeo — TCL BeyondTV4 (Realtek RTD2851M)

Este documento descreve as descobertas de baixo nível, restrições e arquitetura do compositor de vídeo da Smart TV TCL.

---

## 1. Especificações Técnicas da Plataforma

* **Dispositivo:** TCL Smart TV BeyondTV4 (`Smart_TV_Pro` / `BeyondTV4`).
* **SoC:** Realtek RTD2851M (`rtd288o`).
* **CPU:** Quad-Core ARM Cortex-A55 @ 1.3 GHz (Arquitetura 32-bit `armeabi-v7a` no userland do Android).
* **GPU:** ARM Mali-G31 MP2.
* **Memória RAM:** 1.5 GB de RAM física + 768 MB Swap ZRAM.
* **Painel:** 1920x1080 @ 60 Hz.
* **Decodificador:** `OMX.realtek.video.decoder` (suporte a hardware para AVC/H.264, HEVC/H.265, VP9 e AV1).
* **Sistema Operacional:** Android TV 11 (Kernel Linux 4.19).

---

## 2. O Gargalo Crítico: Composição via GPU (CLIENT Layer)

No Android TV convencional e em aplicativos baseados em WebView ou renderizadores padrão:
1. O vídeo decodificado pelo MediaCodec passa para um `ImageReader` ou textura OpenGL.
2. A GPU Mali-G31 compõe a cena em um framebuffer intermediário (FBO).
3. O `SurfaceFlinger` requisita nova composição (`CLIENT`), rasterizando a interface em software/GPU.
4. **Resultado em TVs de Entrada:** Em 1080p a 60 FPS, a taxa de preenchimento da GPU Mali-G31 satura a 100%, elevando a latência de decodificação para **119 ms**, com descarte de até 10 quadros por segundo e travamentos contínuos.

---

## 3. A Solução: Túnel de Vídeo Direto via Realtek VSC (DEVICE Layer)

O processador Realtek RTD2851M conta com um bloco dedicado de exibição denominado **Video Surface Composer (VSC)** ou Hardware Composer (HWC2).

Quando o aplicativo aloca uma `SurfaceView` diretamente ligada à saída do `MediaCodec`:
1. O SurfaceFlinger promove a camada para **`DEVICE (2)`**.
2. Os buffers YUV decodificados pelo hardware fluem direto para a camada física de display do chip Realtek.
3. A GPU Mali-G31 fica completamente livre para processar apenas elementos da interface gráfica 2D.
4. **Métricas Físicas Atingidas:**
   * Taxa de quadros: **60 FPS estáveis** (59.988 FPS medidos).
   * Latência de decodificação: < 4 ms.
   * Perda de quadros: **0.00%**.
   * Consumo de CPU: reduzido em mais de 40%.
