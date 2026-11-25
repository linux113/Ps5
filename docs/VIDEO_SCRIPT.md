# 🎬 Demo Video — LEONIDA LIVE

> ✅ **Ready video: [`assets/demo.mp4`](../assets/demo.mp4)** (52s, 1280×720, narration included).
> Rebuild anytime: `python3 tools/make_video.py` (needs `pip install pillow imageio imageio-ffmpeg`).
> For a live screen-recording version, use the shot list below.

## Setup (do this before recording)

```bash
python3 mock/server.py          # Terminal 1
python3 -m http.server 3000     # Terminal 2
# Open http://localhost:3000, reset flags (↺ Reset button)
# Zoom browser to 110%, close extra tabs, hide bookmarks bar
```

## Shot list (record in order, one take is fine)

| Time | On screen | Say / do |
|------|-----------|----------|
| 0:00–0:15 | Hero: Vice City map, locked islands | "Rockstar ships GTA VI on PS5. New island? Hurricane? Double XP? They don't ship a patch — they flip a feature flag. This is LEONIDA LIVE." |
| 0:15–0:45 | Flip `leonida_expansion` (press `1`) | "One flag. Leonida Keys and Port Gellhorn unlock — live, for everyone. No restart." |
| 0:45–1:05 | Flip `neon_nights_event` + `hurricane_ian` | "Weekend event — night falls. Weather system — rain rolls in. All flags, all live." |
| 1:05–1:20 | Flip `double_xp_weekend` + `police_pursuit_ai` | "Economy lever, XP doubles. Gameplay AI — five-star wanted. Every pixel is driven by Flagsmith." |
| 1:20–1:35 | Switch Production → Staging tab | "Same flags, different environment. Production stays safe while staging experiments." |
| 1:35–1:50 | Terminal: `python3 cli/leonida.py --list`, flip one | "Producers don't need the browser. Terminal dashboard, same shared state — watch the web update." |
| 1:50–2:00 | Back to web, closing | "One command to run it. Built on self-hosted Flagsmith. Flip a flag. Change Vice City." |

## Recording tips (solo, phone or laptop)

- **Laptop:** OBS Studio (free) or Windows `Win+G` / Mac `Cmd+Shift+5`. Record screen + mic, or screen + `assets/narration.mp3` as voiceover.
- **Phone:** film the monitor straight-on, good light, no glare. Works fine.
- Record **twice**, keep the better take. Judges forgive small mistakes — they don't forgive a video that doesn't show the flip.
- Upload to YouTube (unlisted) or GitHub Releases, paste the link in your submission + README.

## If the mock API fails during recording

Don't stop. The app falls back to LOCAL MODE automatically — keep flipping.
Say: *"Offline fallback — still fully live."* Judges respect recovery.
