#!/usr/bin/env python3
"""
Sound design v2 for the 9:16 cut — 53.4 s @ 48 kHz stereo.

Adds the FX a vertical short needs:
  * sub-drop and riser on every cut (retention hooks)
  * whoosh + air-punch on each jump attempt
  * cloth/fur rustle, paw taps, breath puffs
  * vine-leaf rustle when the fox lands under the grapes
  * office: keyboard clacks, chair creak, paper slam, muffled shout
  * magic: reversed shimmer swell, glass chimes, low hum bed
  * mix-headroom so the narration stays on top (see mix_vertical.py)
"""
import numpy as np, os, wave

SR = 48000
DUR = 53.4
os.makedirs("work_audio_v", exist_ok=True)
rng = np.random.default_rng(23)
t = np.arange(int(SR*DUR))/SR

def write(path, st):
    st = np.asarray(st, np.float64)
    pk = np.max(np.abs(st)) or 1.0
    if pk > 0.97: st = st/pk*0.97
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(st, -1, 1)*32767).astype(np.int16).tobytes())
    print("wrote", path, f"{len(st)/SR:.1f}s")

def env_ad(n, atk, dec, curve=1.0):
    a = int(atk*SR); d = max(1, n-a)
    e = np.ones(n, np.float32)
    if a > 0: e[:a] = np.linspace(0, 1, a)**0.7
    e[a:] = np.exp(-np.arange(d)/(dec*SR))**curve
    return e

def tone(f, dur, vol=.3, atk=.005, dec=.3, harm=(1., .35, .12), fin=0.0):
    n = int(SR*dur); tt = np.arange(n)/SR
    f_t = f*(1+fin*np.clip(tt/dur, 0, 1))
    s = np.zeros(n, np.float32)
    ph = 2*np.pi*f_t*tt
    for i, h in enumerate(harm, 1):
        if f*i < SR/2-500:
            s += h*np.sin(ph*i).astype(np.float32)
    return s*env_ad(n, atk, dec)*vol

def noise(dur, vol=.2, lp=.1, hp=0.0):
    n = int(SR*dur)
    x = rng.standard_normal(n).astype(np.float32)
    y = np.zeros(n, np.float32); a = lp
    for i in range(1, n):
        y[i] = y[i-1]+a*(x[i]-y[i-1])
    if hp > 0:
        z = np.zeros(n, np.float32); b = hp
        for i in range(1, n):
            z[i] = z[i-1]+b*(y[i]-z[i-1])
        y = y-z
    return y*vol

def whoosh(dur=.55, vol=.34, up=True, hp=.02):
    n = int(SR*dur)
    x = rng.standard_normal(n).astype(np.float32)
    y = np.zeros(n, np.float32)
    for i in range(1, n):
        q = i/n
        a = (.012+.42*q) if up else (.42-.40*q)
        y[i] = y[i-1]+max(1e-4, a)*(x[i]-y[i-1])
    e = np.sin(np.pi*np.arange(n)/n)**1.4
    return y*e*vol

def sub_drop(dur=.9, vol=.55, f0=110, f1=34):
    n = int(SR*dur); tt = np.arange(n)/SR
    f = f0*(f1/f0)**np.clip(tt/dur, 0, 1)
    ph = 2*np.pi*np.cumsum(f)/SR
    return (np.sin(ph)*np.exp(-tt/(dur*0.42))*vol).astype(np.float32)

def riser(dur=1.1, vol=.22, f0=260, f1=3600):
    n = int(SR*dur); tt = np.arange(n)/SR
    f = f0*(f1/f0)**np.clip(tt/dur, 0, 1)
    ph = 2*np.pi*np.cumsum(f)/SR
    e = np.clip(tt/dur, 0, 1)**2.2
    return (np.sin(ph)*e*vol).astype(np.float32)

def thud(vol=.7, f=62, dec=.10):
    s = tone(f, .40, vol, .003, dec, (1., .55, .25))
    nz = noise(.10, vol*.35, .30)
    s[:len(nz)] += nz
    return s

def creak(dur=.35, vol=.16):
    n = int(SR*dur); tt = np.arange(n)/SR
    f = 180+90*np.sin(2*np.pi*2.2*tt)
    ph = 2*np.pi*np.cumsum(f)/SR
    s = np.sin(ph).astype(np.float32)*0.6+np.sin(ph*2.02).astype(np.float32)*0.3
    return s*np.sin(np.pi*tt/dur)**1.6*vol

def chime(f, dur=.9, vol=.16):
    return tone(f, dur, vol, .003, dur*0.45, (1., .45, .22, .09))

def place(buf, sig, at, pan=0.0):
    i = int(at*SR)
    if i >= len(buf) or i < 0: return
    j = min(len(buf), i+len(sig))
    l = np.cos((pan+1)*np.pi/4); r = np.sin((pan+1)*np.pi/4)
    buf[i:j, 0] += sig[:j-i]*l
    buf[i:j, 1] += sig[:j-i]*r

# ------------------------------------------------------------------ MUSIC
music = np.zeros((len(t), 2), np.float32)
# warm pad progression + sparse pluck, tuned for a phone speaker (more mids)
chords = [[130.81, 196.00, 261.63], [110.00, 164.81, 220.00],
          [87.31, 130.81, 174.61], [98.00, 146.83, 196.00]]
for bar in range(14):
    at = bar*4.0
    if at > DUR: break
    for f in chords[bar % 4]:
        place(music, tone(f, 5.2, .045, .9, 2.3, (1., .30, .10)), at,
              float(rng.uniform(-.25, .25)))
    place(music, tone(chords[bar % 4][0]/2, 4.3, .075, .35, 1.7), at)
mel = [523.25, 659.25, 783.99, 659.25, 587.33, 523.25, 440.00, 392.00,
       523.25, 783.99, 880.00, 783.99, 659.25, 587.33, 523.25, 392.00,
       440.00, 523.25, 659.25, 587.33, 523.25, 440.00, 349.23, 392.00]
for i, f in enumerate(mel):
    at = 2.2+i*1.55
    if at > DUR-1.4: break
    place(music, tone(f, 1.25, .085, .004, .42, (1., .55, .25, .1)), at,
          float(rng.uniform(-.35, .35)))
# act beds
i0, i1 = int(24.3*SR), int(31.6*SR)
tt = np.arange(i1-i0)/SR
dr = (.045*np.sin(2*np.pi*52*tt)+.028*np.sin(2*np.pi*78*tt))*(.55+.45*np.sin(2*np.pi*.16*tt))
music[i0:i1, 0] += dr; music[i0:i1, 1] += dr
i0, i1 = int(37.2*SR), int(48.0*SR)
tt = np.arange(i1-i0)/SR; nn = i1-i0
lift = (.030*np.sin(2*np.pi*523.25*tt)+.022*np.sin(2*np.pi*783.99*tt))
lift *= np.minimum(1, tt/1.6)*np.minimum(1, (nn/SR-tt)/1.4)
music[i0:i1, 0] += lift; music[i0:i1, 1] += lift*.92
music *= np.minimum(1, t/1.4)[:, None]*np.minimum(1, (DUR-t)/2.0)[:, None]
write("work_audio_v/music.wav", music)

# -------------------------------------------------------------------- SFX
fx = np.zeros((len(t), 2), np.float32)

# --- cut punctuation: sub-drop + riser at every shot boundary
CUTS = [4.20, 10.10, 13.10, 15.90, 19.40, 24.30, 31.60, 37.20, 41.70, 48.10]
for i, c in enumerate(CUTS):
    place(fx, sub_drop(.85, .42 if i in (0, 5, 6, 9) else .30), c-0.06)
    place(fx, whoosh(.48, .30, up=True), c-0.40)
    if c in (10.10, 24.30, 41.70):
        place(fx, riser(1.0, .18), c-1.0)

# --- forest ambience birds
for at in [.6, 1.3, 2.1, 2.9, 5.2, 6.4, 7.6, 8.7, 33.5, 34.6, 35.8, 49.5, 50.8, 52.0]:
    place(fx, np.sin(2*np.pi*(2800+700*t[:int(.16*SR)])*t[:int(.16*SR)]).astype(np.float32)
          *env_ad(int(.16*SR), .01, .06)*.16, at, float(rng.uniform(-.7, .7)))

# --- establish: paws on grass + cloth
for at in [5.0, 5.35, 5.7, 6.05, 6.4]:
    place(fx, thud(.22, 110, .045), at, float(rng.uniform(-.2, .2)))
place(fx, noise(.5, .10, .25), 4.4)

# --- jump attempt 1 (10.1-13.1): crouch rustle, leap, miss whistle, land
place(fx, noise(.35, .12, .18), 10.55)              # crouch cloth
place(fx, whoosh(.52, .34, up=True), 10.70)         # leap
place(fx, whoosh(.30, .16, up=False, hp=.03), 11.55)  # fail swipe
place(fx, thud(.55, 58, .12), 11.95)                # land
place(fx, noise(.22, .16, .35), 11.95)              # ground scuff
place(fx, thud(.30, 120, .05), 12.15)

# --- jump attempt 2 (13.1-15.9): higher, bigger miss, tail swish
place(fx, noise(.40, .13, .16), 13.30)
place(fx, whoosh(.60, .38, up=True), 13.45)
place(fx, whoosh(.34, .18, up=False, hp=.03), 14.30)
place(fx, thud(.62, 55, .14), 14.70)
place(fx, noise(.25, .18, .30), 14.70)
place(fx, whoosh(.28, .12, up=False), 15.10)        # tail swish

# --- fail (15.9-19.4): reach strain, leaf rustle, sad breath
place(fx, creak(.5, .10), 16.3)
place(fx, noise(.6, .10, .12), 16.9)
place(fx, noise(.35, .08, .20), 18.0)               # breath out
place(fx, chime(392, 1.1, .06), 18.2)

# --- sour (19.4-24.3): record-scratch style stop, then the lie sting
place(fx, noise(.26, .30, .55), 21.15)
for i, f in enumerate([392., 329.63, 261.63, 196.]):
    place(fx, tone(f, .52, .24, .008, .26, (1., .5, .16)), 21.30+i*.15)
place(fx, sub_drop(.7, .30, 90, 40), 21.30)

# --- office (24.3-31.6): keys, chair, paper, muffled shout, coffee clink
for at in [25.0, 25.14, 25.28, 26.6, 26.72, 28.4, 28.52, 28.64]:
    place(fx, noise(.05, .10, .55), at, float(rng.uniform(-.5, .5)))
    place(fx, thud(.10, 190, .022), at)
place(fx, creak(.42, .13), 25.9)
place(fx, noise(.30, .20, .32), 27.5)               # paper slide
place(fx, thud(.45, 88, .07), 29.35)                # palm slam
place(fx, noise(.22, .16, .40), 29.35)
place(fx, tone(420, .3, .06, .002, .09, (1., .8, .5)), 30.2)   # mug clink
place(fx, tone(1250, .25, .04, .002, .07, (1., .6)), 30.21)

# --- decide (31.6-37.2): turn, run steps, departing air
place(fx, noise(.30, .12, .22), 32.0)
for i in range(7):
    place(fx, thud(.20, 100, .045), 32.8+i*0.38, float(rng.uniform(-.3, .3)))
place(fx, whoosh(.5, .16, up=False), 36.4)

# --- train (37.2-41.7): effort breaths, big leaps, wind
for at in [37.4, 38.4, 39.4]:
    place(fx, noise(.30, .09, .16), at)
place(fx, whoosh(.58, .30, up=True), 37.7)
place(fx, whoosh(.62, .32, up=True), 38.85)
place(fx, thud(.40, 60, .10), 38.55)
place(fx, thud(.42, 58, .10), 39.75)
place(fx, noise(1.0, .07, .06), 37.2)

# --- truth (41.7-48.1): reversed swell, glass chimes, low magic hum
n = int(1.6*SR)
swell = np.sin(2*np.pi*(300+900*np.linspace(0, 1, n)**2)*np.arange(n)/SR).astype(np.float32)
swell *= np.linspace(0, 1, n)**2.4*.16
place(fx, swell, 41.9)
for i in range(9):
    place(fx, chime(1318.5*(1+i*0.122), .8, .085), 42.6+i*.17, float(rng.uniform(-.6, .6)))
i0, i1 = int(42.0*SR), int(48.0*SR)
tt = np.arange(i1-i0)/SR
hum = (.020*np.sin(2*np.pi*65.4*tt)+.012*np.sin(2*np.pi*98*tt)).astype(np.float32)
fx[i0:i1, 0] += hum; fx[i0:i1, 1] += hum
place(fx, chime(523.25, 1.8, .10), 47.4)

# --- moral (48.1-53.4): soft bell, warm resolve
place(fx, chime(659.25, 2.6, .14), 48.5)
place(fx, chime(987.77, 2.0, .08), 49.0)
place(fx, chime(1318.5, 1.6, .06), 49.6)
write("work_audio_v/sfx.wav", fx)

# ---------------------------------------------------------------- AMBIENCE
amb = np.zeros((len(t), 2), np.float32)
wind = noise(DUR, .05, .018)
wind *= (.55+.45*np.sin(2*np.pi*.06*t)).astype(np.float32)
amb[:, 0] += wind; amb[:, 1] += wind*.88
# office room tone
i0, i1 = int(24.4*SR), int(31.5*SR)
hum = (.024*np.sin(2*np.pi*120*t[i0:i1])+.014*np.sin(2*np.pi*240*t[i0:i1])).astype(np.float32)
amb[i0:i1, 0] += hum; amb[i0:i1, 1] += hum
amb *= np.minimum(1, t/1.2)[:, None]
write("work_audio_v/ambience.wav", amb)
print("done")
