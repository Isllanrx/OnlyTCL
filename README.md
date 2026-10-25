# OnlyTCL — Otimização Extrema, Engenharia Reversa e Suíte de Apps para TCL Android TV

Repositório público dedicado à modernização, otimização de desempenho e ecossistema de aplicativos desenvolvidos e adaptados especificamente para a **Smart TV TCL** (modelo BeyondTV4 / SoC Realtek RTD2851M / Android TV 11).

Este projeto resolve os gargalos crônicos de desempenho, stuttering em jogos na nuvem, bloatwares de fábrica e poluição visual da interface original, elevando a experiência para nível profissional com **1080p a 60 FPS estáveis**.

---

## 🔬 Metodologia: Engenharia Reversa Assistida por Inteligência Artificial

Todas as soluções, pontes de comunicação e otimizações de baixo nível presentes neste repositório foram projetadas e homologadas através de **Engenharia Reversa Assistida por Modelos de Inteligência Artificial Avançados (Anthropic Claude & Google Antigravity / DeepMind)** em conjunto com ferramentas especializadas de auditoria binária:

* **Descompilação e Análise Estática:** JADX, Ghidra e Apktool para engenharia reversa de runtimes Smali, injeção de bytecodes e desmontagem de bibliotecas C/C++ compartilhadas (`.so`).
* **Instrumentação Dinâmica e Forense:** Ferramentas REA (*Reverse Engineer Anything*) e ADB para inspeção em tempo real de sockets de rede (`/proc/net/tcp`), alocação de buffers gráficos no `SurfaceFlinger`, fences de hardware (`RHWC2`) e estados do gerenciador de mídia (`media.resource_manager`).
* **Engenharia de Roteamento e WebRTC:** Reestruturação de descritores de sessão SDP, shims para W3C Gamepad API, injeção assíncrona de WebMessageListener e ancoragem geográfica de datacenters.

---

## 📺 Hardware Alvo (Dispositivo Homologado)

* **Modelo:** TCL Smart TV BeyondTV4 (`Smart_TV_Pro` / `BeyondTV4`).
* **Processador (SoC):** Realtek RTD2851M (`rtd288o`) — Quad-Core ARM Cortex-A55 @ 1.3 GHz (userland de 32 bits `armeabi-v7a`).
* **Processador Gráfico (GPU):** ARM Mali-G31 MP2.
* **Memória:** 1.5 GB RAM física + 768 MB Swap ZRAM.
* **Display:** 1920x1080 @ 60 Hz.
* **Sistema:** Android TV 11 (Kernel Linux 4.19).
* **Decodificador:** `OMX.realtek.video.decoder` com suporte a hardware para H.264/AVC, H.265/HEVC, VP9 e AV1.

---

## 📦 Aplicativos Disponíveis (`apks/`)

Todos os APKs compilados, alinhados em 4K (`zipalign -p 4`) e assinados estão disponíveis prontos para instalação direta na pasta [`apks/`](apks/):

| Aplicativo | APK | Descrição Técnica |
|---|---|---|
| **Xbox Game Pass TV Custom** | `gamepass-tv-custom.apk` | Roda o xCloud a **1080p cravado a 60 FPS** com renderização direta no plano de hardware Realtek VSC (`DEVICE` layer). Ancorado no datacenter de São Paulo (**Ping 21 ms** contra 150 ms nos EUA) e com suporte nativo total ao **Controle Xbox Bluetooth**. |
| **ZeusBR (Twitch TV)** | `zeusbr-tv.apk` | Cliente Twitch nativo construído do zero em **Rust (UniFFI) + Jetpack Compose for TV**. Túnel de vídeo por hardware com **zero quadros perdidos**, consumo de CPU inferior a 45% e player com baixa latência. |
| **Claude TV** | `claude-tv.apk` | Port adaptado do aplicativo Claude AI para Android TV 11. Interface escura 1080p com D-pad focus scaling e **disparo automático do microfone pelo botão de voz do controle da TV** via serviço de acessibilidade dedicado. |
| **tv-home** | `tv-home.apk` | Launcher minimalista ultra-rápido (< 700 KB). Substitui a interface pesada e cheia de propagandas da Google TV por um grid limpo e instantâneo com atalhos diretos. |
| **ZeusRemote** | `zeusremote.apk` | Receptor e ponte de controle remoto via Wi-Fi integrado diretamente ao serviço nativo de rede local da TCL (protocolo T-Cast / `nScreen_srv`). |

---

## ⚡ Instalação Rápida via ADB

Certifique-se de que a sua TV TCL está na mesma rede local e com a **Depuração USB / Modo Desenvolvedor** ativada nas configurações do sistema.

### 1. Conectar à TV via Rede
```bash
adb connect <IP_DA_SUA_TV>:5555
```

### 2. Instalação Completa Automatizada
Execute o script correspondente ao seu sistema operacional:

* **Windows:**
  ```cmd
  scripts\install_all.bat
  ```
* **Linux / macOS:**
  ```bash
  chmod +x scripts/install_all.sh
  ./scripts/install_all.sh
  ```

O script automaticamente instala os 5 APKs, concede as permissões de sistema (`WRITE_SECURE_SETTINGS`, gravação de áudio e acessibilidade) e executa a compilação AOT (`dex2oat speed`) para carregamento instantâneo.

---

## 🧹 Otimização do Sistema e Remoção de Bloatware (Debloat)

As TVs TCL vêm de fábrica com mais de 30 processos em segundo plano que consomem RAM e ciclos de CPU essenciais.

Para liberar até **400 MB de memória RAM** e deixar o sistema fluido:

* **Windows:**
  ```cmd
  scripts\tv_debloat.bat
  ```
* **Linux / macOS:**
  ```bash
  chmod +x scripts/tv_debloat.sh
  ./scripts/tv_debloat.sh
  ```

### O que o debloat realiza:
1. Desativa de forma segura 31 pacotes de fábrica desnecessários (telemetria, lojas secundárias e serviços em background).
2. Ajusta as escalas de animação do Android para `0.5x`, dobrando a sensação de resposta do controle.
3. Limpa caches temporários de pacotes (`trim-caches 4096M`).

---

## 📚 Documentação Técnica Aprofundada

Para engenheiros e desenvolvedores interessados nos detalhes de baixo nível:

* [Arquitetura de Hardware e Pipeline Realtek VSC](docs/HARDWARE_REALTEK.md): Análise da GPU Mali-G31 versus o plano de exibição direto do Realtek RTD2851M.
* [Engenharia Reversa do xCloud e Roteamento Regional](docs/XBOX_PIPELINE.md): Detalhamento do motor Rust WebRTC, SDP Munging e fixação de servidores em São Paulo.

---

## ⚖️ Aviso Legal

Este projeto é disponibilizado exclusivamente para fins educacionais, de pesquisa em engenharia reversa e para melhoria de acessibilidade e desempenho pessoal em dispositivos próprios. Todas as marcas, nomes de produtos e logos citados pertencem aos seus respectivos proprietários.
