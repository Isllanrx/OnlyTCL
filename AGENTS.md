# AGENTS.md - Repository Guidelines for OnlyTCL

Instructions for automated agents and contributors.
The primary guideline document is [CLAUDE.md](CLAUDE.md).

## Core Directives
1. No Emojis: All documentation, commit messages, and logs must be strictly technical and devoid of emojis.
2. Documentation in English: All markdown documentation must be written in standard technical English.
3. No Comments in Code: Do not put conversational or explanatory comments inside code or script files. All documentation must live in `.md` files.
4. Vertical Architecture: Components and application slices must remain self-contained within `apps/<app-name>/`.
5. Binaries in Releases: Never commit `.apk`, `.so`, or binary artifacts to Git. Use GitHub Releases exclusively.
