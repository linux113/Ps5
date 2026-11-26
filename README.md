# अंगूर खट्टे हैं — The Fox & The Grapes

Animated Hindi short built from the fable — fully animated character
performance, cinematic camera moves, VFX, sound design and a real Hindi male
voiceover with a processed film tone. Ships in **16:9 (55 s)** and
**9:16 vertical (53.4 s, re-composed for Reels/Shorts)**.

## ▶ Final videos — two cuts

| Cut | File | Spec | For |
|-----|------|------|-----|
| **9:16 vertical** | `output/Angoor_Khatte_Hain_VERTICAL_9x16.mp4` | 53.4 s · 1080×1920 · 30 fps · 22 MB · −13.6 LUFS | Reels · Shorts · TikTok |
| 16:9 landscape | `output/Angoor_Khatte_Hain_LIVE_ANIMATION.mp4` | 55 s · 1920×1080 · 30 fps · 31 MB · −13.5 LUFS | YouTube · web |

Thumbnails: `output/thumbnail_vertical.jpg` (1080×1920), `output/thumbnail_live.jpg` (1280×720).

The vertical cut is **not a crop** — every shot was re-composed for the tall frame
(fox low in frame with headroom, grapes in the upper third, vertical type stacks).

### Short links

| Link | Serves |
|------|--------|
| `/reel` · `/vertical` · `/shorts` | 9:16 file (forced download) |
| `/download` · `/dl` | 16:9 file (forced download) |
| `/video` | redirect for in-tab playback |

### Download / play

```bash
.venv/bin/python serve_output.py 8000     # HTTP Range enabled (seek + resume)
# open http://localhost:8000/   -> big Download button + player
```

`output/index.html` has a large **Download MP4** button, a new-tab link, a
thumbnail download, and a "Save video as…" fallback note. Range requests are
tested: `206 Partial Content` with a correct `Content-Range` header.

## What makes it animation (not slideshow)

| Layer | Implementation |
|-------|----------------|
| Character | 7 cutout fox poses (stand / reach / jump / sad / sit / run / shock) composited as an **actor** with feet-anchored ground contact |
| Acting | Anticipation crouch → stretch on launch → squash on landing, idle breathing (squash+stretch), tail sway, run bob, motion-blur afterimages |
| Camera | Per-shot authored moves: push-ins, trucks, whip pans, low-angle jump coverage, hero wide — all in plate space with parallax |
| VFX | Volumetric god rays, dust motes, fireflies, magic sparks, impact rings, speed streaks, camera shake, chromatic aberration on impacts, bloom, film grain, vignette |
| **Realistic VFX pass (9:16)** | Depth of field with per-shot focus masks, physical lens flare (hexagonal ghosts + starburst + anamorphic streaks), halation on light sources only, 3-depth volumetric fog, atmospheric haze, highlight roll-off, rolling-shutter micro jitter |
| **Sound FX (9:16)** | Sub-drop + riser on every cut, leap whooshes, landing thuds, cloth/fur rustle, paw taps, leaf rustle, keyboard clacks, chair creak, paper slam, mug clink, breath puffs, reversed magic swell, glass chimes |
| Editing | 11 shots cut on narration beats, punch-in sub-cuts, whip transitions, colour-grade changes per act (warm forest → cold office → gold sunrise → violet magic) |
| Sound | Narration-first mix: male voice pitched −4 % with mud cut + 1.6–4.5 kHz presence lift + 3.2:1 compression; per-sample side-chain ducks the bed by up to −21 dB and carves 350–3500 Hz while speaking (**dialog SNR +15.3 dB**, was +4.8); music/SFX return to full level between lines; bus limiter → loudnorm −14 LUFS |

## Story / script (voiceover)

> एक लोमड़ी को जंगल में अंगूरों की एक बेल दिखी।
> उसने पूरी कोशिश की... ऊपर कूदी, बार-बार कूदी।
> लेकिन अंगूर उसकी पहुँच से बाहर थे।
> तो उसने मुँह बनाकर कह दिया — अंगूर खट्टे हैं!
> आज भी कुछ लोग ऐसे हैं, जब कुछ हासिल नहीं कर पाते, तो अपनी असफलता दूसरों पर थोपते हैं।
> किसी को बर्बाद करके, आप खुद कामयाब नहीं हो सकते।
> दूसरों की बुराई करने से बेहतर है — अपनी कमियों को सुधारना।
> याद रखना... अंगूर खट्टे नहीं थे — बस लोमड़ी की पहुँच से बाहर थे।

*Note: the source transcript read “अंकुर खाते हैं” (ASR error); the film uses
the correct fable line “अंगूर खट्टे हैं”.*

## Shot list

| # | Time | Shot | Narration |
|---|------|------|-----------|
| 1 | 0.0–4.2 | Title over forest, god rays + haze | — |
| 2 | 4.2–10.6 | Wide reveal, fox trots in, notices the vine | “एक लोमड़ी को… बेल दिखी” |
| 3 | 10.6–13.2 | Low-angle jump attempt #1 (squash/stretch, impact ring) | “उसने पूरी कोशिश की…” |
| 4 | 13.2–16.2 | Tighter jump #2 — misses, shock pose | “ऊपर कूदी, बार-बार कूदी” |
| 5 | 16.2–20.0 | Reach-and-fail, grapes glow out of reach | “पहुँच से बाहर थे” |
| 6 | 20.0–25.3 | The lie: “अंगूर खट्टे हैं!” stamp, red grade | “अंगूर खट्टे हैं!” |
| 7 | 25.3–32.5 | Office blame parallel — cold grade, callout | “आज भी कुछ लोग ऐसे हैं…” |
| 8 | 32.5–38.2 | Fox turns her back and runs off | “किसी को बर्बाद करके…” |
| 9 | 38.2–42.4 | Sunrise training: jumps, sun flare, backlight | “अपनी कमियों को सुधारना” |
| 10 | 42.4–49.1 | Magic dusk — grapes truly glow, sparkles, fireflies | “अंगूर खट्टे नहीं थे…” |
| 11 | 49.1–55.0 | Moral card, pill typography, fade out | “बस पहुँच से बाहर थे” |

## Files

```
assets2/                    art for the animated cut
  bg_forest.jpg             sunny forest plate (vine + path)
  bg_sunrise.jpg            golden hills plate
  bg_dusk.jpg               magical violet forest plate
  fox_*.jpg                 white-bg pose plates (stand/jump/sad/sit/reach/run/shock)
  cut/*.png                 soft-alpha cutouts used by the renderer
audio2/v01..v10.mp3         narration cues (same voice, 10 beats)
work_audio/                 generated music, SFX, ambience, voice, final mix
build_anim.py               animation renderer, 16:9 (PIL + NumPy → raw frames → ffmpeg)
build_vertical.py           9:16 renderer — re-composed shots + realistic VFX pass
cutout_fox.py               plate → alpha cutout (flood-fill + feather + de-fringe)
make_sfx_music.py           procedural score + sound design, 16:9 (numpy synth)
make_sfx_vertical.py        sound design for the 9:16 cut (cut-punctuation FX)
mix_final.py                voice EQ/compression, side-chain duck, limiter (16:9)
mix_vertical.py             phone-tuned voice + punchier FX, side-chain duck (9:16)
serve_output.py             static server with HTTP Range support (206) for seek/resume
build_video.py              legacy Ken-Burns version (kept for reference)
output/                     deliverables
```

## Rebuild

```bash
python3 -m venv .venv
.venv/bin/pip install pillow numpy imageio-ffmpeg opencv-python-headless
.venv/bin/python cutout_fox.py        # pose plates -> alpha cutouts
.venv/bin/python make_sfx_music.py    # music + SFX + ambience (55 s)
.venv/bin/python mix_final.py         # voice processing + final mix
.venv/bin/python build_anim.py full   # render 1650 frames -> work/render/video_only.mp4
FF=.venv/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2
# ---- 9:16 vertical cut ----
.venv/bin/python make_sfx_vertical.py
.venv/bin/python mix_vertical.py
.venv/bin/python build_vertical.py full     # 1602 frames -> work/render_v/video_v.mp4
$FF -i work_audio_v/final_mix.wav -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
    -ar 48000 -ac 2 work_audio_v/final_master.wav
$FF -i work/render_v/video_v.mp4 -i work_audio_v/final_master.wav \
    -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 256k \
    -movflags +faststart output/Angoor_Khatte_Hain_VERTICAL_9x16.mp4
# optional: shrink for upload
$FF -i output/Angoor_Khatte_Hain_VERTICAL_9x16.mp4 -c:v libx264 -preset slow \
    -crf 22 -c:a copy -movflags +faststart /tmp/small.mp4

# ---- 16:9 landscape cut ----
# loudness-normalise the mix, then mux
$FF -i work_audio/final_mix.wav -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
    -ar 48000 -ac 2 work_audio/final_master.wav
$FF -i work/render/video_only.mp4 -i work_audio/final_master.wav \
    -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 256k \
    -movflags +faststart output/Angoor_Khatte_Hain_LIVE_ANIMATION.mp4
```
