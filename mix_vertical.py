#!/usr/bin/env python3
"""
Mix for the 9:16 cut — narration first, then punchy vertical-style FX.

Phone speakers are mid-heavy and small, so:
  * voice gets a bit more 2-4 kHz presence and a tighter low cut
  * SFX are high-passed (no sub mud) but keep a 60-100 Hz thump for earbuds
  * music sits lower and is ducked harder than the landscape mix
"""
import os, math, subprocess, numpy as np, wave
from scipy.signal import butter, sosfilt

SR = 48000
DUR = 53.4
N = int(DUR*SR)
FF = ".venv/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2"
TMP = "work/voice_wav_v"
os.makedirs(TMP, exist_ok=True)

CUES = [("v01", 4.40), ("v02", 10.10), ("v03", 15.40), ("v04", 18.70),
        ("v05", 24.30), ("v06", 31.60), ("v07", 37.20), ("v08", 41.70),
        ("v09", 45.60), ("v10", 48.80)]
SRC = {"v01": "v01_sees_vine", "v02": "v02_jumps", "v03": "v03_out_of_reach",
       "v04": "v04_sour", "v05": "v05_people", "v06": "v06_ruin",
       "v07": "v07_improve", "v08": "v08_remember", "v09": "v09_out_of_reach_only",
       "v10": "v10_moral"}

def read_wav(p):
    with wave.open(p) as w:
        n, ch = w.getnframes(), w.getnchannels()
        a = np.frombuffer(w.readframes(n), np.int16).astype(np.float32)/32768.
    a = a.reshape(-1, ch)
    return np.repeat(a, 2, 1) if ch == 1 else a

def write_wav(p, a):
    with wave.open(p, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1)*32767).astype(np.int16).tobytes())
    print("wrote", p)

def decode(mp3, out):
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", mp3,
                    "-ar", str(SR), "-ac", "2", out], check=True)

def resample_ratio(a, r):
    n_out = int(a.shape[0]/r)
    idx = np.linspace(0, a.shape[0]-1, n_out)
    i0 = np.floor(idx).astype(int); i1 = np.minimum(i0+1, a.shape[0]-1)
    f = (idx-i0)[:, None]
    return a[i0]*(1-f)+a[i1]*f

def db2lin(d): return 10**(d/20)

def speech_db(x):
    sos = butter(4, [300, 3000], btype="band", fs=SR, output="sos")
    return 20*np.log10(np.sqrt(np.mean(sosfilt(sos, x)**2))+1e-12)

def compress(x, thresh_db=-22, ratio=3.4, atk=0.004, rel=0.13):
    out = np.zeros_like(x)
    a_att = math.exp(-1.0/(atk*SR)); a_rel = math.exp(-1.0/(rel*SR))
    for ch in range(x.shape[1]):
        env = 0.0
        g = np.ones(x.shape[0], np.float32)
        for i in range(x.shape[0]):
            lvl = abs(x[i, ch])
            env = a_att*env+(1-a_att)*lvl if lvl > env else a_rel*env+(1-a_rel)*lvl
            e_db = 20*math.log10(env+1e-9)
            if e_db > thresh_db:
                g[i] = db2lin(-(e_db-thresh_db)*(1-1/ratio))
        out[:, ch] = x[:, ch]*g
    return out

# ------------------------------------------------------------------ VOICE
voice = np.zeros((N, 2), np.float32)
spans = []
for key, at in CUES:
    wav = f"{TMP}/{key}.wav"
    if not os.path.exists(wav):
        decode(f"audio2/{SRC[key]}.mp3", wav)
    v = read_wav(wav)
    v = resample_ratio(v, 0.958)                      # slightly deeper again
    v = sosfilt(butter(2, 120, btype="high", fs=SR, output="sos"), v, axis=0)
    v -= sosfilt(butter(2, [230, 520], btype="band", fs=SR, output="sos"), v, axis=0)*0.34
    v += sosfilt(butter(2, [1800, 4800], btype="band", fs=SR, output="sos"), v, axis=0)*1.05
    v -= sosfilt(butter(2, [6000, 7800], btype="band", fs=SR, output="sos"), v, axis=0)*0.30
    v += sosfilt(butter(2, 200, btype="low", fs=SR, output="sos"), v, axis=0)*0.34
    v = compress(v, -23, 3.6)
    rev = np.zeros_like(v)
    for d, g in [(0.017, .18), (0.029, .13), (0.043, .10), (0.067, .07)]:
        k = int(d*SR); rev[k:] += v[:-k]*g
    v = v+rev*0.15
    cur = speech_db(v.mean(1))
    v *= db2lin(-16.0-cur)
    i0 = int(at*SR); i1 = min(N, i0+len(v))
    seg = v[:i1-i0].copy()
    f = int(0.006*SR)
    if len(seg) > 2*f:
        seg[:f] *= np.linspace(0, 1, f)[:, None]
        seg[-f:] *= np.linspace(1, 0, f)[:, None]
    voice[i0:i1] += seg
    spans.append((at, at+len(v)/SR))
write_wav("work_audio_v/voice.wav", voice)

# --------------------------------------------------------------- SIDECHAIN
v_env = np.abs(voice).max(1)
e = 0.0
a_att = math.exp(-1.0/(0.003*SR)); a_rel = math.exp(-1.0/(0.26*SR))
env = np.empty(N, np.float32)
for i in range(N):
    x = v_env[i]
    e = a_att*e+(1-a_att)*x if x > e else a_rel*e+(1-a_rel)*x
    env[i] = e
env_db = 20*np.log10(env+1e-6)
presence = np.clip((env_db+52)/26.0, 0, 1)**0.72

def level(stem, target_db):
    r = np.sqrt(np.mean(stem**2))+1e-9
    return stem*(db2lin(target_db)/r)

music = read_wav("work_audio_v/music.wav")[:N]
sfx = read_wav("work_audio_v/sfx.wav")[:N]
amb = read_wav("work_audio_v/ambience.wav")[:N]
for nm in ("music", "sfx", "amb"):
    a = globals()[nm]
    if len(a) < N:
        globals()[nm] = np.vstack([a, np.zeros((N-len(a), 2), np.float32)])

sos_carve = butter(2, [400, 3600], btype="band", fs=SR, output="sos")
def carve(stem, amount):
    return stem-sosfilt(sos_carve, stem, axis=0)*(amount*presence[:, None])

# SFX keep their transient snap: duck less, but hard-carve the vocal band
sfx = carve(level(sfx, -19.5), 0.30)*db2lin(-11.0*presence)[:, None]
music = carve(level(music, -24.0), 0.50)*db2lin(-22.0*presence)[:, None]
amb = carve(level(amb, -32.0), 0.55)*db2lin(-17.0*presence)[:, None]

mix = voice+music+sfx+amb
th = 0.82
mix = np.where(np.abs(mix) > th, np.sign(mix)*(th+(1-th)*np.tanh((np.abs(mix)-th)/(1-th))), mix)
pk = np.max(np.abs(mix))
if pk > 0.92: mix *= 0.92/pk
f = int(0.9*SR)
mix[-f:] *= np.linspace(1, 0, f)[:, None]
write_wav("work_audio_v/final_mix.wav", mix)

bed = music+sfx+amb
print("\n--- vertical mix ---")
for nm, st in (("voice", voice), ("music", music), ("sfx", sfx), ("ambience", amb)):
    print("%-9s %6.1f dBFS (speech band)" % (nm, speech_db(st.mean(1))))
print("BED       %6.1f dBFS" % speech_db(bed.mean(1)))
print("=> dialog SNR %+.1f dB" % (speech_db(voice.mean(1))-speech_db(bed.mean(1))))
print("peak %.3f" % float(np.max(np.abs(mix))))
