# Engenharia Reversa e Arquitetura do Xbox Cloud Gaming TV Custom

Este documento detalha o processo de engenharia reversa e otimização do aplicativo oficial do Xbox Game Pass (`gamepass.fire.tv`) para execução em Smart TVs com processador Realtek.

---

## 1. Desafios Enfrentados na Versão Original

1. **Gargalo de Decodificação na WebView:**
   O app oficial roda sobre Chromium WebView. A decodificação WebRTC passava pela GPU Mali-G31, gerando travamentos constantes, perda maciça de pacotes e delay de entrada perceptível.
2. **Matchmaking e Jitter Transcontinental:**
   O app roteava frequentemente a conexão para datacenters nos Estados Unidos (Boydton/Virgínia e Washington), resultando em RTT de ~150 ms, acionando o controle de congestionamento da Microsoft (BWE) e reduzindo a taxa de bits para menos de 4 Mbps com trepidação visual.
3. **Bug do Controle Bluetooth no Android 11:**
   No Android 11, serviços de acessibilidade ativos suprimem a detecção do controle Xbox Wireless via W3C Gamepad API da WebView, fazendo com que o app não reconhecesse comandos in-game.

---

## 2. Engenharia Reversa e Modificações Aplicadas

### A. Motor WebRTC Nativo em Rust (`crates/xstream`)
* Criada uma biblioteca nativa em Rust e C++ que assume a sessão WebRTC diretamente.
* O fluxo de vídeo H.264 é montado e entregue de forma assíncrona para o decodificador de hardware Realtek (`MediaCodec`) desenhado diretamente sobre uma `SurfaceView`.
* Conexão promovida para **`DEVICE`** no SurfaceFlinger, sem sobrecarga de GPU.

### B. Ancoragem Geográfica Estrita no Brasil (`BrazilSouth`)
* Interceptação da chamada `/v2/login/user` via shim JavaScript (`tv-shim.js`).
* A região `BrazilSouth` (`https://brs.core.gssv-play-prod.xboxlive.com`) é reordenada para o **índice 0** do array de regiões com prioridade `fallbackPriority = 0` e `isDefault = true`.
* Redundância mantida de forma decrescente para as demais regiões, prevenindo travamentos caso o cluster brasileiro atinja capacidade total.
* **Resultado:** Ping estável em **21 ms** (São Paulo) com **0.00% de perda de pacotes**.

### C. Ponte de Input Nativa com Prioridade de Tempo Real
* Mapeamento de eixos e botões do controle Xbox Bluetooth via bridge Java dedicada, expondo o estado para a engine com debounce de 4 ms.
* Isolamento de estado (`sIsInGame`): durante o jogo, a injeção de teclas virtuais no DOM da WebView é desativada, impedindo repaints concorrentes e perda de foco.
