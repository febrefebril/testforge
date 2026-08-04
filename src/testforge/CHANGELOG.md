
# Changelog

## Unreleased

### Added
- P0.2-S: revisao Pydantic de dados sensiveis, scanner offline, copia sanitizada, GUI por flag e CLI `submit --dry-run` sem publicacao Git.

### Deprecated
- `testforge run` agora delega com seguranca para `testforge run-incremental`; remocao prevista em 2026-08-12. Migre para `testforge run-incremental <script>`.

### Fixed
- Relatorio ausente ou inconsistente retorna `indeterminado` (exit 2), nunca sucesso.

