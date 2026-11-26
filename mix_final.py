#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final sound mix: narration (processed) + music (ducked) + SFX + ambience -> WAV."""
import os, subprocess, numpy as np, wave

SR = 48000
DUR = 55.0
FF = ".venv/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2"
TMP = "work/voice_wav"
os.makedirs(TMP, exist_ok=True)

CUES = [("v01", 4.55), ("v02", 10.60), ("v03", 16.15), ("v04", 19.60),
        ("v05", 25.30), ("v06", 32.50), ("v07", 38.30), ("v08", 42.90),
        ("v09", 46.80), ("v10", 49.95)]
SRC = {"v01": "v01_sees_vine", "v02": "v02_jumps", "v03": "v03_out_of_reach",
       "v04": "v04_sour", "v05": "v05_people", "v06": "v06_ruin",
       "v07": "v07_improve", "v08": "v08_remember", "v09": "v09_out_of_reach_only",
       "v10": "v10_moral"}

N = int(DUR*SR)

def read_wav(path):
    with wave.open(path) as w:
        n = w.getnframes(); ch = w.getnchannels()
        a = np.frombuffer(w.readframes(n), np.int16).astype(np.float32)/32768.
    a = a.reshape(-1, ch)
    if ch == 1: a = np.repeat(a, 2, 1)
    return a

def write_wav(path, a):
    a = np.clip(a, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a*32767).astype(np.int16).tobytes())
    print("wrote", path)

def decode(mp3, out):
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", mp3,
                    "-ar", str(SR), "-ac", "2", out], check=True)

def resample_ratio(a, r):
    """change pitch+duration by ratio r (r<1 => lower pitch, longer)"""
    n_out = int(a.shape[0]/r)
    idx = np.linspace(0, a.shape[0]-1, n_out)
    i0 = np.floor(idx).astype(int); i1 = np.minimum(i0+1, a.shape[0]-1)
    f = (idx-i0)[:, None]
    return a[i0]*(1-f)+a[i1]*f

def rms_norm(a, target_db=-19.0):
    r = np.sqrt(np.mean(a**2))+1e-9
    return a*(10**(target_db/20)/r)

voice = np.zeros((N, 2), np.float32)
spans = []
for key, at in CUES:
    wav = f"{TMP}/{key}.wav"
    if not os.path.exists(wav):
        decode(f"audio2/{SRC[key]}.mp3", wav)
    v = read_wav(wav)
    # --- male voice effect: -4% pitch (deeper chest), gentle de-ess, warmth EQ
    v = resample_ratio(v, 0.962)
    n = v.shape[0]
    # simple biquad-free warmth: low-shelf boost + presence cut
    lp = np.zeros_like(v)
    a_lp = 0.035
    for ch in range(2):
        y = np.zeros(n, np.float32); x = v[:, ch]
        acc = 0.0
        for i in range(n):
            acc += a_lp*(x[i]-acc); y[i] = acc
        lp[:, ch] = y
    v = v+lp*0.55                       # body
    v = v-np.roll(lp, 2)*0.0
    v = rms_norm(v, -18.0)
    # short room reverb tail for "recorded in a studio" feel
    rev = np.zeros_like(v)
    for d, g in [(0.021, .22), (0.037, .16), (0.053, .12), (0.079, .09)]:
        k = int(d*SR)
        rev[k:] += v[:-k]*g
    v = v+rev*0.22
    i0 = int(at*SR); i1 = min(N, i0+n)
    seg = v[:i1-i0]
    # 8 ms fade in/out to avoid clicks
    f = int(0.008*SR)
    if len(seg) > 2*f:
        seg[:f] *= np.linspace(0, 1, f)[:, None]; seg[-f:] *= np.linspace(1, 0, f)[:, None]
    voice[i0:i1] += seg
    spans.append((at, at+n/SR))

write_wav("work_audio/voice.wav", voice)

# ---------------- ducking envelope
env = np.ones(N, np.float32)
for a, b in spans:
    i0 = max(0, int((a-0.25)*SR)); i1 = min(N, int((b+0.35)*SR))
    ramp = int(0.22*SR)
    seg = np.ones(i1-i0, np.float32)
    r1 = min(ramp, len(seg)); seg[:r1] = np.linspace(1, 0.42, r1)
    r2 = min(ramp, len(seg)); seg[-r2:] = np.linspace(0.42, 1, r2)
    env[i0:i1] = np.minimum(env[i0:i1], seg)

music = read_wav("work_audio/music.wav")[:N]
sfx = read_wav("work_audio/sfx.wav")[:N]
amb = read_wav("work_audio/ambience.wav")[:N]
if len(music) < N: music = np.pad(music, ((0, N-len(music)), (0, 0)))
if len(sfx) < N: sfx = np.pad(sfx, ((0, N-len(sfx)), (0, 0)))
if len(amb) < N: amb = np.pad(amb, ((0, N-len(amb)), (0, 0)))

mix = voice*1.0+music*env[:, None]*0.62+sfx*0.9+amb*0.75
# gentle bus glue: soft-knee limiter
th = 0.72
mix = np.where(np.abs(mix) > th, np.sign(mix)*(th+(1-th)*np.tanh((np.abs(mix)-th)/(1-th))), mix)
# fade the last 0.8 s
f = int(0.8*SR)
mix[-f:] *= np.linspace(1, 0, f)[:, None]
write_wav("work_audio/final_mix.wav", mix)
print("peak", float(np.max(np.abs(mix))))
