# अंगूर खट्टे हैं — The Fox & The Grapes

A 55-second live **2.5D animation** (1920×1080 · 30 fps · 2.35:1 letterbox) built
from the Hindi fable — fully animated character performance, cinematic camera
moves, VFX, sound design and a real Hindi male voiceover with a processed film
tone.

## ▶ Final video

**`output/Angoor_Khatte_Hain_LIVE_ANIMATION.mp4`** — 55 s, H.264 + AAC 48 kHz,
`+faststart`, **−13.5 LUFS / −1.5 dBTP**, YouTube-ready.
Thumbnail: `output/thumbnail_live.jpg`.

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
| VFX | Volumetric god rays, dust motes, fireflies, magic sparks, impact rings, speed streaks, camera shake, chromatic aberration on impacts, bloom, film grain, vignette, 2.35:1 letterbox |
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
build_anim.py               animation renderer (PIL + NumPy → raw frames → ffmpeg)
cutout_fox.py               plate → alpha cutout (flood-fill + feather + de-fringe)
make_sfx_music.py           procedural score + sound design (numpy synth)
mix_final.py                voice EQ/compression, side-chain duck, limiter, loudness report
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
# loudness-normalise the mix, then mux
$FF -i work_audio/final_mix.wav -af "loudnorm=I=-14:TP=-1.5:LRA=11" \
    -ar 48000 -ac 2 work_audio/final_master.wav
$FF -i work/render/video_only.mp4 -i work_audio/final_master.wav \
    -map 0:v:0 -map 1:a:0 -c:v copy -c:a aac -b:a 256k \
    -movflags +faststart output/Angoor_Khatte_Hain_LIVE_ANIMATION.mp4
```
