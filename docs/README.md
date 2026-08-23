# QTR Pairing Process documentation

QTR is a Python desktop application for 5v5 tournament-pairing analysis. Start
with the repository [README](../README.md) for product setup and
[CONTRIBUTING](../CONTRIBUTING.md) for contribution expectations.

## Developer learning set

- [Architecture](architecture.md): launcher, UI, data, and dependency boundaries.
- [Testing](testing.md): local test commands and the Tk-aware CI model.
- [Releasing](releasing.md): the exact behavior of `scripts/build_release.ps1`.
- [Copilot guide](../.github/copilot-instructions.md): repository-specific agent guidance.

Run the Windows-first task runner from the repository root:

```powershell
.\dev.ps1 setup
.\dev.ps1 check
```

## Existing reference material

- [Developer Guide](DEVELOPER_GUIDE.md)
- [Technical Architecture](TECHNICAL_ARCHITECTURE.md)
- [Database Schema](DATABASE_SCHEMA.md)
- [User Guide](USER_GUIDE.md)
- [Project Scope](PROJECT_SCOPE.md)
