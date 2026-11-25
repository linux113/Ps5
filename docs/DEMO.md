# 🎬 2-Minute Judge Demo Script — LEONIDA LIVE

> Goal: make the judge *feel* feature flags in 30 seconds. Everything below is
> one click or one keypress. No signup, no waiting for a build.

## Setup (before judges arrive, 20 seconds)

```bash
# Terminal 1 — mock Flagsmith API (shared state for web + CLI)
python3 mock/server.py

# Terminal 2 — the app
python3 -m http.server 3000
# open http://localhost:3000
```

Or one command: `docker compose up` → http://localhost:3000

## The pitch (say this verbatim)

> "Rockstar ships GTA VI on PS5. A new island, a hurricane, a double-XP
> weekend — how do they ship that to 10 million players without a patch?
> **Feature flags.** This is LEONIDA LIVE: the live-ops command center.
> Every toggle here is a real Flagsmith flag. Flip one — the world changes
> instantly. No restart. No app update."

## Demo beats

| # | Do this | Say this | Judge sees |
|---|---------|----------|------------|
| 1 | Open the page | "This map is Vice City. Locked islands at the bottom." | PS5-style UI, Leonida Keys greyed + 🔒 |
| 2 | Flip **leonida_expansion** (or press `1`) | "One flag. New islands, new heists — live for everyone." | Keys + Port Gellhorn unlock with glow, players +5,200 |
| 3 | Flip **neon_nights_event** | "Weekend event. Night falls over the city." | Night overlay, neon banner, sun dims |
| 4 | Flip **hurricane_ian** | "Weather system. No patch." | Rain + storm banner |
| 5 | Flip **double_xp_weekend** | "Economy lever. XP doubles." | XP ×2 in yellow |
| 6 | Flip **police_pursuit_ai** | "Gameplay AI. Wanted level jumps." | Police + helicopter + ★★★★★ |
| 7 | Switch tab to **Staging** | "Same flags, different environment. Prod stays safe." | Different flag values per env |
| 8 | Open terminal: `python3 cli/leonida.py --list` then flip one there | "Producers don't need the browser. Terminal dashboard, same state." | CLI flip → web updates in <2s (polling) |
| 9 | Click **⚙ Connect Flagsmith** | "And this is the real thing — official Flagsmith JS SDK, `init` + `onChange`. Self-host it with `docker compose --profile real up`." | Real SDK code path |

## If something breaks

- **Mock API not running?** The app auto-falls back to LOCAL MODE — keep demoing.
- **No internet?** LOCAL MODE needs zero network. Everything still works.
- **Judge asks "is this real Flagsmith?"** Point at `app.js` → `connectRealFlagsmith()`:
  `flagsmith.init({ environmentID, api, cacheFlags:true, onChange })` — the official pattern.
  And `docker-compose.yml` profile `real` runs the genuine Flagsmith image + Postgres.

## Closing line

> "Getting Flagsmith running was the start, not the project. We built the
> thing we wished existed while setting it up — packaged so anyone can run
> it in one command, with zero setup. Flip a flag. Change Vice City."
