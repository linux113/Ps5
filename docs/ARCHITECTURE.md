# Architecture — LEONIDA LIVE

```
┌──────────────────────────────┐        ┌──────────────────────────────┐
│  Web Dashboard (index.html)  │        │  Terminal Dashboard (CLI)    │
│  PS5-style UI + Vice City    │        │  cli/leonida.py (stdlib)     │
│  SVG map, keyboard + gamepad │        │  list / toggle / events      │
└──────────────┬───────────────┘        └──────────────┬───────────────┘
               │ fetch / poll (2s)                     │ REST
               ▼                                       ▼
┌──────────────────────────────┐        ┌──────────────────────────────┐
│  Mock Flagsmith API          │        │  Real Flagsmith (optional)   │
│  mock/server.py (stdlib)     │        │  docker.flagsmith.com image  │
│  /api/v1/flags, /toggle      │        │  + Postgres, :8000           │
│  state.json persistence      │        │  Official JS SDK in app.js   │
└──────────────────────────────┘        └──────────────────────────────┘
```

## Design decisions (why judges should care)

1. **Zero-dependency core.** Mock API, CLI and static server are Python stdlib /
   vanilla JS. `python3 mock/server.py` + `python3 -m http.server 3000` runs
   anywhere — no `pip install`, no `npm install`, no build step. Hackathon-proof.
2. **Graceful degradation.** Web app tries Mock API → falls back to LOCAL
   (seed + localStorage). Demo never dies because a server didn't start.
3. **Real SDK path, not a fake.** `connectRealFlagsmith()` loads the official
   `flagsmith` JS SDK and calls `init({ environmentID, api, cacheFlags, onChange })`,
   reading via `hasFeature()` / `getValue()` — exactly the documented pattern.
   Writes in real mode go through REST (server token) or guide to the dashboard.
4. **Per-environment flags.** Production / Staging / Dev each hold independent
   values (like real Flagsmith environments). Switching tabs re-evaluates live.
5. **Polling mirrors the SDK.** 2s poll + `onChange`-style re-render means a
   CLI flip appears on the web dashboard without refresh — the "live" feel.
6. **Gamepad + keyboard first.** PS5 UI conventions (D-pad, ✕ to toggle) via
   Gamepad API + arrow keys. The demo is operable without a mouse.

## Flag → world mapping

| Flag | World effect |
|------|--------------|
| `leonida_expansion` | Leonida Keys + Port Gellhorn unlock |
| `neon_nights_event` | Night overlay + event banner |
| `hurricane_ian` | Rain layer + storm banner |
| `double_xp_weekend` | XP multiplier ×2 |
| `ps5_beta_access` | Player count + 4K/120Hz badge |
| `police_pursuit_ai` | Police layer + 5-star wanted |
| `lowrider_culture_pack` | Car-meet marker |
| `crossplay_enabled` | Player count ×3 (PS5+Xbox+PC) |
| `new_weapon_smg` | Loadout event (log + toast) |
| `traffic_density_high` | Traffic count + speed |

## Adding your own flag (3 steps)

1. Add an entry to `seed-flags.json` (name, description, per-env values).
2. Restart the mock API (`python3 mock/server.py`) — it picks up new flags.
3. In `app.js`, add one line to `renderMap()` mapping the flag to a DOM effect.

That's it. No build, no deploy.
