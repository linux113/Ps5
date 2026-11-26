"""Build the 1080x1920 thumbnail for the 9:16 cut.

Grabs a hero frame from the finished vertical MP4 and lays a scrim + the
film's line over it, using the repo's Noto Devanagari fonts.

    .venv/bin/python make_thumb_vertical.py
"""
import glob
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FF = glob.glob(".venv/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-*")[0]
SRC = "output/Angoor_Khatte_Hain_VERTICAL_9x16.mp4"
OUT = "output/thumbnail_vertical.jpg"
HERO_T = 11.2          # the mid-leap frame
FONT_DIR = "fonts"


def font(size, weight="Bold"):
    for name in (f"NotoSansDevanagari-{weight}.ttf",
                 f"NotoSansDevanagari_{weight}.ttf",
                 f"NotoSansDevanagari-{weight}.otf"):
        p = os.path.join(FONT_DIR, name)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    for p in glob.glob(f"{FONT_DIR}/*Devanagari*"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def grab(t, path):
    subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", str(t), "-i", SRC, "-frames:v", "1", path],
                   check=True)
    return Image.open(path).convert("RGB")


def center(draw, y, text, fnt, fill, stroke=0, stroke_fill=None):
    w = draw.textlength(text, font=fnt)
    x = (1080 - w) / 2
    draw.text((x, y), text, font=fnt, fill=fill,
              stroke_width=stroke, stroke_fill=stroke_fill)
    return y + fnt.size * 1.45


def main():
    img = grab(HERO_T, tempfile.mktemp(suffix=".png"))

    # --- vignette + bottom scrim so the type always reads -------------------
    scrim = Image.new("L", (1, 1920), 0)
    sd = ImageDraw.Draw(scrim)
    for y in range(1920):
        v = 0
        if y < 620:                       # top scrim for the kicker
            v = int(150 * max(0.0, (620 - y) / 620) ** 1.5)
        if y > 1060:                      # bottom scrim for the headline
            v = max(v, int(215 * min(1.0, (y - 1060) / 720) ** 0.85))
        sd.point((0, y), fill=v)
    scrim = scrim.resize((1080, 1920))
    img = Image.composite(Image.new("RGB", (1080, 1920), (4, 6, 4)), img, scrim)

    d = ImageDraw.Draw(img)

    # --- top kicker -------------------------------------------------------
    f_kick = font(34, "SemiBold")
    kick = "एक  हिंदी  कहानी"
    kw = d.textlength(kick, font=f_kick)
    ky = 150
    d.text(((1080 - kw) / 2, ky), kick, font=f_kick, fill=(226, 191, 120))
    d.line([(540 - kw / 2, ky + 62), (540 + kw / 2, ky + 62)],
           fill=(190, 152, 78), width=2)

    # --- headline ---------------------------------------------------------
    y = 1290
    l1 = font(64, "SemiBold")
    l2 = font(82, "Bold")
    y = center(d, y, "अंगूर खट्टे नहीं थे —", l1, (246, 242, 234), 3, (10, 12, 9))
    y = center(d, y + 6, "बस पहुँच से बाहर थे।", l2, (247, 205, 122), 4, (12, 14, 10))

    # --- bottom bar -------------------------------------------------------
    f_small = font(30, "Regular")
    tag = "THE FOX & THE GRAPES"
    tw = d.textlength(tag, font=f_small)
    d.text(((1080 - tw) / 2, 1750), tag, font=f_small, fill=(176, 184, 170))
    dur = "53 सेकंड"
    dw = d.textlength(dur, font=f_small)
    d.text(((1080 - dw) / 2, 1800), dur, font=f_small, fill=(140, 148, 134))

    # subtle bloom on the highlights, then a little sharpen for phone screens
    blur = img.filter(ImageFilter.GaussianBlur(12))
    img = Image.blend(img, Image.blend(img, blur, 0.35), 0.28)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=55, threshold=3))

    img.save(OUT, quality=90, optimize=True)
    print("wrote", OUT, img.size, os.path.getsize(OUT) // 1024, "KB")


if __name__ == "__main__":
    main()
