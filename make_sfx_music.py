#!/usr/bin/env python3
"""Music + SFX + ambience for 'Angoor Khatte Hain' — 55 s, 48 kHz stereo."""
import numpy as np, os, wave

SR = 48000
DUR = 55.0
os.makedirs("work_audio", exist_ok=True)
rng = np.random.default_rng(7)
t = np.arange(int(SR*DUR))/SR

def write_wav(path, stereo):
    stereo = np.asarray(stereo, np.float64)
    peak = np.max(np.abs(stereo)) or 1.0
    if peak > 0.98: stereo = stereo/peak*0.98
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(stereo, -1, 1)*32767).astype(np.int16).tobytes())
    print("wrote", path, f"{len(stereo)/SR:.1f}s")

def tone(f, dur, vol=.3, atk=.01, dec=None, harm=(1.0, .4, .15)):
    n = int(SR*dur); tt = np.arange(n)/SR; s = np.zeros(n)
    for i, h in enumerate(harm, 1):
        if f*i > SR/2-200: break
        s += h*np.sin(2*np.pi*f*i*tt)
    e = np.minimum(1.0, tt/max(atk, 1e-4))
    if dec is not None: e *= np.exp(-tt/dec)
    return s*e*vol

def noise(dur, vol=.2, lp=.08):
    n = int(SR*dur); x = rng.standard_normal(n); y = np.zeros(n); a = lp
    for i in range(1, n): y[i] = y[i-1]+a*(x[i]-y[i-1])
    return y*vol

def chirp(f0, f1, dur, vol=.18):
    n = int(SR*dur); tt = np.arange(n)/SR
    ph = 2*np.pi*(f0*tt+(f1-f0)*tt**2/(2*dur))
    return np.sin(ph)*(np.sin(np.pi*tt/dur)**2)*vol

def place(buf, sig, at, pan=0.0):
    i = int(at*SR)
    if i >= len(buf): return
    j = min(len(buf), i+len(sig))
    l = np.cos((pan+1)*np.pi/4); r = np.sin((pan+1)*np.pi/4)
    buf[i:j, 0] += sig[:j-i]*l; buf[i:j, 1] += sig[:j-i]*r

def whoosh(dur=.5, vol=.35):
    n = int(SR*dur); x = rng.standard_normal(n); y = np.zeros(n)
    for i in range(1, n):
        a = .015+.4*(i/n); y[i] = y[i-1]+a*(x[i]-y[i-1])
    return y*(np.sin(np.pi*np.arange(n)/n)**1.5)*vol

def thud(vol=.7):
    s = tone(58, .45, vol=vol, atk=.004, dec=.1, harm=(1., .5, .2))
    nz = noise(.14, vol*.4, .25); s[:len(nz)] += nz
    return s

# ---------------- MUSIC ----------------
music = np.zeros((len(t), 2))
chords = [[130.81, 164.81, 196.00, 246.94], [110.00, 130.81, 164.81, 196.00],
          [87.31, 110.00, 130.81, 164.81], [98.00, 123.47, 146.83, 174.61]]
for bar in range(15):
    ch = chords[bar % 4]; at = bar*4.0
    if at > DUR: break
    for f in ch:
        place(music, tone(f, 5.4, .05, 1.4, 2.4, (1., .22, .07)), at, float(rng.uniform(-.3, .3)))
    place(music, tone(ch[0]/2, 4.4, .085, .5, 1.9), at)
melody = [523.25, 587.33, 659.25, 783.99, 659.25, 587.33, 523.25, 440.00,
          523.25, 659.25, 783.99, 880.00, 783.99, 659.25, 587.33, 523.25,
          349.23, 440.00, 523.25, 587.33, 659.25, 587.33, 523.25, 392.00,
          440.00, 523.25, 659.25, 523.25, 440.00, 349.23]
for i, f in enumerate(melody):
    at = 2.0+i*1.7
    if at > DUR-1.2: break
    place(music, tone(f, 1.5, .095, .006, .55, (1., .5, .2, .08)), at, float(rng.uniform(-.4, .4)))
# tension drone during office
i0, i1 = int(25.2*SR), int(32.4*SR)
tt = np.arange(i1-i0)/SR
dr = (.05*np.sin(2*np.pi*55*tt)+.03*np.sin(2*np.pi*82.5*tt))*(.6+.4*np.sin(2*np.pi*.18*tt))
music[i0:i1, 0] += dr; music[i0:i1, 1] += dr
# hopeful lift
i0, i1 = int(38.2*SR), int(49.0*SR)
tt = np.arange(i1-i0)/SR; n = i1-i0
lift = (.035*np.sin(2*np.pi*523.25*tt)+.025*np.sin(2*np.pi*659.25*tt))
lift *= np.minimum(1, tt/2)*np.minimum(1, (n/SR-tt)/1.5)
music[i0:i1, 0] += lift; music[i0:i1, 1] += lift*.9
music *= np.minimum(1, t/1.5)[:, None]*np.minimum(1, (DUR-t)/2.2)[:, None]
write_wav("work_audio/music.wav", music)

# ---------------- SFX ----------------
sfx = np.zeros((len(t), 2))
for at in [.5, 1.2, 1.9, 2.7, 5.0, 6.2, 43.4, 45.0, 46.6, 50.4, 51.6, 53.0]:
    place(sfx, chirp(2800, 3600, .16), at, float(rng.uniform(-.6, .6)))
    place(sfx, chirp(3300, 2500, .2), at+.22, float(rng.uniform(-.6, .6)))
for at, v in [(4.2, .30), (7.4, .34), (10.6, .38), (13.2, .34), (16.2, .36), (20.0, .38),
              (25.2, .42), (32.4, .44), (38.2, .38), (42.4, .40), (49.0, .36), (54.0, .3)]:
    place(sfx, whoosh(.55, v), at-.1)
# three jump attempts
for at in [10.95, 12.45, 14.45]:
    place(sfx, whoosh(.45, .30), at)
    place(sfx, whoosh(.35, .22), at+.55)
for at in [11.85, 13.35, 15.35]:
    place(sfx, thud(.65), at)
# sour sting
for i, f in enumerate([392., 329.63, 261.63, 196.]):
    place(sfx, tone(f, .5, .26, .01, .28, (1., .45, .12)), 23.2+i*.16)
place(sfx, noise(.25, .35, .6), 23.35)
# office
place(sfx, noise(.5, .20, .3), 25.6)
for a in [26.4, 28.4, 30.2]:
    m = tone(95, .9, .09, .08, .7, (1., .6, .3))
    m *= (.7+.3*np.sin(2*np.pi*7*np.arange(len(m))/SR))
    place(sfx, m, a)
place(sfx, tone(72, .4, .6, .004, .09, (1., .45)), 31.55)
place(sfx, noise(.3, .25, .5), 31.55)
# signature stamp at "kisi ko barbaad"
place(sfx, tone(60, .5, .8, .004, .14, (1., .5, .3)), 33.3)
place(sfx, noise(.35, .3, .35), 33.3)
# glass shards shimmer at decide
for i in range(12):
    place(sfx, tone(float(rng.uniform(2200, 6200)), .18, .06, .001, .06),
          34.2+float(rng.uniform(0, .5)), float(rng.uniform(-.8, .8)))
# riser into sunrise
n = int(1.1*SR); tt = np.arange(n)/SR
place(sfx, np.sin(2*np.pi*(300+1400*(tt/1.1)**2)*tt)*(tt/1.1)**2*.16, 37.1)
place(sfx, noise(1.0, .10, .05)*np.linspace(.2, 1, int(1.0*SR)), 37.2)
# training jumps
place(sfx, whoosh(.55, .28), 39.3)
place(sfx, whoosh(.7, .24), 40.9)
place(sfx, tone(1046.5, .8, .10, .05, .5), 40.95)
# magic truth
place(sfx, chirp(1200, 5200, 1.3, .20), 42.8)
for i in range(8):
    place(sfx, tone(1568+i*196, .6, .10, .005, .35), 43.3+i*.16)
place(sfx, tone(1318.5, 1.4, .10, .01, .7), 46.0)
# moral chimes + final bell
for at in [49.6, 51.2]:
    place(sfx, tone(880, 1.4, .16, .005, .8, (1., .5, .2)), at)
    place(sfx, tone(1318.5, 1.2, .09, .005, .7), at+.18)
place(sfx, tone(659.25, 2.4, .20, .005, 1.2, (1., .5, .25, .1)), 52.6)
place(sfx, tone(1318.5, 1.6, .09, .005, .8, (1., .4)), 52.6)
write_wav("work_audio/sfx.wav", sfx)

# ---------------- AMBIENCE ----------------
amb = np.zeros((len(t), 2))
wind = noise(DUR, .045, .02)*(.6+.4*np.sin(2*np.pi*.07*t))
amb[:, 0] += wind; amb[:, 1] += wind*.9
for at in np.arange(1.0, DUR, 3.7):
    if 25.0 <= at <= 32.5: continue
    place(amb, chirp(float(rng.uniform(2400, 3400)), float(rng.uniform(2000, 3000)), .14, .05), at,
          float(rng.uniform(-.8, .8)))
i0, i1 = int(25.3*SR), int(32.4*SR)
hum = .028*np.sin(2*np.pi*120*t[i0:i1])+.018*np.sin(2*np.pi*240*t[i0:i1])
amb[i0:i1, 0] += hum; amb[i0:i1, 1] += hum
write_wav("work_audio/ambience.wav", amb)
print("done")
