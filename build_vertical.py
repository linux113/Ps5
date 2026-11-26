#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANGOOR KHATTE HAIN — 9:16 vertical edition
==========================================
1080 x 1920 · 30 fps · 53.4 s · 11 shots

Rebuilt for a phone-first frame:
  * every shot is re-composed for 9:16 (tall, headroom-rich, subject centred)
  * fox actor keeps squash/stretch, anticipation, landing impacts, run bob
  * camera language re-authored for vertical: push-ins, vertical trucks,
    low-angle hero shots, whip cuts
  * new realistic VFX pass
      - depth of field (blurred far + near layers, focus pulls)
      - physical lens flare (hexagonal ghosts, starburst, veiling glare)
      - halation / highlight bleed around bright sources
      - layered volumetric fog drifting at three depths
      - atmospheric haze that increases with distance
      - rolling-shutter-style micro jitter on impacts
      - per-shot colour science (teal-orange, bleach bypass, night-for-night)
"""
import os, math, sys, subprocess, random, json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 53.4
NF = int(round(DUR*FPS))
FF = ".venv/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2"
OUT = "work/render_v"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(11)
random.seed(11)

def log(*a): print(*a, flush=True)
def cl(x, a=0.0, b=1.0): return a if x < a else (b if x > b else x)
def smooth(x): x = cl(x); return x*x*(3-2*x)
def eio(x): x = cl(x); return 0.5-0.5*math.cos(math.pi*x)
def eout(x, p=2.0): return 1-(1-cl(x))**p
def ein(x, p=2.0): return cl(x)**p
def L(a, b, t): return a+(b-a)*t
def ramp(t, a, b): return 0.0 if t <= a else (1.0 if t >= b else smooth((t-a)/(b-a)))
def win(t, a, b, c, d): return min(ramp(t, a, b), 1-ramp(t, c, d))

def rgb(p): return np.asarray(Image.open(p).convert("RGB"), np.float32)/255.
def rgba(p): return np.asarray(Image.open(p).convert("RGBA"), np.float32)/255.
def rs(im, w, h, f=Image.BILINEAR):
    mode = "RGBA" if im.shape[2] == 4 else "RGB"
    return np.asarray(Image.fromarray((np.clip(im, 0, 1)*255).astype(np.uint8), mode)
                      .resize((max(2, int(w)), max(2, int(h))), f), np.float32)/255.

# ------------------------------------------------------------------ plates
PAD = 420          # generous pad: vertical crops travel far
class Plate:
    def __init__(self, path, scale=2.4, ew=0, eh=0):
        im = rgb(path); ih, iw = im.shape[:2]
        big = Image.fromarray((im*255).astype(np.uint8)).resize(
            (int(iw*scale)+ew, int(ih*scale)+eh), Image.LANCZOS)
        cv = Image.new("RGB", (big.width+2*PAD, big.height+2*PAD), (7, 11, 8))
        cv.paste(big, (PAD, PAD))
        self.img = np.asarray(cv, np.float32)/255.
        self.scale = scale; self.w, self.h = iw, ih
    def M(self, px, py): return PAD+px*self.scale, PAD+py*self.scale

FOREST = Plate("assets2/bg_forest.jpg", 2.4, 120, 100)
DUSK   = Plate("assets2/bg_dusk.jpg",   2.4, 100, 100)
SUN    = Plate("assets2/bg_sunrise.jpg",2.4, 160, 120)
OFFICE = Plate("assets/scene4_people_blame.jpg", 2.4, 100, 100)
log("plates", FOREST.img.shape, DUSK.img.shape, SUN.img.shape, OFFICE.img.shape)

FOX = {n: rgba(f"assets2/cut/{n}.png") for n in
       ["fox_stand", "fox_jump", "fox_sad", "fox_sit", "fox_reach", "fox_run", "fox_shock"]}
_fc = {}
def foximg(pose, h):
    k = (pose, int(h))
    if k not in _fc:
        im = FOX[pose]; s = h/im.shape[0]
        _fc[k] = rs(im, im.shape[1]*s, h, Image.LANCZOS)
    return _fc[k]

def crop(img, x, y, w, h):
    ih, iw = img.shape[:2]
    x, y, w, h = int(x), int(y), int(w), int(h)
    xs = np.clip(x+np.arange(w), 0, iw-1); ys = np.clip(y+np.arange(h), 0, ih-1)
    return img[ys][:, xs]

def blit(dst, src, x, y, a=1.0, additive=False):
    h, w = src.shape[:2]; H_, W_ = dst.shape[:2]
    x, y = int(round(x)), int(round(y))
    dx0, dy0, dx1, dy1 = max(0, x), max(0, y), min(W_, x+w), min(H_, y+h)
    if dx1 <= dx0 or dy1 <= dy0: return
    s = src[dy0-y:dy0-y+(dy1-dy0), dx0-x:dx0-x+(dx1-dx0)]
    al = s[:, :, 3:4]*a
    reg = dst[dy0:dy1, dx0:dx1]
    if additive:
        dst[dy0:dy1, dx0:dx1] = np.clip(reg+s[:, :, :3]*al*0.6, 0, 1)
    else:
        dst[dy0:dy1, dx0:dx1] = reg*(1-al)+s[:, :, :3]*al

# ------------------------------------------------------------------ scene
class Scene:
    def __init__(self, plate, cx, cy, z, shake=0.0):
        self.p = plate; self.cx = cx; self.cy = cy; self.z = z; self.shake = shake
        self.items = []
        self.char_boxes = []      # (x0,y0,x1,y1) screen space, for VFX masking

    def begin(self, img, t):
        mx, my = self.p.M(self.cx, self.cy)
        vw, vh = int(round(W/self.z)), int(round(H/self.z))
        shx = math.sin(t*53)*self.shake; shy = math.cos(t*41)*self.shake
        sub = crop(self.p.img, mx-vw/2+shx, my-vh/2+shy, vw, vh)
        if (vw, vh) != (W, H):
            img[...] = rs(sub, W, H, Image.BICUBIC)
        else:
            img[...] = sub
        return img

    def scr(self, px, py):
        mx, my = self.p.M(px, py)
        cx, cy = self.p.M(self.cx, self.cy)
        return (mx-(cx-W/(2*self.z)))*self.z, (my-(cy-H/(2*self.z)))*self.z

    def fox(self, pose, x, y, h, alpha=1.0, flip=False, sx=1., sy=1., rot=0., blur=0.,
            shadow=True, rim=True):
        self.items.append(("fox", dict(pose=pose, x=x, y=y, h=h, alpha=alpha, flip=flip,
                                       sx=sx, sy=sy, rot=rot, blur=blur, shadow=shadow, rim=rim)))
    def sprite(self, im, x, y, h, alpha=1., blobur=0.):
        self.items.append(("spr", dict(im=im, x=x, y=y, h=h, alpha=alpha, blur=blobur)))

    def finish(self, img, t):
        for kind, p in self.items:
            (self._fox if kind == "fox" else self._spr)(img, p)
        return img

    def _fox(self, img, p):
        im = foximg(p["pose"], p["h"])
        if p["flip"]: im = im[:, ::-1]
        if abs(p["sx"]-1) > .004 or abs(p["sy"]-1) > .004:
            im = rs(im, im.shape[1]*p["sx"], im.shape[0]*p["sy"])
        if abs(p["rot"]) > .05:
            im = np.asarray(Image.fromarray((np.clip(im, 0, 1)*255).astype(np.uint8), "RGBA")
                            .rotate(p["rot"], Image.BICUBIC, expand=True), np.float32)/255.
        sx, sy = self.scr(p["x"], p["y"])
        if p["shadow"]:
            self._shadow(img, sx, sy, im.shape[1])
        if p["blur"] > .4:
            im = np.asarray(Image.fromarray((np.clip(im, 0, 1)*255).astype(np.uint8), "RGBA")
                            .filter(ImageFilter.GaussianBlur(p["blur"])), np.float32)/255.
        bx0 = sx-im.shape[1]/2; by0 = sy-im.shape[0]
        self.char_boxes.append((bx0-18, by0-18, bx0+im.shape[1]+18, sy+18))
        blit(img, im, bx0, by0, p["alpha"])
        if p["rim"]:
            r = rimlight(im, 0.34)
            if r is not None:
                blit(img, r, sx-im.shape[1]/2, sy-im.shape[0], p["alpha"]*0.7, additive=True)

    def _spr(self, img, p):
        im = p["im"]
        h = int(p["h"]); w = int(im.shape[1]*h/im.shape[0])
        im2 = rs(im, w, h, Image.LANCZOS)
        if p["blur"] > .3:
            im2 = np.asarray(Image.fromarray((np.clip(im2, 0, 1)*255).astype(np.uint8), "RGBA")
                             .filter(ImageFilter.GaussianBlur(p["blur"])), np.float32)/255.
        sx, sy = self.scr(p["x"], p["y"])
        blit(img, im2, sx-w/2, sy-h, p["alpha"])

    def _shadow(self, img, sx, sy, w):
        rx = max(8, w*0.26); ry = max(4, w*0.055)
        H_, W_ = img.shape[:2]
        x0, x1 = max(0, int(sx-rx*2.4)), min(W_, int(sx+rx*2.4))
        y0, y1 = max(0, int(sy-ry*3)), min(H_, int(sy+ry*3))
        if x1 <= x0 or y1 <= y0: return
        yy, xx = np.mgrid[y0:y1, x0:x1]
        d = ((xx-sx)/rx)**2+((yy-sy)/ry)**2
        img[y0:y1, x0:x1] *= (1-np.clip(1-d, 0, 1)**1.5*0.5)[..., None]

_rimk = {}
def rimlight(im, strength=.5):
    a = im[:, :, 3]
    edge = np.abs(np.gradient(a)[0])+np.abs(np.gradient(a)[1])
    e = np.clip(edge*2.2, 0, 1)
    if e.max() < .02: return None
    yy, xx = np.mgrid[0:im.shape[0], 0:im.shape[1]]
    bias = np.clip((xx/im.shape[1]-0.55)/0.30, 0, 1)*np.clip((yy/im.shape[0])*0.35+0.65, 0, 1)
    e = e*bias
    out = np.zeros_like(im)
    out[:, :, 0] = e*.95*strength; out[:, :, 1] = e*.74*strength; out[:, :, 2] = e*.42*strength
    out[:, :, 3] = e*strength
    return out

# ================================================================ VFX (new)
def depth_of_field(img, focus_mask, strength=2.2):
    """Realistic split-focus: blur where focus_mask says 'far/near'.
    focus_mask: float 0..1 (0 = sharp, 1 = fully defocused)."""
    if strength <= .05: return img
    a = np.clip(focus_mask, 0, 1)[..., None]
    pil = Image.fromarray((np.clip(img, 0, 1)*255).astype(np.uint8))
    big = pil.filter(ImageFilter.GaussianBlur(strength*3.6))
    small = pil.filter(ImageFilter.GaussianBlur(strength*1.3))
    b1 = np.asarray(small, np.float32)/255.
    b2 = np.asarray(big, np.float32)/255.
    # two-step blend gives a smoother, more lens-like roll-off
    return img*(1-a)+b1*a*(1-a*0.45)+b2*a*a*0.45

def radial_focus(base, cx, cy, in_focus_r, feather=260):
    """0 in the sharp core, rising to 1 outside (out-of-focus background)."""
    H_, W_ = base.shape[:2]
    yy, xx = np.mgrid[0:H_, 0:W_]
    d = np.sqrt(((xx-cx))**2+((yy-cy))**2)
    return np.clip((d-in_focus_r)/feather, 0, 1)

def top_bottom_focus(base, near_frac=0.30, far_frac=0.32, near_amt=0.85, far_amt=0.55):
    """near foreground (bottom) and far background (top) softly out of focus."""
    H_, W_ = base.shape[:2]
    yy = np.linspace(0, 1, H_)[:, None]*np.ones((1, W_), np.float32)
    far = np.clip((far_frac-yy)/max(far_frac, 1e-3), 0, 1)**1.4*far_amt
    near = np.clip((yy-(1-near_frac))/max(near_frac, 1e-3), 0, 1)**1.4*near_amt
    return np.clip(np.maximum(far, near), 0, 1)

_flare_cache = {}
def lens_flare(img, x, y, strength=1.0, scale=1.0, col=(255, 226, 176), ghosts=7, seed=3):
    """Physical-style flare: core bloom, anamorphic streak, starburst and
    a chain of hexagonal ghosts along the lens axis."""
    H_, W_ = img.shape[:2]
    if strength <= .01: return img
    key = (int(x//6), int(y//6), round(strength, 2), round(scale, 2), ghosts, seed)
    if key in _flare_cache:
        lay = _flare_cache[key]
    else:
        ss = 4
        sw, sh = W_//ss, H_//ss
        lay = np.zeros((sh, sw, 3), np.float32)
        yy, xx = np.mgrid[0:sh, 0:sw]
        cx, cy = x/ss, y/ss
        # --- core + veiling glare
        d = np.sqrt((xx-cx)**2+(yy-cy)**2)
        core = np.clip(1-d/(38*scale), 0, 1)**2.0
        veil = np.clip(1-d/(460*scale), 0, 1)**3.2*0.42
        base = (core+veil)
        # --- starburst: 6 soft spokes + 2 long anamorphic streaks
        ang = np.arctan2(yy-cy, xx-cx)
        for k in range(6):
            a = k*math.pi/3 + 0.13
            lobe = np.exp(-((np.abs(np.sin((ang-a)/2)))**2)*90)
            base += lobe*np.clip(1-d/(300*scale), 0, 1)**2.6*0.30
        base += np.exp(-((yy-cy)/(1.8*scale))**2)*np.clip(1-np.abs(xx-cx)/(560*scale), 0, 1)**2.0*0.30
        base += np.exp(-((xx-cx)/(1.8*scale))**2)*np.clip(1-np.abs(yy-cy)/(520*scale), 0, 1)**2.0*0.16
        # --- hexagonal ghosts mirrored through the frame centre
        r = random.Random(seed)
        for i in range(ghosts):
            t = 0.35+i*0.24+r.uniform(-.05, .05)
            gx = cx+(W_/ss*0.5-cx)*t*1.55
            gy = cy+(H_/ss*0.5-cy)*t*1.55
            rad = (10+i*4.5+r.uniform(-2, 2))*scale
            hexm = np.zeros((sh, sw), np.float32)
            pts = []
            for k in range(6):
                a = k*math.pi/3+0.2
                pts.append((gx+math.cos(a)*rad, gy+math.sin(a)*rad))
            mimg = Image.new("L", (sw, sh), 0)
            ImageDraw.Draw(mimg).polygon(pts, fill=110)
            mimg = mimg.filter(ImageFilter.GaussianBlur(rad*0.40))
            base += (np.asarray(mimg, np.float32)/255.)*(0.55-0.05*i)
        lay[:, :, 0] = base*col[0]/255.
        lay[:, :, 1] = base*col[1]/255.
        lay[:, :, 2] = base*col[2]/255.
        if len(_flare_cache) > 26: _flare_cache.clear()
        _flare_cache[key] = lay
    big = np.asarray(Image.fromarray((np.clip(lay, 0, 1)*255).astype(np.uint8)).resize((W_, H_), Image.BILINEAR), np.float32)/255.
    return np.clip(img+big*strength, 0, 1)

def halation(img, thresh=0.88, amt=0.22, radius=10, tint=(255, 145, 100), mask=None):
    """Film halation: bright light sources bleed a warm halo into the emulsion."""
    lum = img.max(2)
    m = np.clip((lum-thresh)/(1-thresh+1e-6), 0, 1)
    if mask is not None: m = m*mask
    if m.max() < 0.02: return img
    src = (img*m[..., None]*np.array(tint, np.float32)/255.)
    b = np.asarray(Image.fromarray((np.clip(src, 0, 1)*255).astype(np.uint8))
                   .filter(ImageFilter.GaussianBlur(radius)), np.float32)/255.
    return np.clip(img+b*amt, 0, 1)

def fog_layer(img, t, density=0.16, seed=4, speed=1.0, y_bias=0.55, tint=(212, 214, 198)):
    """Layered volumetric fog drifting horizontally."""
    H_, W_ = img.shape[:2]
    r = random.Random(seed)
    key = ("fog", H_, W_, seed)
    if key not in _flare_cache:
        sw, sh = W_//3, H_//3
        acc = np.zeros((sh, sw), np.float32)
        rr = np.random.default_rng(seed)
        for octv, amp in ((6, .55), (12, .28), (26, .17)):
            n = rr.normal(0, 1, (max(2, sh//octv+1), max(2, sw//octv+1))).astype(np.float32)
            n = np.asarray(Image.fromarray(((np.clip(n, -2, 2)+2)*63).astype(np.uint8))
                           .resize((sw, sh), Image.BICUBIC), np.float32)/255.
            acc += n*amp
        acc = np.asarray(Image.fromarray((np.clip(acc, 0, 1)*255).astype(np.uint8))
                         .filter(ImageFilter.GaussianBlur(9)), np.float32)/255.
        _flare_cache[key] = acc
    base = _flare_cache[key]
    Hf, Wf = base.shape
    shift = int((t*speed*22) % Wf)
    tex = np.roll(base, shift, axis=1)
    tex = np.asarray(Image.fromarray((tex*255).astype(np.uint8)).resize((W_, H_), Image.BILINEAR), np.float32)/255.
    yy = np.linspace(0, 1, H_)[:, None]
    grad = np.clip(1-np.abs(yy-y_bias)/0.55, 0, 1)**1.1
    mask = (tex*grad*density)[..., None]
    img = img*(1-mask*0.55)+mask*np.array(tint, np.float32)/255.
    return img

def haze_distance(img, amt=0.10, tint=(198, 208, 196)):
    """Atmospheric perspective: lift blacks towards the top of frame."""
    H_, W_ = img.shape[:2]
    yy = np.linspace(0, 1, H_)[:, None]
    g = np.clip(1-yy/0.62, 0, 1)**1.6*amt
    return np.clip(img*(1-g[..., None])+g[..., None]*np.array(tint, np.float32)/255., 0, 1)

def jitter(img, t, amt, freq=13.0):
    """rolling-shutter style micro shake (sub-pixel, resampled)"""
    if amt < 0.25: return img
    dx = math.sin(t*freq*2*math.pi)*amt
    dy = math.cos(t*freq*1.7*2*math.pi)*amt*0.7
    H_, W_ = img.shape[:2]
    xs = np.clip(np.arange(W_)+dx, 0, W_-1); ys = np.clip(np.arange(H_)+dy, 0, H_-1)
    out = img[ys.astype(int)][:, xs.astype(int)]
    return out

def chroma_aberration(img, amt):
    if amt < .4: return img
    a = int(round(amt))
    return np.dstack([np.roll(img[:, :, 0], a, 1), img[:, :, 1], np.roll(img[:, :, 2], -a, 1)])

def glow(img, cx, cy, r, color, strength=1.0, power=2.2):
    H_, W_ = img.shape[:2]
    x0, x1 = max(0, int(cx-r)), min(W_, int(cx+r)); y0, y1 = max(0, int(cy-r)), min(H_, int(cy+r))
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.sqrt((xx-cx)**2+(yy-cy)**2)/max(r, 1e-3)
    m = np.clip(1-d, 0, 1)**power*strength
    img[y0:y1, x0:x1] += m[..., None]*np.array(color, np.float32)/255.

# god rays adapted to vertical
_rays = {}
def godrays(img, x, y, ang, strength, spread, n=14, color=(255, 228, 168), seed=2):
    H_, W_ = img.shape[:2]
    key = (int(x//12), int(y//12), round(ang, 3), round(spread, 3), n, seed, round(strength, 2))
    if key in _rays:
        lay = _rays[key]
    else:
        sw, sh = W_//4, H_//4
        m = Image.new("L", (sw, sh), 0); d = ImageDraw.Draw(m); rr = random.Random(seed)
        for i in range(n):
            a = ang+(i-(n-1)/2)*(spread/n)*2+rr.uniform(-.012, .012)
            wd = rr.uniform(1.6, 6.2)*(sh/270.)
            ln = max(sw, sh)*2.0
            x0, y0 = x/4, y/4
            for k, wk in enumerate([.35, .7, 1.]):
                d.line([(x0, y0), (x0+math.cos(a)*ln, y0+math.sin(a)*ln)],
                       fill=int(112*wk), width=max(2, int(wd*wk*2)))
        m = m.filter(ImageFilter.GaussianBlur(max(2., wd*2.5)))
        arr = np.asarray(m, np.float32)/255.
        yy = np.linspace(0, 1, sh)[:, None]
        arr *= np.clip(1.25-yy*.9, 0, 1)
        nz = rng.normal(0, 1, (max(2, sh//6), max(2, sw//6))).astype(np.float32)
        nz = np.asarray(Image.fromarray(((np.clip(nz, -2, 2)+2)*63).astype(np.uint8))
                        .resize((sw, sh), Image.BILINEAR), np.float32)/255.
        arr *= (.80+.42*nz)
        if len(_rays) > 40: _rays.clear()
        _rays[key] = arr
        lay = arr
    lay = np.asarray(Image.fromarray((np.clip(lay, 0, 1)*255).astype(np.uint8))
                     .resize((W_, H_), Image.BILINEAR), np.float32)/255.
    img += (lay*strength)[..., None]*np.array(color, np.float32)/255.

class Motes:
    def __init__(self, n, seed, y0=0., y1=1., speed=1.):
        r = np.random.default_rng(seed)
        self.x = r.uniform(0, W, n); self.y = r.uniform(y0*H, y1*H, n)
        self.z = r.uniform(.28, 1., n); self.vx = r.uniform(-9, 15, n)
        self.vy = r.uniform(-24, -4, n)*speed
        self.ph = r.uniform(0, 6.283, n); self.sp = r.uniform(.5, 1.7, n); self.n = n
    def draw(self, img, t, amp=1., size=2.4, color=(255, 236, 180)):
        col = np.array(color, np.float32)/255.
        for i in range(self.n):
            a = amp*self.z[i]*(.45+.55*math.sin(t*self.sp[i]+self.ph[i]))*.6
            if a <= .02: continue
            x, y = int(self.x[i]), int(self.y[i]); r = int(size*self.z[i])+1
            if 0 <= y < H and 0 <= x < W:
                yi0, yi1 = max(0, y-r), min(H, y+r+1); xi0, xi1 = max(0, x-r), min(W, x+r+1)
                img[yi0:yi1, xi0:xi1] = np.clip(img[yi0:yi1, xi0:xi1]+a*col*.55, 0, 1)

MOTES = Motes(210, 3); MOTES2 = Motes(110, 8, .4, 1.); FIRE = Motes(80, 15, .35, .95)

def sparkle_field(img, seeds, t, amp=1., color=(255, 224, 130)):
    for (x, y, ph, sp, rad) in seeds:
        k = .5+.5*math.sin(t*sp+ph)
        if k < .22: continue
        glow(img, x, y, rad*(.7+.5*k), color, .85*k*amp, 2.4)

def mk_sparks(n, seed, x0, x1, y0, y1):
    r = random.Random(seed)
    return [(r.uniform(x0, x1), r.uniform(y0, y1), r.uniform(0, 6.28),
             r.uniform(1.2, 3.8), r.uniform(10, 34)) for _ in range(n)]

def impact(img, cx, cy, dt, strength=1.0):
    if dt < 0 or dt > .55: return
    p = dt/.55; rad = 40+620*eout(p)
    H_, W_ = img.shape[:2]
    x0, x1 = max(0, int(cx-rad-26)), min(W_, int(cx+rad+26))
    y0, y1 = max(0, int(cy-rad*.8-26)), min(H_, int(cy+rad*.8+26))
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.sqrt((xx-cx)**2+((yy-cy)/.72)**2)
    img[y0:y1, x0:x1] += (np.exp(-((d-rad)/26.)**2)*(1-p)**1.5*strength)[..., None]*np.array([1., .93, .75], np.float32)

def speed_streaks(img, cx, cy, t, amt, n=16, color=(255, 246, 222)):
    if amt <= .01: return
    r = random.Random(int(t*9)); H_, W_ = img.shape[:2]
    lay = np.zeros((H_, W_), np.float32)
    for i in range(n):
        a = r.uniform(0, 6.283); rr = r.uniform(340, 860); ln = r.uniform(110, 320)
        x0, y0 = cx+math.cos(a)*rr, cy+math.sin(a)*rr*1.15
        for k in range(int(ln/5)):
            u = k/(ln/5); px = int(x0+math.cos(a)*ln*u); py = int(y0+math.sin(a)*ln*u)
            if 0 <= px < W and 0 <= py < H:
                lay[max(0, py-2):py+2, max(0, px-2):px+2] += amt*(1-u)*.13
    img += np.clip(lay, 0, 1)[..., None]*np.array(color, np.float32)/255.

# ------------------------------------------------------------ grading
def grade(img, warm=1., contrast=1.08, sat=1.06, lift=0., mode="normal"):
    img = np.clip(img, 0, 1)
    img = img*img*(3-2*img)*.40+img*.60
    img = (img-.5)*contrast+.5+lift
    lum = img@np.array([.299, .587, .114], np.float32)
    img = lum[..., None]+(img-lum[..., None])*sat
    if mode == "teal_orange":
        sh = np.clip(1-lum*2.4, 0, 1)[..., None]; hl = np.clip(lum*1.8-.30, 0, 1)[..., None]
        img = img+sh*np.array([-.030, .004, .044], np.float32)
        img = img+hl*np.array([.042, .014, -.026], np.float32)*warm
    elif mode == "bleach":
        g = img.mean(2, keepdims=True)
        img = np.clip(img*0.72+g*0.34, 0, 1)
        img = np.clip((img-.5)*1.16+.5, 0, 1)
    elif mode == "night":
        img = img*np.array([.86, .92, 1.12], np.float32)
        lum2 = img@np.array([.299, .587, .114], np.float32)
        img = np.clip(img+lum2[..., None]*np.array([.10, .02, -.06], np.float32), 0, 1)
    return np.clip(img, 0, 1)

_vig = None
def vignette(img, amt=.30):
    global _vig
    if _vig is None:
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx-W/2)/(W*.62))**2+((yy-H/2)/(H*.58))**2)
        _vig = np.clip(1-amt*d**2.0, 0, 1).astype(np.float32)
    img *= _vig[..., None]

_gr = [rng.normal(0, 1, (H, W)).astype(np.float32) for _ in range(8)]
def grain(img, t, amt=.0075):
    img += _gr[int(t*FPS) % 8][..., None]*amt
    return img

def bloom(img, amt=.25, thresh=.72, radius=16, mask=None):
    if amt <= .01: return img
    m = np.clip((img.max(2)-thresh)/(1-thresh+1e-6), 0, 1)
    if mask is not None: m = m*mask
    src = img*m[..., None]
    b = np.asarray(Image.fromarray((np.clip(src, 0, 1)*255).astype(np.uint8))
                   .filter(ImageFilter.GaussianBlur(radius)), np.float32)/255.
    return np.clip(img+b*amt, 0, 1)

def flash(img, a, color=(255, 240, 210)):
    if a <= .004: return img
    return np.clip(img*(1-a)+np.array(color, np.float32)/255.*a, 0, 1)

# ------------------------------------------------------------ text (vertical)
F_H1 = ImageFont.truetype("fonts/NotoSansDevanagari.ttf", 96)
F_H2 = ImageFont.truetype("fonts/NotoSansDevanagari.ttf", 68)
F_H3 = ImageFont.truetype("fonts/NotoSansDevanagari.ttf", 52)
F_H4 = ImageFont.truetype("fonts/NotoSansDevanagari.ttf", 44)
F_E1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
F_E2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 27)
_tc = {}
def tlayer(txt, font, fill=(255, 255, 255), stroke=(0, 0, 0, 165), sw=3, glowc=(255, 205, 110, 90)):
    k = (txt, font.size, fill, sw, glowc)
    if k in _tc: return _tc[k]
    tmp = Image.new("RGBA", (W+40, 320), (0, 0, 0, 0)); d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0, 0), txt, font=font, stroke_width=sw)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    lay = Image.new("RGBA", (min(W+40, tw+100), th+100), (0, 0, 0, 0)); d2 = ImageDraw.Draw(lay)
    ox, oy = 50-bb[0], 50-bb[1]
    if glowc:
        g = Image.new("RGBA", lay.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text((ox, oy), txt, font=font, fill=glowc, stroke_width=sw+7, stroke_fill=glowc)
        lay.alpha_composite(g.filter(ImageFilter.GaussianBlur(11)))
    d2.text((ox, oy), txt, font=font, fill=fill+(255,), stroke_width=sw, stroke_fill=stroke)
    _tc[k] = np.asarray(lay, np.float32)/255.
    return _tc[k]

def text(img, txt, font, cx, cy, alpha=1., fill=(255, 255, 255), sw=3,
         stroke=(0, 0, 0, 165), scale=1., glowc=(255, 205, 110, 90)):
    if alpha <= .01: return
    lay = tlayer(txt, font, fill, stroke, sw, glowc)
    if abs(scale-1) > .01:
        lay = rs(lay, lay.shape[1]*scale, lay.shape[0]*scale)
    blit(img, lay, cx-lay.shape[1]/2, cy-lay.shape[0]/2, alpha)

def text_wrapped(img, txt, font, cx, cy, alpha, max_w, fill=(255, 255, 255), sw=3,
                 stroke=(0, 0, 0, 165), glowc=(255, 205, 110, 90), line_gap=16):
    words = txt.split(" ")
    lines, cur = [], ""
    tmp = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    for w in words:
        trial = (cur+" "+w).strip()
        bb = tmp.textbbox((0, 0), trial, font=font)
        if bb[2]-bb[0] <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur); cur = w
    if cur: lines.append(cur)
    bb = tmp.textbbox((0, 0), "Ag", font=font)
    lh = (bb[3]-bb[1])*1.62+line_gap
    y0 = cy-(len(lines)-1)*lh/2
    for i, ln in enumerate(lines):
        text(img, ln, font, cx, y0+i*lh, alpha, fill, sw, stroke, 1.0, glowc)

# ------------------------------------------------------------ narration map
CUES = [("v01", 4.40), ("v02", 10.10), ("v03", 15.40), ("v04", 18.70),
        ("v05", 24.30), ("v06", 31.60), ("v07", 37.20), ("v08", 41.70),
        ("v09", 45.60), ("v10", 48.80)]

# ------------------------------------------------------------ shot table
SHOTS = [
    ("title",     0.00,  4.20),
    ("establish", 4.20, 10.10),
    ("jumpA",    10.10, 13.10),
    ("jumpB",    13.10, 15.90),
    ("fail",     15.90, 19.40),
    ("sour",     19.40, 24.30),
    ("office",   24.30, 31.60),
    ("decide",   31.60, 37.20),
    ("train",    37.20, 41.70),
    ("truth",    41.70, 48.10),
    ("moral",    48.10, 53.40),
]
def shot_at(t):
    for n, a, b in SHOTS:
        if a <= t < b: return n, a, b
    return SHOTS[-1]

GY = 700; GYS = 726; GYD = 700
def breath(t, amp=.012, sp=2.1, ph=0.): return 1+amp*math.sin(t*sp+ph)
def sway(t, amp=1.4, sp=1.7, ph=0.): return amp*math.sin(t*sp+ph)

ZMIN = 2.52          # vertical frame needs this much plate->screen zoom
def zc(eff):         # clamp an authored zoom
    return max(ZMIN, eff)

def _clamp_cam(plate, cx, cy, eff):
    """Keep the visible window inside the plate so padded edges never show."""
    vw, vh = W/eff, H/eff
    cx = min(max(cx, vw/2), plate.w-vw/2)
    cy = min(max(cy, vh/2), plate.h-vh/2)
    return cx, cy

def frame_v(plate, cx, ground, gfrac=.80, eff=1.60):
    """Vertical framing: ground line at gfrac*H, plate->screen zoom `eff`."""
    cy = ground-(H*gfrac-H/2)/eff
    cx, cy = _clamp_cam(plate, cx, cy, eff)
    return Scene(plate, cx, cy, eff/plate.scale)

def cam_v(plate, eff, focus_xy, screen_xy):
    cx = focus_xy[0]-(screen_xy[0]-W/2)/eff
    cy = focus_xy[1]-(screen_xy[1]-H/2)/eff
    cx, cy = _clamp_cam(plate, cx, cy, eff)
    return Scene(plate, cx, cy, eff/plate.scale)

GRX, GRB = 1117, 432     # real vine bunch in the forest plate

# ---------------------------------------------------------------- VFX helper
def char_mask(boxes, pad=26):
    """1.0 on background, 0.0 on the character (feathered) — so bloom and
    halation only pick up real light sources, never the actor."""
    if not boxes: return None
    m = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(m)
    for (x0, y0, x1, y1) in boxes:
        d.rectangle([x0-pad, y0-pad, x1+pad, y1+pad], fill=0)
    m = m.filter(ImageFilter.GaussianBlur(18))
    return np.asarray(m, np.float32)/255.

def finish_shot(img, t, *, focus=None, dof=2.0, flare=None, fog=0.14, fog_seed=4,
                haze=0.0, mode="teal_orange", warm=1.12, contrast=1.09, sat=1.06,
                bloom_amt=.30, bloom_thresh=.72, bloom_r=16, vig=.34, ca_amt=0.0,
                hal=0.30, grain_amt=.0075, jitter_amt=0.0, mask=None):
    if focus is not None:
        img = depth_of_field(img, focus, dof)
    if haze: img = haze_distance(img, haze)
    if fog: img = fog_layer(img, t, fog, fog_seed)
    if flare:
        fx, fy, fs = flare
        img = lens_flare(img, fx, fy, fs)
    img = bloom(img, bloom_amt, bloom_thresh, bloom_r, mask)
    img = halation(img, .88, hal, mask=mask)
    img = grade(img, warm, contrast, sat, 0.0, mode)
    # highlight roll-off keeps sky detail instead of clipping to white
    img = img/(1.0+np.maximum(img-0.72, 0)*0.85)
    if ca_amt: img = chroma_aberration(img, ca_amt)
    if jitter_amt: img = jitter(img, t, jitter_amt)
    vignette(img, vig)
    img = grain(img, t, grain_amt)
    return np.clip(img, 0, 1)

# ================================================================ SHOTS
def sh_title(t, lt, dur):
    eff = L(2.20, 2.34, eio(lt/dur))
    sc = frame_v(FOREST, L(1080, 1054, eio(lt/dur)), GY, .84, zc(eff))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t); sc.finish(img, t)
    godrays(img, 900, -140, math.radians(70), .52, .32, 15)
    MOTES.draw(img, t, .9, 2.6)
    img = finish_shot(img, t, focus=top_bottom_focus(img, .26, .30, .9, .62), dof=2.4,
                      flare=(880, 120, 0.55), fog=.18, fog_seed=4, haze=.05,
                      mode="teal_orange", warm=1.22, contrast=1.10, bloom_amt=.42,
                      vig=.40, hal=.34, mask=char_mask(sc.char_boxes))
    # --- title block, vertical stack
    p = win(lt, .20, 1.0, 3.30, 3.95)
    if p > .01:
        band = Image.new("RGBA", (W, 560), (0, 0, 0, 0)); d = ImageDraw.Draw(band)
        for yy in range(560):
            e = 1-abs((yy-280)/280)
            d.rectangle([0, yy, W, yy+1], fill=(4, 7, 5, int(168*(e**1.45))))
        blit(img, np.asarray(band, np.float32)/255., 0, 700, p)
    kick = win(lt, .50, 1.15, 3.25, 3.90)
    text(img, "A  F A B L E", F_E2, W/2, 760, .78*kick, (255, 232, 198), 0, glowc=(255, 185, 85, 70))
    text(img, "अंगूर", F_H1, W/2, 880, kick, (255, 251, 242), 4,
         scale=.94+.06*eout(ramp(lt, .45, 1.2)), glowc=(255, 200, 120, 110))
    text(img, "खट्टे हैं", F_H1, W/2, 1000, kick, (255, 214, 128), 4,
         scale=.90+.10*eout(ramp(lt, .60, 1.35)), glowc=(255, 170, 60, 120))
    text(img, "THE FOX & THE GRAPES", F_E1, W/2, 1110, .82*kick, (240, 220, 188), 0, glowc=(255, 180, 90, 40))
    sub = win(lt, 1.15, 1.75, 3.25, 3.90)
    text(img, "एक छोटी कहानी", F_H4, W/2, 1180, .68*sub, (226, 214, 196), 2, glowc=(255, 180, 90, 50))
    img *= ramp(lt, 0, .7)
    return img

def sh_establish(t, lt, dur):
    eff = L(2.10, 2.24, eio(lt/dur))
    sc = frame_v(FOREST, L(1010, 960, eio(lt/dur)), GY, .84, zc(eff))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    walk = ramp(lt, .05, .70)*(1-ramp(lt, 3.0, 3.4))
    fx = L(760, 1010, eout(ramp(lt, .08, 2.95), 2.2))
    if lt < 3.0:
        bob = abs(math.sin(lt*9.2))*9*walk
        pose = "fox_run" if lt < .8 else "fox_stand"
        sc.fox(pose, fx, GY-bob, 560 if pose == "fox_stand" else 520,
               alpha=cl(lt/.55) if lt < .8 else 1.0,
               rot=sway(t, 1.7)*walk if pose == "fox_stand" else sway(t, 2., 1.2),
               blur=1.4 if pose == "fox_run" else 0.,
               sx=1+.014*math.sin(lt*7), sy=breath(t, .012))
    else:
        sc.fox("fox_stand", 1010, GY, 575, sx=1+.018*math.sin(lt*3.2),
               sy=breath(t, .015), rot=sway(t, 1.5))
    sc.finish(img, t)
    godrays(img, 980, -90, math.radians(74), .34, .27, 12)
    MOTES.draw(img, t, .7)
    img = finish_shot(img, t, focus=top_bottom_focus(img, .30, .28, .85, .55), dof=2.2,
                      flare=(1010, 300, .18), fog=.15, fog_seed=6, haze=.05,
                      warm=1.16, bloom_amt=.30, vig=.30, hal=.28, mask=char_mask(sc.char_boxes))
    hx, hy = sc.scr(1010, GY-190)
    g = ramp(lt, 2.9, 3.4)
    if g > .05:
        glow(img, hx+20, hy-30, 52, (255, 240, 205), .40*g, 2.4)
        for i in range(3):
            text(img, "?", F_E1, hx+56+i*24, hy-92-i*22, .55*g*max(0., math.sin(t*4.4-i*1.1)),
                 (255, 248, 214), 0, glowc=None)
    # chapter card - vertical, lower third
    cp = win(lt, .95, 1.35, 3.85, 4.3)
    if cp > .01:
        pw, ph = 940, 190
        panel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(panel)
        d.rounded_rectangle([0, 0, pw, ph], 12, fill=(9, 11, 10, 236))
        d.rectangle([0, 0, 6, ph], fill=(240, 196, 104, 255))
        d.text((30, 20), "CHAPTER ONE  ·  THE VINE", font=F_E2, fill=(244, 200, 112, 255))
        d.text((30, 66), "जंगल में अंगूरों", font=F_H4, fill=(255, 246, 230, 255))
        d.text((30, 122), "की एक बेल", font=F_H4, fill=(255, 246, 230, 255))
        blit(img, np.asarray(panel, np.float32)/255., (W-pw)//2, 1430, cp)
    return img

def sh_jumpA(t, lt, dur):
    # vertical low-angle: fox at the bottom, grapes at the top of frame
    eff = L(2.55, 2.74, eio(lt/dur))
    fx = 1050
    sc = cam_v(FOREST, zc(eff), (fx, GY), (W*0.46, 1660))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    if lt < .60:
        k = lt/.60
        sc.fox("fox_stand", fx, GY, 540, sy=1-.17*k, sx=1+.13*k)
    elif lt < 1.70:
        p = (lt-.60)/1.10; arc = math.sin(p*math.pi)
        sc.fox("fox_jump", fx, GY-arc*150, 548+26*arc, sy=1+.11*arc, sx=1-.05*arc)
        for k in range(3):
            sc.fox("fox_jump", fx, GY-arc*150+52*(k+1), 536, alpha=.10, shadow=False)
    elif lt < 2.30:
        sc.fox("fox_stand", fx, GY, 540)
    else:
        k = max(0., 1-abs((lt-2.30)/.32))
        sc.fox("fox_stand", fx, GY, 540, sy=1-.18*k, sx=1+.15*k)
    sc.finish(img, t)
    godrays(img, 1040, -60, math.radians(80), .30, .23, 11)
    gsx, gsy = sc.scr(GRX, GRB)
    speed_streaks(img, gsx, gsy+200, t, win(lt, .6, .9, 1.5, 1.75)*.7, 14)
    if 2.25 < lt < 2.9:
        ix, iy = sc.scr(fx, GY); impact(img, ix, iy-30, lt-2.25, .85)
    MOTES.draw(img, t, .62)
    img = finish_shot(img, t, focus=radial_focus(img, W*0.5, H*0.72, 560, 420), dof=2.0,
                      flare=(gsx, gsy, .22), fog=.12, fog_seed=8,
                      warm=1.14, bloom_amt=.28, vig=.32, hal=.30,
                      ca_amt=2.2 if .6 <= lt <= 1.75 else 0,
                      jitter_amt=1.6 if 2.25 < lt < 2.55 else 0, mask=char_mask(sc.char_boxes))
    return img

def sh_jumpB(t, lt, dur):
    eff = L(2.62, 2.80, eio(lt/dur))
    fx = 1040
    sc = cam_v(FOREST, zc(eff), (fx, GY), (W*0.44, 1640))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    if lt < .55:
        sc.fox("fox_reach", fx, GY, 520, sy=1+.04*math.sin(t*3.))
    elif lt < 1.65:
        p = (lt-.55)/1.10; arc = math.sin(p*math.pi)
        sc.fox("fox_jump", fx, GY-arc*140, 532+24*arc, sy=1+.09*arc, sx=1-.04*arc)
        for k in range(3):
            sc.fox("fox_jump", fx, GY-arc*140+50*(k+1), 520, alpha=.11, shadow=False)
    elif lt < 2.30:
        sc.fox("fox_shock", fx, GY, 512, sy=1-.05*math.sin(cl((lt-1.65)/.65)*math.pi))
    else:
        sc.fox("fox_sad", fx, GY, 505, sy=breath(t, .012), rot=sway(t, 1.))
    sc.finish(img, t)
    godrays(img, 1060, -40, math.radians(84), .24, .20, 10)
    gsx, gsy = sc.scr(GRX, GRB)
    speed_streaks(img, gsx, gsy+240, t, win(lt, .62, .85, 1.5, 1.75)*.55, 10)
    MOTES.draw(img, t, .52)
    img = finish_shot(img, t, focus=radial_focus(img, W*0.5, H*0.74, 520, 400), dof=1.9,
                      flare=(gsx, gsy, .18), fog=.10, fog_seed=9,
                      warm=1.10, bloom_amt=.26, vig=.33, hal=.28, mask=char_mask(sc.char_boxes))
    return img

def sh_fail(t, lt, dur):
    eff = L(2.46, 2.64, eio(lt/dur))
    fx = 1050
    sc = cam_v(FOREST, zc(eff), (fx, GY), (W*0.40, 1660))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    if lt < 1.30:
        sc.fox("fox_reach", fx, GY, 530, sy=1+.04*math.sin(t*2.8))
    elif lt < 2.30:
        p = (lt-1.30)/1.0
        sc.fox("fox_jump", fx, GY-math.sin(p*math.pi)*95, 536)
    else:
        sc.fox("fox_sad", L(fx, fx+52, eout(ramp(lt, 2.30, 3.20))), GY, 515,
               sy=breath(t, .011), rot=sway(t, .9))
    sc.finish(img, t)
    gsx, gsy = sc.scr(GRX, GRB-20)
    glow(img, gsx, gsy, 260, (255, 178, 100), .26+.10*math.sin(t*2.2), 2.2)
    godrays(img, 1060, -20, math.radians(84), .26, .20, 10)
    MOTES.draw(img, t, .60)
    img = finish_shot(img, t, focus=radial_focus(img, W*0.5, H*0.76, 500, 420), dof=2.0,
                      flare=(gsx, gsy, .26), fog=.12, fog_seed=10,
                      warm=1.12, bloom_amt=.30, vig=.34, hal=.32, mask=char_mask(sc.char_boxes))
    cp = win(lt, 1.45, 1.95, 3.15, 3.55)
    if cp > .01:
        text(img, "पहुँच से बाहर...", F_H3, W/2, 560, .94*cp, (255, 236, 206), 2,
             glowc=(255, 180, 90, 70))
    return img

def sh_sour(t, lt, dur):
    eff = L(2.42, 2.48, eio(cl(lt/1.9)))*L(1., 1.06, eio(cl((lt-1.9)/1.5)))
    fx = 1046
    sc = cam_v(FOREST, zc(eff), (fx, GY), (W*0.42, 1680))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    if lt < 1.80:
        sc.fox("fox_sad", fx, GY, 560, rot=sway(t, 1.2))
    else:
        sc.fox("fox_shock", fx, GY, 575, sy=breath(t, .012))
    sc.finish(img, t)
    godrays(img, 1060, -30, math.radians(84), .20, .17, 9)
    MOTES.draw(img, t, .45)
    img = finish_shot(img, t, focus=radial_focus(img, W*0.46, H*0.74, 470, 380), dof=1.8,
                      flare=None, fog=.10, fog_seed=11,
                      warm=1.00, contrast=1.13, sat=1.02, bloom_amt=.24, vig=.40, hal=.26, mask=char_mask(sc.char_boxes))
    img[:, :, 0] = np.clip(img[:, :, 0]+.024*ramp(lt, 1.9, 2.4), 0, 1)
    p = win(lt, 1.95, 2.35, 3.7, 4.2)
    if p > .01:
        text(img, "अंगूर", F_H1, W/2, 620, p, (255, 126, 104), 3,
             scale=1.16-.16*eout(ramp(lt, 1.95, 2.35)), glowc=(255, 60, 40, 120))
        text(img, "खट्टे हैं!", F_H1, W/2, 748, p, (255, 126, 104), 3,
             scale=1.16-.16*eout(ramp(lt, 1.95, 2.35)), glowc=(255, 60, 40, 120))
    if 1.95 < lt < 2.5: flash(img, .13*win(lt, 1.95, 2.0, 2.15, 2.5), (255, 214, 205))
    return img

def sh_office(t, lt, dur):
    eff = L(2.56, 2.66, eio(lt/dur))
    sc = frame_v(OFFICE, L(700, 660, eio(lt/dur)), 700, .74, zc(eff))
    sc.shake = 5*win(lt, 3.9, 4.0, 4.3, 5.0)
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t); sc.finish(img, t)
    MOTES2.draw(img, t, .40, 2.6, (255, 226, 195))
    img = finish_shot(img, t, focus=top_bottom_focus(img, .22, .20, .75, .40), dof=1.9,
                      flare=None, fog=.07, fog_seed=14,
                      mode="bleach", warm=.92, contrast=1.16, sat=.94,
                      bloom_amt=.20, vig=.38, hal=.20)
    img[:, :, 2] = np.clip(img[:, :, 2]+.024, 0, 1)
    p = win(lt, 1.0, 1.4, 4.4, 5.0)
    if p > .01:
        text(img, "इसकी गलती है!", F_H2, W*0.5, 430, .96*p, (255, 96, 80), 3,
             scale=.94+.06*eout(ramp(lt, 1.0, 1.4)), glowc=(255, 60, 40, 100))
    cp = win(lt, 4.9, 5.4, 6.4, 6.8)
    if cp > .01:
        pw, ph = 950, 200
        panel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(panel)
        d.rounded_rectangle([0, 0, pw, ph], 12, fill=(9, 11, 10, 238))
        d.rectangle([0, 0, 6, ph], fill=(240, 80, 62, 255))
        d.text((30, 22), "EXACTLY THE SAME STORY", font=F_E2, fill=(244, 190, 96, 255))
        d.text((30, 70), "अपनी असफलता,", font=F_H4, fill=(255, 246, 230, 255))
        d.text((30, 128), "दूसरों पर मत थोपो", font=F_H4, fill=(255, 246, 230, 255))
        blit(img, np.asarray(panel, np.float32)/255., (W-pw)//2, 1400, cp)
    if 3.9 < lt < 4.6: flash(img, .09*win(lt, 3.9, 3.98, 4.1, 4.55), (255, 218, 208))
    return img

def sh_decide(t, lt, dur):
    eff = L(2.36, 2.16, eio(lt/dur))
    sc = frame_v(FOREST, L(1040, 1080, eio(lt/dur)), GY, .84, zc(eff))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    walk = ramp(lt, .7, 1.4)
    fx = L(1040, 1210, eout(ramp(lt, 1.1, 4.0), 1.9))
    bob = abs(math.sin(lt*8.6))*10*walk*(1-ramp(lt, 3.8, 4.6))
    if lt < 1.2:
        sc.fox("fox_sad", 1040, GY, 540, sy=breath(t, .012), rot=sway(t, 1.2))
    else:
        sc.fox("fox_run", fx, GY-bob, 520, sy=breath(t, .01), rot=sway(t, 1.8),
               blur=1.2 if walk > .5 else 0)
    sc.finish(img, t)
    godrays(img, 1060, -40, math.radians(78), .20, .17, 9)
    MOTES.draw(img, t, .55)
    img = finish_shot(img, t, focus=top_bottom_focus(img, .26, .26, .80, .50), dof=1.9,
                      flare=None, fog=.13, fog_seed=16,
                      warm=1.02, bloom_amt=.22, vig=.32, hal=.26, mask=char_mask(sc.char_boxes))
    cp = win(lt, 2.2, 2.8, 4.1, 4.6)
    if cp > .01:
        text(img, "पीठ फेर ली...", F_H3, W/2, 520, .94*cp, (255, 232, 198), 2,
             glowc=(255, 180, 90, 60))
    return img

def sh_train(t, lt, dur):
    eff = L(2.62, 2.76, eio(lt/dur))
    sc = frame_v(SUN, L(700, 668, eio(lt/dur)), GYS, .76, zc(eff))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    if lt < .9:
        sc.fox("fox_run", L(430, 700, eout(ramp(lt, 0, .9), 1.4)), GYS-abs(math.sin(lt*10))*8,
               500, rot=sway(t, 2., 1.3), blur=1.2)
    elif lt < 3.1:
        p = ((lt-.9) % 1.05)/1.05
        sc.fox("fox_jump", 700, GYS-math.sin(p*math.pi)*190, 515, sy=1+.05*math.sin(p*math.pi))
    else:
        sc.fox("fox_sit", 700, GYS, 530, sy=breath(t, .012), rot=sway(t, .8))
    sc.finish(img, t)
    sunx, suny = 760, 300
    glow(img, sunx, suny, 340, (255, 216, 152), .34, 2.3)
    godrays(img, sunx, suny+30, math.radians(98), .48, .32, 14)
    MOTES.draw(img, t, .9, 2.4)
    img = finish_shot(img, t, focus=top_bottom_focus(img, .30, .26, .85, .45), dof=2.1,
                      flare=(sunx, suny, .85), fog=.16, fog_seed=18, haze=.07,
                      warm=1.22, contrast=1.13, sat=1.10, bloom_amt=.34, vig=.30, hal=.30, mask=char_mask(sc.char_boxes))
    cp = win(lt, 1.2, 1.8, 2.9, 3.3)
    if cp > .01:
        text(img, "हर दिन,", F_H2, W/2, 600, .94*cp, (255, 246, 226), 2, glowc=(255, 190, 90, 80))
        text(img, "थोड़ा और बेहतर", F_H3, W/2, 690, .94*cp, (255, 246, 226), 2, glowc=(255, 190, 90, 80))
    return img

def sh_truth(t, lt, dur):
    eff = L(2.56, 2.70, eio(lt/dur))
    sc = frame_v(DUSK, L(700, 686, eio(lt/dur)), GYD, .86, zc(eff))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    sc.fox("fox_sit", 700, GYD, 520, sy=breath(t, .011), rot=sway(t, .8))
    sc.finish(img, t)
    pulse = .5+.5*math.sin(t*2.1)
    for i, (gx, gy) in enumerate([(300, 250), (420, 400), (600, 280), (800, 300),
                                  (960, 330), (1120, 290), (1160, 480)]):
        sx, sy = sc.scr(gx, gy)
        glow(img, sx, sy, 175, (198, 122, 255), (.30+.22*pulse)*(1 if i % 2 else .8), 2.)
    sparkle_field(img, mk_sparks(38, 21, W*.10, W*.95, H*.14, H*.74), t, .85)
    FIRE.draw(img, t, .60)
    godrays(img, 1050, -50, math.radians(82), .24, .19, 10)
    img = finish_shot(img, t, focus=top_bottom_focus(img, .30, .22, .85, .42), dof=2.2,
                      flare=(W*0.62, H*0.20, .40), fog=.20, fog_seed=20,
                      mode="night", warm=1.02, contrast=1.10, sat=1.12,
                      bloom_amt=.52, vig=.36, hal=.44, mask=char_mask(sc.char_boxes))
    p = win(lt, 1.0, 1.6, 4.6, 5.0)
    if p > .01:
        text(img, "सच यही है —", F_H3, W/2, 500, .92*p, (255, 238, 196), 2, glowc=(255, 180, 90, 60))
        text_wrapped(img, "अंगूर कभी खट्टे नहीं थे।", F_H2, W/2, 620, p, 900,
                     (255, 252, 240), 3, glowc=(190, 120, 255, 110))
    p2 = win(lt, 2.6, 3.2, 4.6, 5.0)
    if p2 > .01:
        text_wrapped(img, "बस लोमड़ी की पहुँच से बाहर थे।", F_H3, W/2, 830, p2, 900,
                     (255, 220, 150), 3, glowc=(255, 170, 60, 100))
    return img

def sh_moral(t, lt, dur):
    eff = L(2.58, 2.70, eio(lt/dur))
    sc = frame_v(SUN, L(690, 712, eio(lt/dur)), GYS, .80, zc(eff))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t); sc.finish(img, t)
    godrays(img, 760, 260, math.radians(94), .34, .26, 12)
    MOTES.draw(img, t, .78)
    img = finish_shot(img, t, focus=top_bottom_focus(img, .28, .22, .85, .42), dof=2.1,
                      flare=(760, 250, .45), fog=.17, fog_seed=22, haze=.06,
                      warm=1.16, contrast=1.14, sat=1.08, bloom_amt=.33, vig=.33, hal=.28)
    p = win(lt, .15, .85, 4.3, 4.85)
    if p > .01:
        scr = np.zeros((H, W), np.float32)
        yy = np.linspace(0, 1, H)[:, None]
        scr[:] = (np.clip(1-abs(yy-.5)*1.75, 0, 1)**1.4)*.60*p
        img *= (1-scr[..., None]*.80)
    text(img, "T H E   T R U T H", F_E2, W/2, 520, .82*p, (255, 226, 180), 0, glowc=(255, 180, 90, 50))
    text_wrapped(img, "अंगूर खट्टे नहीं थे,", F_H3, W/2, 630, p, 900, (255, 250, 240), 3, glowc=(255, 190, 90, 80))
    text_wrapped(img, "बस पहुँच से बाहर थे।", F_H1, W/2, 800, p, 940, (255, 214, 128), 4,
                 glowc=(255, 170, 60, 110))
    pill = win(lt, 1.25, 1.85, 4.35, 4.8)
    if pill > .01:
        pw, ph = 960, 210
        panel = Image.new("RGBA", (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(panel)
        d.rounded_rectangle([0, 0, pw, ph], 24, fill=(8, 10, 9, 212))
        d.rounded_rectangle([0, 0, pw, ph], 24, outline=(240, 190, 90, 215), width=2)
        d.text((pw//2, 62), "अपनी कमज़ोरी सुधारो", font=F_H4, fill=(255, 246, 226, 255), anchor="mm")
        d.text((pw//2, 140), "दूसरों को दोष मत दो", font=F_H4, fill=(240, 200, 130, 255), anchor="mm")
        blit(img, np.asarray(panel, np.float32)/255., (W-pw)//2, 1050, pill)
    text(img, "A  F A B L E   R E T O L D   ·   2 0 2 6", F_E2, W/2, 1250, .42*p,
         (236, 224, 204), 0, glowc=None)
    img *= 1-ramp(lt, dur-.6, dur)
    return img

SHOT_FN = {n: globals()["sh_"+n] for n, _, _ in SHOTS}

def render_frame(fi, t=None):
    if t is None: t = fi/FPS
    n, a, b = shot_at(t)
    img = SHOT_FN[n](t, t-a, b-a)
    return np.clip(img, 0, 1)

def main():
    if len(sys.argv) > 1 and sys.argv[1] != "full":
        for tt in [float(x) for x in sys.argv[1].split(",")]:
            im = render_frame(int(tt*FPS), tt)
            Image.fromarray((im*255).astype(np.uint8)).save(f"work/vst_{tt}.png")
            log("still", tt)
        return
    cmd = [FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
           "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an",
           "-c:v", "libx264", "-preset", "medium", "-crf", "17",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", f"{OUT}/video_v.mp4"]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(NF):
        pr.stdin.write((render_frame(fi)*255).astype(np.uint8).tobytes())
        if fi % 60 == 0:
            log(f"  {fi}/{NF} t={fi/FPS:5.1f}s shot={shot_at(fi/FPS)[0]}")
    pr.stdin.close(); pr.wait()
    log("done rc", pr.returncode)

if __name__ == "__main__":
    main()
