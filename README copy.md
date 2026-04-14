# Guardian

Windows-native parental safety tool that monitors children's gaming sessions and alerts parents to potentially dangerous interactions.

## Architecture

| Component | Tech | Purpose |
|---|---|---|
| **Guardian.Desktop** | WPF / .NET 8 | Parent-facing setup & status app |
| **Guardian.Worker** | .NET 8 Windows Service | Game detection, text capture, OpenAI analysis, parent alerts |
| **Guardian.Shared** | .NET 8 class library | Shared DTOs, enums, constants |
| **Installer** | WiX Toolset (MSI) | Windows installer with service registration |

> All monitoring + LLM logic runs locally on the client via OpenAI API. The backend (separate repo) is only a customer portal / download site.

## Repo Layout

```
client/
  Guardian.sln              Solution file
  Directory.Build.props     Shared MSBuild properties
  apps/
    Guardian.Desktop/       WPF desktop app (Views, ViewModels, Services, Models)
    Guardian.Worker/        Background service (Workers, Services, Models)
  shared/
    Guardian.Shared/        Shared DTOs, enums, constants
  installer/                WiX MSI packaging
docs/                       Architecture, setup flow, privacy
```

## Quick Start

```bash
cd client
dotnet restore
dotnet build
```

## Design Principles

- **Consent-based** — installed by parent, visible to child
- **Transparent** — system tray icon, auditable rules and alerts
- **Minimal data** — only game presence and policy events collected
- **No covert surveillance** — no keylogging, screen capture, or chat interception