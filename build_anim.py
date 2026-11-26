#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANGOOR KHATTE HAIN — live 2.5D animation renderer
=================================================
55.0 s · 1920x1080 · 30 fps · 12 shots

Everything is authored in *plate space* (source art 1376x768).  The camera is
defined by what it must contain (framing box); a fox actor is placed at
specific plate coordinates and gets:

  * idle breathing (squash/stretch on Y with counter-X)
  * tail sway (rotational shear around feet)
  * run cycle (vertical bob + lean + motion blur)
  * jump parabola with anticipation crouch, stretch on launch and squash
    on landing, plus a moving contact shadow
  * shock / sad / reach / sit poses on the narration beats

VFX: volumetric god rays, dust motes, fireflies, magic sparks, impact rings,
speed streaks, camera shake, chromatic aberration on impacts, 2.35:1
letterbox, film grade, bloom, vignette, grain.
"""
import os, math, sys, subprocess, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, DUR = 1920, 1080, 30, 55.0
BAR = 86
NF = int(round(DUR*FPS))
FF = ".venv/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2"
OUT = "work/render"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(5)
random.seed(5)

def log(*a): print(*a, flush=True)
def cl(x, a=0.0, b=1.0): return a if x < a else (b if x > b else x)
def smooth(x): x = cl(x); return x*x*(3-2*x)
def eio(x): x = cl(x); return 0.5-0.5*math.cos(math.pi*x)
def eout(x, p=2.0): return 1-(1-cl(x))**p
def ein(x, p=2.0): return cl(x)**p
def L(a, b, t): return a+(b-a)*t
def ramp(t, a, b): return 0.0 if t <= a else (1.0 if t >= b else smooth((t-a)/(b-a)))
def win(t, a, b, c, d): return min(ramp(t, a, b), 1-ramp(t, c, d))

def rgb(p): return np.asarray(Image.open(p).convert("RGB"), np.float32)/255.0
def rgba(p): return np.asarray(Image.open(p).convert("RGBA"), np.float32)/255.0
def rs(im, w, h, f=Image.BILINEAR):
    mode = "RGBA" if im.shape[2] == 4 else "RGB"
    return np.asarray(Image.fromarray((np.clip(im, 0, 1)*255).astype(np.uint8), mode).resize((max(2, int(w)), max(2, int(h))), f), np.float32)/255.0

PAD = 260
class Plate:
    def __init__(self, path, scale=2.0, ew=0, eh=0):
        im = rgb(path); ih, iw = im.shape[:2]
        big = Image.fromarray((im*255).astype(np.uint8)).resize((int(iw*scale)+ew, int(ih*scale)+eh), Image.LANCZOS)
        cv = Image.new("RGB", (big.width+2*PAD, big.height+2*PAD), (7, 11, 8))
        cv.paste(big, (PAD, PAD))
        self.img = np.asarray(cv, np.float32)/255.0
        self.scale = scale; self.w, self.h = iw, ih
    def M(self, px, py): return PAD+px*self.scale, PAD+py*self.scale

FOREST = Plate("assets2/bg_forest.jpg", 2.0, 200, 160)
DUSK   = Plate("assets2/bg_dusk.jpg",   2.0, 160, 160)
SUN    = Plate("assets2/bg_sunrise.jpg",2.0, 220, 180)
OFFICE = Plate("assets/scene4_people_blame.jpg", 2.0, 160, 160)
log("plates ok")

FOX = {n: rgba(f"assets2/cut/{n}.png") for n in
       ["fox_stand", "fox_jump", "fox_sad", "fox_sit", "fox_reach", "fox_run", "fox_shock"]}
GRAPE = rgba("assets2/cut/grape_cluster.png")
_fc = {}
def foximg(pose, h):
    k = (pose, int(h))
    if k not in _fc:
        im = FOX[pose]; s = h/im.shape[0]
        _fc[k] = rs(im, im.shape[1]*s, h, Image.LANCZOS)
    return _fc[k]

# ============================================================ camera
def cam_contain(plate, box, z=1.0):
    """box = (x0,y0,x1,y1) in plate pixels that must be visible.
    Returns camera centre (plate px) + zoom, chosen to contain the box."""
    bw, bh = box[2]-box[0], box[3]-box[1]
    zx = min(W/bw, H/bh)
    z = min(z, zx)
    return ((box[0]+box[2])/2, (box[1]+box[3])/2, z)

class Scene:
    def __init__(self, plate, camx, camy, z, shake=0.0):
        self.p = plate; self.cx = camx; self.cy = camy; self.z = z; self.shake = shake
        self.items = []
        self.fx = []      # (callable(img)) after composite

    def begin(self, img, t):
        mx, my = self.p.M(self.cx, self.cy)
        vw, vh = int(round(W/self.z)), int(round(H/self.z))
        shx = math.sin(t*47)*self.shake; shy = math.cos(t*39)*self.shake
        x0, y0 = mx-vw/2+shx, my-vh/2+shy
        sub = crop(self.p.img, x0, y0, vw, vh)
        if (vw, vh) != (W, H):
            img[...] = rs(sub, W, H, Image.BICUBIC)
        else:
            img[...] = sub
        return img

    def scr(self, px, py):
        mx, my = self.p.M(px, py)
        cx, cy = self.p.M(self.cx, self.cy)
        return (mx-(cx-W/(2*self.z)))*self.z, (my-(cy-H/(2*self.z)))*self.z

    def fox(self, pose, x, y, h, alpha=1.0, flip=False, sx=1., sy=1., rot=0., blur=0., shadow=True, tint=None):
        self.items.append(("fox", dict(pose=pose, x=x, y=y, h=h, alpha=alpha, flip=flip,
                                       sx=sx, sy=sy, rot=rot, blur=blur, shadow=shadow, tint=tint)))
    def sprite(self, im, x, y, h, alpha=1., flip=False, glow=None, blur=0.):
        self.items.append(("spr", dict(im=im, x=x, y=y, h=h, alpha=alpha, flip=flip, blur=blur)))

    def finish(self, img, t):
        for kind, p in self.items:
            if kind == "fox": self._fox(img, p, t)
            else: self._spr(img, p)
        for f in self.fx: f(img)
        return img

    def _fox(self, img, p, t):
        im = foximg(p["pose"], p["h"])
        if p["flip"]: im = im[:, ::-1]
        if abs(p["sx"]-1) > .004 or abs(p["sy"]-1) > .004:
            im = rs(im, im.shape[1]*p["sx"], im.shape[0]*p["sy"])
        if abs(p["rot"]) > .05:
            im = np.asarray(Image.fromarray((np.clip(im, 0, 1)*255).astype(np.uint8), "RGBA")
                            .rotate(p["rot"], Image.BICUBIC, expand=True), np.float32)/255.0
        sx, sy = self.scr(p["x"], p["y"])
        if p["shadow"]:
            self._shadow(img, sx, sy, im.shape[1])
        if p["blur"] > .4:
            im = np.asarray(Image.fromarray((np.clip(im, 0, 1)*255).astype(np.uint8), "RGBA")
                            .filter(ImageFilter.GaussianBlur(p["blur"]*self.z)), np.float32)/255.0
        if p["tint"] is not None:
            im = im.copy(); im[:, :, :3] *= np.array(p["tint"], np.float32)
        blit(img, im, sx-im.shape[1]/2, sy-im.shape[0], p["alpha"])
        # warm rim light from the sun side
        rim = rimlight(im, strength=0.55)
        if rim is not None:
            blit(img, rim, sx-im.shape[1]/2, sy-im.shape[0], p["alpha"]*0.9, additive=True)

    def _spr(self, img, p):
        im = p["im"]
        if p["flip"]: im = im[:, ::-1]
        h = int(p["h"]); w = int(im.shape[1]*h/im.shape[0])
        im2 = rs(im, w, h, Image.LANCZOS)
        if p["blur"] > .3:
            im2 = np.asarray(Image.fromarray((np.clip(im2, 0, 1)*255).astype(np.uint8), "RGBA")
                             .filter(ImageFilter.GaussianBlur(p["blur"])), np.float32)/255.0
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
        dst[dy0:dy1, dx0:dx1] = np.clip(reg+s[:, :, :3]*al*0.55, 0, 1)
    else:
        dst[dy0:dy1, dx0:dx1] = reg*(1-al)+s[:, :, :3]*al

_rimk = {}
def rimlight(im, strength=0.5):
    """extract bright right-top edge for additive rim light"""
    key = (im.shape, strength)
    a = im[:, :, 3]
    edge = np.abs(np.gradient(a)[0])+np.abs(np.gradient(a)[1])
    e = np.clip(edge*2.2, 0, 1)
    if e.max() < 0.02: return None
    # bias to the upper-right (sun side)
    yy, xx = np.mgrid[0:im.shape[0], 0:im.shape[1]]
    bias = np.clip((xx/im.shape[1]-0.3)*1.2, 0, 1)*np.clip((yy/im.shape[0])*0.6+0.4, 0, 1)
    e = e*bias
    out = np.zeros_like(im)
    out[:, :, 0] = e*1.0*strength; out[:, :, 1] = e*0.80*strength; out[:, :, 2] = e*0.45*strength
    out[:, :, 3] = e*strength
    return out

# ============================================================ VFX
def glow(img, cx, cy, r, color, strength=1.0, power=2.2):
    H_, W_ = img.shape[:2]
    x0, x1 = max(0, int(cx-r)), min(W_, int(cx+r)); y0, y1 = max(0, int(cy-r)), min(H_, int(cy+r))
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.sqrt((xx-cx)**2+(yy-cy)**2)/max(r, 1e-3)
    m = np.clip(1-d, 0, 1)**power*strength
    img[y0:y1, x0:x1] += m[..., None]*np.array(color, np.float32)/255.0

_rays = {}
def godrays(img, x, y, ang, strength, spread, n=14, color=(255, 228, 168), seed=2):
    H_, W_ = img.shape[:2]
    key = (int(x//10), int(y//10), round(ang, 3), round(spread, 3), n, seed, round(strength, 2))
    if key in _rays: lay = _rays[key]
    else:
        sw, sh = W_//4, H_//4
        m = Image.new("L", (sw, sh), 0); d = ImageDraw.Draw(m); rr = random.Random(seed)
        for i in range(n):
            a = ang+(i-(n-1)/2)*(spread/n)*2+rr.uniform(-.01, .01)
            wd = rr.uniform(2., 7.)*(sh/270.)
            ln = max(sw, sh)*1.9
            x0, y0 = x/4, y/4
            for k, wk in enumerate([.35, .7, 1.]):
                d.line([(x0, y0), (x0+math.cos(a)*ln, y0+math.sin(a)*ln)],
                       fill=int(115*wk), width=max(2, int(wd*wk*2)))
        m = m.filter(ImageFilter.GaussianBlur(max(2., wd*2.4)))
        arr = np.asarray(m, np.float32)/255.0
        yy = np.linspace(0, 1, sh)[:, None]
        arr *= np.clip(1.22-yy*.85, 0, 1)
        nz = rng.normal(0, 1, (max(2, sh//6), max(2, sw//6))).astype(np.float32)
        nz = np.asarray(Image.fromarray(((np.clip(nz, -2, 2)+2)*63).astype(np.uint8)).resize((sw, sh), Image.BILINEAR), np.float32)/255.0
        arr *= (.78+.44*nz)
        lay = arr
        if len(_rays) > 40: _rays.clear()
        _rays[key] = lay
    lay = np.asarray(Image.fromarray((np.clip(lay, 0, 1)*255).astype(np.uint8)).resize((W_, H_), Image.BILINEAR), np.float32)/255.0
    img += (lay*strength)[..., None]*np.array(color, np.float32)/255.0

class Motes:
    def __init__(self, n, seed, y0=.0, y1=1., speed=1.):
        r = np.random.default_rng(seed)
        self.x = r.uniform(0, W, n); self.y = r.uniform(y0*H, y1*H, n)
        self.z = r.uniform(.3, 1., n); self.vx = r.uniform(-8, 14, n); self.vy = r.uniform(-22, -4, n)*speed
        self.ph = r.uniform(0, 6.283, n); self.sp = r.uniform(.5, 1.6, n); self.n = n
    def step(self, dt):
        self.x = (self.x+self.vx*self.z*dt) % (W+40)-20
        self.y += self.vy*self.z*dt
        self.y = np.where(self.y < -20, H+20, self.y)
    def draw(self, img, t, amp=1., size=2.2, color=(255, 236, 180)):
        col = np.array(color, np.float32)/255.0
        for i in range(self.n):
            a = amp*self.z[i]*(.45+.55*math.sin(t*self.sp[i]+self.ph[i]))*.55
            if a <= .02: continue
            x, y = int(self.x[i]), int(self.y[i]); r = int(size*self.z[i])+1
            if 0 <= y < H and 0 <= x < W:
                yi0, yi1 = max(0, y-r), min(H, y+r+1); xi0, xi1 = max(0, x-r), min(W, x+r+1)
                img[yi0:yi1, xi0:xi1] = np.clip(img[yi0:yi1, xi0:xi1]+a*col*.55, 0, 1)

MOTES = Motes(180, 3); MOTES2 = Motes(90, 8, .4, 1.); FIRE = Motes(60, 15, .35, .95)

def sparkles(img, seeds, t, amp=1., color=(255, 224, 130)):
    for (x, y, ph, sp, rad) in seeds:
        k = .5+.5*math.sin(t*sp+ph)
        if k < .22: continue
        glow(img, x, y, rad*(.7+.5*k), color, .85*k*amp, 2.4)
        x, y = int(x), int(y)
        img[max(0, y-2):y+3, max(0, x-2):x+3] += .8*k*amp*np.array(color, np.float32)/255.0

def mk_sparks(n, seed, x0, x1, y0, y1, big=False):
    r = random.Random(seed)
    return [(r.uniform(x0, x1), r.uniform(y0, y1), r.uniform(0, 6.28), r.uniform(1.2, 3.8),
             r.uniform(8, 26) if not big else r.uniform(20, 60)) for _ in range(n)]

def impact(img, cx, cy, dt, strength=1.):
    if dt < 0 or dt > .55: return
    p = dt/.55; rad = 40+560*eout(p)
    H_, W_ = img.shape[:2]
    x0, x1 = max(0, int(cx-rad-26)), min(W_, int(cx+rad+26))
    y0, y1 = max(0, int(cy-rad*.8-26)), min(H_, int(cy+rad*.8+26))
    if x1 <= x0 or y1 <= y0: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    d = np.sqrt((xx-cx)**2+((yy-cy)/.72)**2)
    img[y0:y1, x0:x1] += (np.exp(-((d-rad)/26.)**2)*(1-p)**1.5*strength)[..., None]*np.array([1., .93, .75], np.float32)

def streaks(img, cx, cy, t, amt, n=16, color=(255, 246, 222)):
    if amt <= .01: return
    r = random.Random(int(t*9)); H_, W_ = img.shape[:2]
    lay = np.zeros((H_, W_), np.float32)
    for i in range(n):
        a = r.uniform(0, 6.283); rr = r.uniform(320, 720); ln = r.uniform(100, 280)
        x0, y0 = cx+math.cos(a)*rr, cy+math.sin(a)*rr*.72
        for k in range(int(ln/5)):
            u = k/(ln/5); px = int(x0+math.cos(a)*ln*u); py = int(y0+math.sin(a)*ln*u)
            if 0 <= px < W and 0 <= py < H:
                lay[max(0, py-2):py+2, max(0, px-2):px+2] += amt*(1-u)*.13
    img += np.clip(lay, 0, 1)[..., None]*np.array(color, np.float32)/255.0

def grade(img, warm=1., contrast=1.1, sat=1.06, lift=0.):
    img = np.clip(img, 0, 1)
    img = img*img*(3-2*img)*.42+img*.58
    img = (img-.5)*contrast+.5+lift
    lum = img@np.array([.299, .587, .114], np.float32)
    img = lum[..., None]+(img-lum[..., None])*sat
    sh = np.clip(1-lum*2.3, 0, 1)[..., None]; hl = np.clip(lum*1.7-.28, 0, 1)[..., None]
    img += sh*np.array([-.020, .003, .030], np.float32)
    img += hl*np.array([.030, .012, -.016], np.float32)*warm
    return np.clip(img, 0, 1)

_vig = None
def vignette(img, amt=.3):
    global _vig
    if _vig is None:
        yy, xx = np.mgrid[0:H, 0:W]
        d = np.sqrt(((xx-W/2)/(W*.60))**2+((yy-H/2)/(H*.60))**2)
        _vig = np.clip(1-amt*d**2.05, 0, 1).astype(np.float32)
    img *= _vig[..., None]

_gr = [rng.normal(0, 1, (H, W)).astype(np.float32) for _ in range(8)]
def grain(img, t, amt=.009):
    img += _gr[int(t*FPS) % 8][..., None]*amt
    return img

def letterbox(img):
    img[:BAR] *= .015; img[H-BAR:] *= .012
    img[BAR-1:BAR+1] *= .35
    return img

def ca(img, amt):
    if amt < .5: return img
    return np.dstack([np.roll(img[:, :, 0], int(amt), 1), img[:, :, 1], np.roll(img[:, :, 2], -int(amt), 1)])

def flash(img, a, color=(255, 240, 210)):
    if a <= .004: return img
    return np.clip(img*(1-a)+np.array(color, np.float32)/255.*a, 0, 1)

def bloom(img, amt=.25, thresh=.7, radius=14):
    if amt <= .01: return img
    m = np.clip((img.max(2)-thresh)/(1-thresh), 0, 1)
    src = img*m[..., None]
    b = np.asarray(Image.fromarray((np.clip(src, 0, 1)*255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(radius)), np.float32)/255.
    return np.clip(img+b*amt, 0, 1)

def sky_fill(img, color=(255, 235, 200), amt=0.05):
    img += amt*np.array(color, np.float32)/255.

# ============================================================ text
F_H1 = ImageFont.truetype("fonts/NotoSansDevanagari.ttf", 86)
F_H2 = ImageFont.truetype("fonts/NotoSansDevanagari.ttf", 62)
F_H3 = ImageFont.truetype("fonts/NotoSansDevanagari.ttf", 46)
F_E1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
F_E2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 25)
_tc = {}
def tlayer(txt, font, fill=(255, 255, 255), stroke=(0, 0, 0, 170), sw=3, glowc=(255, 205, 110, 95)):
    k = (txt, font.size, fill, sw, glowc)
    if k in _tc: return _tc[k]
    tmp = Image.new("RGBA", (W, 300), (0, 0, 0, 0)); d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0, 0), txt, font=font, stroke_width=sw)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    lay = Image.new("RGBA", (tw+90, th+90), (0, 0, 0, 0)); d2 = ImageDraw.Draw(lay)
    if glowc:
        g = Image.new("RGBA", lay.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text((45-bb[0], 45-bb[1]), txt, font=font, fill=glowc, stroke_width=sw+7, stroke_fill=glowc)
        lay.alpha_composite(g.filter(ImageFilter.GaussianBlur(10)))
    d2.text((45-bb[0], 45-bb[1]), txt, font=font, fill=fill+(255,), stroke_width=sw, stroke_fill=stroke)
    _tc[k] = np.asarray(lay, np.float32)/255.
    return _tc[k]

def text(img, txt, font, cx, cy, alpha=1., fill=(255, 255, 255), sw=3,
         stroke=(0, 0, 0, 165), scale=1., glowc=(255, 205, 110, 90)):
    if alpha <= .01: return
    lay = tlayer(txt, font, fill, stroke, sw, glowc)
    if abs(scale-1) > .01:
        lay = rs(lay, lay.shape[1]*scale, lay.shape[0]*scale)
    blit(img, lay, cx-lay.shape[1]/2, cy-lay.shape[0]/2, alpha)

# ============================================================ narration map
CUES = [("v01", 4.55), ("v02", 10.55), ("v03", 16.10), ("v04", 19.55),
        ("v05", 25.25), ("v06", 32.45), ("v07", 38.20), ("v08", 42.40),
        ("v09", 46.30), ("v10", 49.30)]
def duck(t):
    v = 1.
    for k, at in CUES:
        d = 6.9 if k == "v05" else 4.5
        if at-.25 <= t <= at+d+.25: v = min(v, .5)
    return v

# ============================================================ shot table
SHOTS = [
    ("title",     0.00,  4.20),
    ("establish", 4.20, 10.55),
    ("jumpA",    10.55, 13.20),
    ("jumpB",    13.20, 16.20),
    ("fail",     16.20, 20.00),
    ("sour",     20.00, 25.25),
    ("office",   25.25, 32.45),
    ("decide",   32.45, 38.20),
    ("train",    38.20, 42.40),
    ("truth",    42.40, 49.05),
    ("moral",    49.05, 55.00),
]
def shot_at(t):
    for n, a, b in SHOTS:
        if a <= t < b: return n, a, b
    return SHOTS[-1]

GY = 700         # forest ground line (plate px)
GYS = 726        # sunrise ground
GYD = 700        # dusk ground

def breath(t, amp=.012, sp=2.1, ph=0.): return 1+amp*math.sin(t*sp+ph)
def sway(t, amp=1.4, sp=1.7, ph=0.): return amp*math.sin(t*sp+ph)

def frame(plate, cx, ground, gfrac=.80, eff=1.60):
    """Camera such that plate ground line sits at gfrac*H and the effective
    plate->screen zoom is `eff` (Scene takes half, since masters are 2x)."""
    cy = ground-(H*gfrac-540)/eff
    return Scene(plate, cx, cy, eff/2.0)

def cam_at(plate, eff, focus_xy, screen_xy):
    """Camera that puts plate point focus_xy at screen_xy with plate->screen zoom eff."""
    cx = focus_xy[0]-(screen_xy[0]-W/2)/eff
    cy = focus_xy[1]-(screen_xy[1]-H/2)/eff
    return Scene(plate, cx, cy, eff/plate.scale)

# plate-space anchors for the real vine (measured from bg_forest.jpg)
GRX, GRB = 1117, 432      # centre x / bottom y of the lowest big bunch
GRT = 372                 # top of that bunch

def bokeh_fg(img, plate, t, amp=1.0, corner="tr"):
    """Out-of-focus foreground foliage sampled from the plate, with a soft
    feathered alpha so no rectangle edge ever shows."""
    if amp <= .01: return
    src = plate.img
    # choose a foliage-dense patch of the plate (leaves + tendril)
    x0, y0 = plate.M(980, 60)
    x1, y1 = plate.M(1290, 330)
    sub = src[int(y0):int(y1), int(x0):int(x1)]
    if sub.size == 0: return
    h = int(H*0.70); w = int(sub.shape[1]*h/sub.shape[0])
    im = rs(sub, w, h, Image.LANCZOS)
    im = np.asarray(Image.fromarray((np.clip(im, 0, 1)*255).astype(np.uint8)).filter(
        ImageFilter.GaussianBlur(18)), np.float32)/255.
    # radial feather mask
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w*0.55, h*0.42
    d = np.sqrt(((xx-cx)/(w*0.52))**2+((yy-cy)/(h*0.55))**2)
    a = np.clip(1-d, 0, 1)**1.5*0.62*amp
    im = np.dstack([im, a])
    dx = W-w*0.62+math.sin(t*0.30)*9
    dy = -h*0.30+math.cos(t*0.24)*7
    if corner == "tl":
        dx = -w*0.42+math.sin(t*0.28)*8
    blit(img, im, dx, dy, 1.0)

# ------------------------------------------------------------ SHOT: title
def sh_title(t, lt, dur):
    eff = L(1.62, 1.74, eio(lt/dur))
    sc = frame(FOREST, L(880, 858, eio(lt/dur)), GY, .84, eff)
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t); sc.finish(img, t)
    godrays(img, 1500, -80, math.radians(74), .60, .30, 16)
    MOTES.draw(img, t, .85, 2.4)
    img = bloom(img, .48, .58, 22)
    img = grade(img, 1.28, 1.12, 1.04); vignette(img, .38)
    p = win(lt, .25, 1.1, 3.3, 3.95)
    if p > .01:
        bd = Image.new("RGBA", (W, 400), (0, 0, 0, 0)); d = ImageDraw.Draw(bd)
        for yy in range(400):
            e = 1-abs((yy-200)/200)
            d.rectangle([0, yy, W, yy+1], fill=(4, 7, 5, int(165*(e**1.5))))
        blit(img, np.asarray(bd, np.float32)/255., 0, H//2-160, p)
    kick = win(lt, .55, 1.2, 3.25, 3.9)
    text(img, "A FABLE ABOUT SOUR GRAPES", F_E1, W/2, 372, .88*kick, (255, 235, 200), 0, glowc=(255, 185, 85, 80))
    text(img, "अंगूर खट्टे हैं", F_H1, W/2, 500, kick, (255, 251, 242), 4,
         scale=.94+.06*eout(ramp(lt, .5, 1.25)))
    sub = win(lt, 1.0, 1.7, 3.25, 3.9)
    text(img, "Angoor Khatte Hain   ·   The Fox & The Grapes", F_E2, W/2, 630, .82*sub, (240, 220, 188), 0, glowc=(255, 180, 90, 40))
    text(img, "A  S H O R T   A N I M A T I O N", F_E2, W/2, 700, .5*sub, (225, 214, 198), 0, glowc=None)
    img *= ramp(lt, 0, .65)
    return letterbox(img)

# ------------------------------------------------------------ SHOT: establish
def sh_establish(t, lt, dur):
    # wide, fox trots in from the left and stops under the vine
    eff = L(1.70, 1.82, eio(lt/dur))
    sc = frame(FOREST, L(880, 820, eio(lt/dur)), GY, .80, eff)
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    walk = ramp(lt, .05, .75)*(1-ramp(lt, 3.15, 3.55))
    fx = L(700, 1010, eout(ramp(lt, .1, 3.1), 2.2))
    if lt < 3.15:
        bob = abs(math.sin(lt*9.2))*10*walk
        if lt < .8:
            sc.fox("fox_run", fx, GY-bob, 320, alpha=cl(lt/.6), rot=sway(t, 2., 1.2), blur=1.6)
        else:
            sc.fox("fox_stand", fx, GY-bob, 340, rot=sway(t, 1.6)*walk,
                   sx=1+.014*math.sin(lt*7), sy=breath(t, .012))
    else:
        sc.fox("fox_stand", 1010, GY, 345, sx=1+.018*math.sin(lt*3.2), sy=breath(t, .015), rot=sway(t, 1.6))
    sc.finish(img, t)
    bokeh_fg(img, FOREST, t, .8, "tl")
    godrays(img, 1460, -60, math.radians(78), .40, .26, 13)
    MOTES.draw(img, t, .72)
    img = bloom(img, .34, .62, 16)
    img = grade(img, 1.18, 1.08); vignette(img, .28)
    hx, hy = sc.scr(1010, GY-230)
    g = ramp(lt, 3.0, 3.5)
    if g > .05:
        glow(img, hx+30, hy-26, 50, (255, 240, 205), .40*g, 2.4)
        for i in range(3):
            text(img, "?", F_E1, hx+66+i*26, hy-88-i*20, .55*g*max(0., math.sin(t*4.4-i*1.1)), (255, 248, 214), 0, glowc=None)
    cp = win(lt, .95, 1.35, 3.9, 4.35)
    if cp > .01:
        panel = Image.new("RGBA", (1180, 108), (0, 0, 0, 0)); d = ImageDraw.Draw(panel)
        d.rounded_rectangle([0, 0, 1180, 108], 8, fill=(9, 11, 10, 234))
        d.rectangle([0, 0, 5, 108], fill=(240, 196, 104, 255))
        d.text((26, 16), "CHAPTER ONE  ·  THE VINE", font=F_E2, fill=(244, 200, 112, 255))
        d.text((26, 46), "जंगल में अंगूरों की एक बेल", font=F_H3, fill=(255, 246, 230, 255))
        blit(img, np.asarray(panel, np.float32)/255., 110, H-BAR-136, cp)
    return letterbox(img)

# ------------------------------------------------------------ SHOT: jumpA
def sh_jumpA(t, lt, dur):
    # under the vine: eyes up, crouch, first leap - fingertips just short
    eff = L(2.10, 2.24, eio(lt/dur))
    fx = 1000
    sc = cam_at(FOREST, eff, (1030, GY), (820, 926))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    if lt < .6:
        k = lt/.6
        sc.fox("fox_stand", fx, GY, 430, sy=1-.17*k, sx=1+.13*k)
    elif lt < 1.65:
        p = (lt-.6)/1.05; arc = math.sin(p*math.pi)
        sc.fox("fox_jump", fx, GY-arc*150, 440+20*arc, sy=1+.10*arc, sx=1-.05*arc)
        for k in range(3):
            sc.fox("fox_jump", fx, GY-arc*150+64*(k+1), 430, alpha=.11, shadow=False)
    elif lt < 2.25:
        sc.fox("fox_stand", fx, GY, 430)
    else:
        k = max(0., 1-abs((lt-2.25)/.32))
        sc.fox("fox_stand", fx, GY, 430, sy=1-.18*k, sx=1+.15*k)
    sc.finish(img, t)
    godrays(img, 1500, 30, math.radians(84), .28, .21, 11)
    gsx, gsy = sc.scr(GRX, GRB)
    streaks(img, gsx-30, gsy+120, t, win(lt, .65, .95, 1.45, 1.7)*.7, 14)
    if 2.2 < lt < 2.85:
        ix, iy = sc.scr(fx, GY); impact(img, ix, iy-24, lt-2.2, .85)
    MOTES.draw(img, t, .6)
    img = bloom(img, .3, .66, 14)
    img = grade(img, 1.16, 1.12); vignette(img, .30)
    if .6 <= lt <= 1.7: img = ca(img, 2.2)
    return letterbox(img)

# ------------------------------------------------------------ SHOT: jumpB
def sh_jumpB(t, lt, dur):
    eff = L(2.28, 2.42, eio(lt/dur))
    fx = 990
    sc = cam_at(FOREST, eff, (1035, GY), (700, 934))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    if lt < .55:
        sc.fox("fox_reach", fx, GY, 415, sy=1+.04*math.sin(t*3.))
    elif lt < 1.6:
        p = (lt-.55)/1.05; arc = math.sin(p*math.pi)
        sc.fox("fox_jump", fx, GY-arc*175, 430+22*arc, sy=1+.09*arc, sx=1-.04*arc)
        for k in range(3):
            sc.fox("fox_jump", fx, GY-arc*175+62*(k+1), 420, alpha=.12, shadow=False)
    elif lt < 2.25:
        sc.fox("fox_shock", fx, GY, 425, sy=1-.05*math.sin(cl((lt-1.6)/.65)*math.pi))
    else:
        sc.fox("fox_sad", fx, GY, 415, sy=breath(t, .012), rot=sway(t, 1.))
    sc.finish(img, t)
    godrays(img, 1520, 40, math.radians(88), .24, .19, 10)
    gsx, gsy = sc.scr(GRX, GRB)
    streaks(img, gsx-10, gsy+130, t, win(lt, .62, .85, 1.45, 1.7)*.55, 10)
    MOTES.draw(img, t, .5)
    img = bloom(img, .28, .66, 12)
    img = grade(img, 1.10, 1.10); vignette(img, .32)
    return letterbox(img)

# ------------------------------------------------------------ SHOT: fail
def sh_fail(t, lt, dur):
    eff = L(2.12, 2.26, eio(lt/dur))
    fx = 1000
    sc = cam_at(FOREST, eff, (1035, GY), (660, 934))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    if lt < 1.35:
        sc.fox("fox_reach", fx, GY, 435, sy=1+.04*math.sin(t*2.8))
    elif lt < 2.35:
        p = (lt-1.35)/1.0
        sc.fox("fox_jump", fx, GY-math.sin(p*math.pi)*115, 440)
    else:
        sc.fox("fox_sad", L(1000, 1060, eout(ramp(lt, 2.35, 3.3))), GY, 420,
               sy=breath(t, .011), rot=sway(t, .9))
    sc.finish(img, t)
    gsx, gsy = sc.scr(GRX, GRB-16)
    glow(img, gsx, gsy, 250, (255, 178, 100), .26+.10*math.sin(t*2.2), 2.2)
    godrays(img, 1520, 0, math.radians(84), .26, .19, 10)
    MOTES.draw(img, t, .62)
    img = bloom(img, .32, .64, 14)
    img = grade(img, 1.12, 1.10); vignette(img, .32)
    cp = win(lt, 1.5, 2.0, 3.3, 3.7)
    if cp > .01:
        text(img, "पहुँच से बाहर...", F_H3, W*.28, 236, .92*cp, (255, 236, 206), 2, glowc=(255, 180, 90, 70))
    return letterbox(img)

# ------------------------------------------------------------ SHOT: sour
def sh_sour(t, lt, dur):
    eff = L(2.20, 2.26, eio(cl(lt/2.2)))*L(1., 1.08, eio(cl((lt-2.1)/1.5)))
    fx = 1010
    sc = cam_at(FOREST, eff, (1040, GY), (780, 940))
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    if lt < 1.9:
        sc.fox("fox_sad", fx, GY, 460, rot=sway(t, 1.2))
    else:
        sc.fox("fox_shock", fx, GY, 470, sy=breath(t, .012))
    sc.finish(img, t)
    godrays(img, 1520, -10, math.radians(86), .22, .18, 9)
    MOTES.draw(img, t, .45)
    img = grade(img, 1.02, 1.14, 1.02); vignette(img, .40)
    img[:, :, 0] = np.clip(img[:, :, 0]+.022*ramp(lt, 2.1, 2.6), 0, 1)
    p = win(lt, 2.15, 2.55, 3.9, 4.4)
    if p > .01:
        text(img, "अंगूर खट्टे हैं!", F_H2, W/2, 300, p, (255, 122, 100), 3,
             scale=1.18-.18*eout(ramp(lt, 2.15, 2.55)), glowc=(255, 60, 40, 120))
    if 2.15 < lt < 2.7: flash(img, .12*win(lt, 2.15, 2.2, 2.35, 2.7), (255, 214, 205))
    return letterbox(img)

# ------------------------------------------------------------ SHOT: office
def sh_office(t, lt, dur):
    eff = L(1.32, 1.38, eio(lt/dur))
    sc = frame(OFFICE, L(700, 652, eio(lt/dur)), 700, .79, eff)
    sc.shake = 5*win(lt, 4.2, 4.3, 4.6, 5.2)
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t); sc.finish(img, t)
    MOTES2.draw(img, t, .42, 2.6, (255, 226, 195))
    img = grade(img, .92, 1.16, .95)
    img[:, :, 2] = np.clip(img[:, :, 2]+.022, 0, 1)
    vignette(img, .36)
    p = win(lt, 1.1, 1.5, 4.6, 5.2)
    if p > .01:
        text(img, "इसकी गलती है!", F_H2, W*.70, H*.22, .94*p, (255, 96, 80), 3,
             scale=.94+.06*eout(ramp(lt, 1.1, 1.5)), glowc=(255, 60, 40, 100))
    cp = win(lt, 5.2, 5.7, 6.6, 7.0)
    if cp > .01:
        panel = Image.new("RGBA", (1010, 112), (0, 0, 0, 0)); d = ImageDraw.Draw(panel)
        d.rounded_rectangle([0, 0, 1010, 112], 8, fill=(9, 11, 10, 236))
        d.rectangle([0, 0, 5, 112], fill=(240, 80, 62, 255))
        d.text((26, 14), "EXACTLY THE SAME STORY", font=F_E2, fill=(244, 190, 96, 255))
        d.text((26, 48), "अपनी असफलता, दूसरों पर मत थोपो", font=F_H3, fill=(255, 246, 230, 255))
        blit(img, np.asarray(panel, np.float32)/255., 120, H-BAR-140, cp)
    if 4.2 < lt < 4.9: flash(img, .09*win(lt, 4.2, 4.28, 4.4, 4.85), (255, 218, 208))
    return letterbox(img)

# ------------------------------------------------------------ SHOT: decide
def sh_decide(t, lt, dur):
    eff = L(2.02, 1.86, eio(lt/dur))
    sc = frame(FOREST, L(1000, 1050, eio(lt/dur)), GY, .84, eff)
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    walk = ramp(lt, .7, 1.4)
    fx = L(1000, 1180, eout(ramp(lt, 1.1, 4.2), 1.9))
    bob = abs(math.sin(lt*8.6))*10*walk*(1-ramp(lt, 4.0, 4.8))
    if lt < 1.2:
        sc.fox("fox_sad", 1000, GY, 420, sy=breath(t, .012), rot=sway(t, 1.2))
    else:
        sc.fox("fox_run", fx, GY-bob, 405, sy=breath(t, .01), rot=sway(t, 1.8), blur=1.3 if walk > .5 else 0)
    sc.finish(img, t)
    bokeh_fg(img, FOREST, t, .65, "tl")
    godrays(img, 1500, -30, math.radians(80), .22, .18, 9)
    MOTES.draw(img, t, .56)
    img = bloom(img, .24, .7, 10)
    img = grade(img, 1.02, 1.08); vignette(img, .30)
    cp = win(lt, 2.4, 3.0, 4.4, 4.9)
    if cp > .01:
        text(img, "पीठ फेर ली...", F_H3, W*.24, 244, .92*cp, (255, 232, 198), 2, glowc=(255, 180, 90, 60))
    return letterbox(img)

# ------------------------------------------------------------ SHOT: train
def sh_train(t, lt, dur):
    eff = L(1.62, 1.74, eio(lt/dur))
    sc = frame(SUN, L(690, 664, eio(lt/dur)), GYS, .80, eff)
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    if lt < .9:
        sc.fox("fox_run", L(560, 700, eout(ramp(lt, 0, .9), 1.4)), GYS-abs(math.sin(lt*10))*8,
               360, rot=sway(t, 2., 1.3), blur=1.2)
    elif lt < 3.2:
        p = ((lt-.9) % 1.15)/1.15
        sc.fox("fox_jump", 700, GYS-math.sin(p*math.pi)*230, 380, sy=1+.05*math.sin(p*math.pi))
    else:
        sc.fox("fox_sit", 700, GYS, 390, sy=breath(t, .012), rot=sway(t, .8))
    sc.finish(img, t)
    sunx, suny = 1160, 130
    glow(img, sunx, suny, 300, (255, 216, 152), .30, 2.4)
    godrays(img, sunx, suny+40, math.radians(100), .46, .32, 15)
    MOTES.draw(img, t, .92, 2.3)
    img = bloom(img, .34, .68, 22)
    img = grade(img, 1.26, 1.05, 1.04, .010); vignette(img, .23)
    cp = win(lt, 1.4, 2.0, 3.1, 3.5)
    if cp > .01:
        text(img, "हर दिन, थोड़ा और बेहतर", F_H3, W*.28, 232, .92*cp, (255, 246, 226), 2, glowc=(255, 190, 90, 80))
    return letterbox(img)

# ------------------------------------------------------------ SHOT: truth
def sh_truth(t, lt, dur):
    eff = L(1.56, 1.68, eio(lt/dur))
    sc = frame(DUSK, L(700, 684, eio(lt/dur)), GYD, .88, eff)
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t)
    sc.fox("fox_sit", 700, GYD, 430, sy=breath(t, .011), rot=sway(t, .8))
    sc.finish(img, t)
    pulse = .5+.5*math.sin(t*2.1)
    for i, (gx, gy) in enumerate([(300, 250), (420, 400), (800, 270), (960, 310), (1100, 280), (1160, 470)]):
        sx, sy = sc.scr(gx, gy)
        glow(img, sx, sy, 165, (198, 122, 255), (.30+.22*pulse)*(1 if i % 2 else .8), 2.)
    sparkles(img, mk_sparks(34, 21, W*.16, W*.94, H*.20, H*.74), t, .85)
    FIRE.draw(img, t, .62)
    godrays(img, 1300, -40, math.radians(84), .26, .20, 10)
    img = bloom(img, .62, .55, 24)
    img = grade(img, 1.04, 1.10, 1.10); vignette(img, .34)
    p = win(lt, 1.2, 1.8, 5.0, 5.4)
    if p > .01:
        text(img, "सच यही है —", F_H3, W/2, 232, .9*p, (255, 238, 196), 2, glowc=(255, 180, 90, 60))
        text(img, "अंगूर कभी खट्टे नहीं थे।", F_H2, W/2, 320, p, (255, 252, 240), 3,
             scale=.96+.04*eout(ramp(lt, 1.2, 1.8)), glowc=(190, 120, 255, 110))
    p2 = win(lt, 2.9, 3.5, 5.0, 5.4)
    if p2 > .01:
        text(img, "बस लोमड़ी की पहुँच से बाहर थे।", F_H3, W/2, 412, p2, (255, 220, 150), 3,
             glowc=(255, 170, 60, 100))
    return letterbox(img)

# ------------------------------------------------------------ SHOT: moral
def sh_moral(t, lt, dur):
    eff = L(1.58, 1.66, eio(lt/dur))
    sc = frame(SUN, L(690, 712, eio(lt/dur)), GYS, .82, eff)
    img = np.zeros((H, W, 3), np.float32); sc.begin(img, t); sc.finish(img, t)
    godrays(img, 1250, 100, math.radians(96), .36, .26, 12)
    MOTES.draw(img, t, .8)
    img = bloom(img, .42, .62, 20)
    img = grade(img, 1.24, 1.06, 1.03); vignette(img, .30)
    p = win(lt, .15, .85, 4.1, 4.65)
    if p > .01:
        scr = np.zeros((H, W), np.float32)
        yy = np.linspace(0, 1, H)[:, None]
        scr[:] = (np.clip(1-abs(yy-.5)*1.85, 0, 1)**1.5)*.58*p
        img *= (1-scr[..., None]*.78)
    text(img, "T H E   T R U T H", F_E2, W/2, 232, .8*p, (255, 226, 180), 0, glowc=(255, 180, 90, 50))
    text(img, "अंगूर खट्टे नहीं थे,", F_H3, W/2, 326, p, (255, 250, 240), 3, glowc=(255, 190, 90, 80))
    text(img, "बस पहुँच से बाहर थे।", F_H1, W/2, 446, p, (255, 214, 128), 4,
         scale=.95+.05*eout(ramp(lt, .15, .95)), glowc=(255, 170, 60, 110))
    pill = win(lt, 1.35, 1.95, 4.15, 4.6)
    if pill > .01:
        panel = Image.new("RGBA", (1100, 100), (0, 0, 0, 0)); d = ImageDraw.Draw(panel)
        d.rounded_rectangle([0, 0, 1100, 100], 50, fill=(8, 10, 9, 208))
        d.rounded_rectangle([0, 0, 1100, 100], 50, outline=(240, 190, 90, 215), width=2)
        d.text((550, 50), "अपनी कमज़ोरी सुधारो — दोष मत दो", font=F_H3, fill=(255, 246, 226, 255), anchor="mm")
        blit(img, np.asarray(panel, np.float32)/255., W/2-550, 618, pill)
    text(img, "A F A B L E   R E T O L D   ·   2 0 2 6", F_E2, W/2, 806, .40*p, (236, 224, 204), 0, glowc=None)
    img *= 1-ramp(lt, dur-.6, dur)
    return letterbox(img)

SHOT_FN = {n: globals()["sh_"+n] for n, _, _ in SHOTS}

def render_frame(fi, t=None):
    if t is None: t = fi/FPS
    n, a, b = shot_at(t)
    img = SHOT_FN[n](t, t-a, b-a)
    img = grain(img, t, .0085)
    return np.clip(img, 0, 1)

def main():
    if len(sys.argv) > 1 and sys.argv[1] not in ("full",):
        ts = [float(x) for x in sys.argv[1].split(",")]
        for tt in ts:
            im = render_frame(int(tt*FPS), tt)
            Image.fromarray((im*255).astype(np.uint8)).save(f"work/still_{tt}.png")
            log("still", tt)
        return
    cmd = [FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
           "-preset", "medium", "-crf", "16", "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", f"{OUT}/video_only.mp4"]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fi in range(NF):
        pr.stdin.write((render_frame(fi)*255).astype(np.uint8).tobytes())
        if fi % 60 == 0: log(f"  {fi}/{NF} t={fi/FPS:.1f}s shot={shot_at(fi/FPS)[0]}")
    pr.stdin.close(); pr.wait()
    log("done rc", pr.returncode)

if __name__ == "__main__":
    main()
