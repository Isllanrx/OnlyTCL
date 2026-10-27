# Task: Remediação de Dados Sensíveis e Configuração de Ambiente

## Pedido Original
- Criar arquivo de exemplo (`exemplo.env` / `.env.example`) referenciando IP e caminhos para parametrização.
- Substituir as ocorrências hardcoded de IP (`192.168.76.209`) e caminhos absolutos locais nos scripts.
- Atualizar `.gitignore` e remover do rastreamento do Git os caches (`__pycache__`, `.pyc`).
- Esclarecer se o DSN do Sentry é um dado sensível pessoal do usuário.

## Concluído
1. Criados `exemplo.env` e `.env.example` na raiz com parametrização de `TV_IP`, `TV_PORT`, `TV_DEVICE`, `ANDROID_SDK_ROOT`, `ADB_PATH`, `PROJECT_ROOT` e `OUTPUT_DIR`.
2. Criados utilitários de carga de ambiente `apps/claude-tv/scripts/load_env.ps1` e `apps/claude-tv/scripts/load_env.py` com fallback automático para variáveis de ambiente ou `exemplo.env`.
3. Substituídas todas as ocorrências de `192.168.76.209` em todos os scripts PowerShell (.ps1), Python (.py), Bash (.sh), Kotlin (.kt) e testes unitários.
4. Substituídos todos os caminhos absolutos locais do host (`C:\Users\Isllan Toso\...`, `E:\projeto_twitchlit\...`, `E:\Android\Sdk\...`) por caminhos relativos ao projeto e variáveis configuráveis.
5. Removidos do controle de versão do Git os artefatos de bytecode `.pyc` e diretórios `__pycache__`.
6. Atualizado `.gitignore` para ignorar `__pycache__/`, `*.pyc`, `.env`, `.env.local`, `.venv/`, `graphify-out/cache/` e temporários.
7. Esclarecido que o DSN do Sentry é público para envio de crash reports e pertence ao upstream/projeto base de terceiros, não constituindo credencial pessoal privada do usuário.

## Próximos Passos
- Nenhum pendente.
