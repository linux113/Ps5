# VS Code extension (roadmap stub)

**Idea:** show live Flagsmith flag values inline in the editor — hover a flag
name, see its current value per environment, flip it without leaving VS Code.

This folder is a stub for the roadmap item in the main README. The web +
terminal dashboards already cover the core demo; this extension is the
natural next step and reuses the same mock/real API (`mock/server.py`).

Planned commands:
- `Leonida: List Flags` — quick-pick to toggle a flag
- `Leonida: Show Flag Values` — inline lens above `hasFeature('…')` calls
