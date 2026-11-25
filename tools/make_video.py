#!/usr/bin/env python3
"""Build LEONIDA LIVE demo video (slides + narration) -> assets/demo.mp4
Uses PIL for slides + imageio-ffmpeg binary for muxing. Stdlib + pillow only.
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = os.path.join(ROOT, "assets")
W, H = 1280, 720

def font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def cover(img_path, w=W, h=H):
    im = Image.open(img_path).convert("RGB")
    s = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    x = (im.width - w) // 2; y = (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))

def slide(base_img, title, sub, accent="#ff2e88"):
    im = cover(base_img) if base_img else Image.new("RGB", (W, H), (10, 10, 18))
    d = ImageDraw.Draw(im, "RGBA")
    # bottom gradient bar
    for i in range(220):
        d.line([(0, H - 220 + i), (W, H - 220 + i)], fill=(5, 5, 12, int(200 * i / 220)))
    # accent line
    d.rectangle([0, H - 228, W, H - 222], fill=accent)
    d.text((48, H - 190), title, font=font(52), fill=(255, 255, 255))
    # wrap sub
    words, lines, cur = sub.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=font(30)) > W - 96:
            lines.append(cur); cur = w_
        else:
            cur = t
    if cur: lines.append(cur)
    y = H - 110
    for ln in lines[:3]:
        d.text((48, y), ln, font=font(30), fill=(200, 210, 230)); y += 40
    # top-left badge
    d.rounded_rectangle([36, 30, 300, 78], 12, fill=(0, 112, 209, 230))
    d.text((56, 42), "LEONIDA LIVE  |  PS5", font=font(24), fill=(255, 255, 255))
    return im

slides = [
    (os.path.join(A, "hero.png"), "LEONIDA LIVE", "Flip a flag. Change Vice City. Instantly.", "#ff2e88"),
    (os.path.join(A, "dashboard.png"), "The problem?", "Shipping GTA VI updates to millions of PS5 players without a patch.", "#00e5ff"),
    (os.path.join(A, "map-unlocked.png"), "Flag: leonida_expansion", "Leonida Keys + Port Gellhorn unlock live. No restart.", "#ff2e88"),
    (os.path.join(A, "hero.png"), "Events + weather", "neon_nights_event: night falls.  hurricane_ian: rain rolls in.", "#7b2fff"),
    (os.path.join(A, "dashboard.png"), "Economy + gameplay", "double_xp_weekend: XP x2.  police_pursuit_ai: 5-star wanted.", "#ffd166"),
    (os.path.join(A, "map-unlocked.png"), "Environments + CLI", "Production / Staging / Dev. Terminal flips update the web live.", "#00e5ff"),
    (os.path.join(A, "hero.png"), "Flip a flag. Change Vice City.", "docker compose up  |  Built on self-hosted Flagsmith", "#ff2e88"),
]
os.makedirs(os.path.join(A, "frames"), exist_ok=True)
for i, (img, t, s, acc) in enumerate(slides):
    slide(img, t, s, acc).save(os.path.join(A, "frames", f"slide{i}.png"))
    print(f"slide {i}: {t}")

# Build video: each slide ~7.4s (total ~52s matching narration)
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()
frames = [os.path.join(A, "frames", f"slide{i}.png") for i in range(len(slides))]
# concat demuxer
lst = os.path.join(A, "frames", "list.txt")
with open(lst, "w") as f:
    for fr in frames:
        f.write(f"file '{fr}'\nduration 7.4\n")
    f.write(f"file '{frames[-1]}'\n")
out = os.path.join(A, "demo.mp4")
cmd = [FF, "-y", "-f", "concat", "-safe", "0", "-i", lst,
       "-i", os.path.join(A, "narration.mp3"),
       "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
       "-c:a", "aac", "-shortest", out]
print(" ".join(cmd))
r = subprocess.run(cmd, capture_output=True, text=True)
print(r.stderr[-800:])
print("OK ->", out, os.path.getsize(out) // 1024, "KB")
