# Diretrizes de Contribuicao - OnlyTCL

Agradecemos o interesse em contribuir com o projeto OnlyTCL. Este projeto e mantido pela comunidade para ajudar proprietarios de Smart TVs TCL a extrair a melhor performance possivel de seus dispositivos.

---

## 1. Principios de Desenvolvimento

1. **Sem Emojis:** Todos os commits, codigos-fonte, comentarios, documentacoes e PRs devem ser estritamente tecnicos e sem emojis.
2. **Arquitetura Vertical:** Novas funcionalidades ou aplicacoes devem ser adicionadas como fatias verticais autonomas dentro do diretorio `apps/<nome-do-app>/`.
3. **Binarios Apenas em Releases:** Nunca submeta arquivos `.apk`, `.so` ou bibliotecas compiladas na arvore do Git. Submissoes devem conter codigo-fonte, patches Smali ou scripts de automacao. Binarios sao distribuidos exclusivamente via GitHub Releases.
4. **Preservacao de Hardware:** Solucoes nao devem realizar escrita direta em particoes protegidas de firmware (ex: `/system`, `/vendor`) sem verificacao de integridade. O foco do projeto e otimizacao em espaco de usuario (`userland`) e APIs padrao do Android.

---

## 2. Como Submeter Alteracoes

1. Crie um fork do repositorio.
2. Crie um branch para sua funcionalidade (`git checkout -b feature/minha-melhoria`).
3. Faca o commit das suas alteracoes seguindo o padrao Conventional Commits (`git commit -m "feat(xbox-tv): adiciona suporte a controle DualShock 4"`).
4. Envie para o seu fork (`git push origin feature/minha-melhoria`).
5. Abra um Pull Request detalhando as alteracoes, testes realizados e o modelo de TV utilizado.
