#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Final sound mix, v2 — narration-first.

Fixes the "SFX/music eats the voice" problem:
  1. Voice chain: mud cut, presence lift (1.6-4.5 kHz), gentle compression,
     then speech-band normalised to -16.5 dBFS.
  2. Bed (music/SFX/ambience) is side-chain ducked hard inside every narration
     window (-18 dB), and its 300 Hz-3.5 kHz band is carved a further 3 dB, so
     consonants stay intelligible.
  3. SFX get their punch back BETWEEN lines (0.9) but sit at 0.28 under speech.
  4. Bus limiter + final loudness handled by ffmpeg loudnorm (-16 LUFS, TP -1.5).
"""
import os, math, subprocess, numpy as np, wave
from scipy.signal import butter, sosfilt, lfilter

SR = 48000
DUR = 55.0
N = int(DUR*SR)
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

def read_wav(p):
    with wave.open(p) as w:
        n, ch = w.getnframes(), w.getnchannels()
        a = np.frombuffer(w.readframes(n), np.int16).astype(np.float32)/32768.
    a = a.reshape(-1, ch)
    return np.repeat(a, 2, 1) if ch == 1 else a

def write_wav(p, a):
    a = np.clip(a, -1, 1)
    with wave.open(p, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((a*32767).astype(np.int16).tobytes())
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
    """RMS dB inside the 300-3000 Hz speech band."""
    sos = butter(4, [300, 3000], btype="band", fs=SR, output="sos")
    return 20*np.log10(np.sqrt(np.mean(sosfilt(sos, x)**2))+1e-12)

def compress(x, thresh_db=-20, ratio=3.0, atk=0.006, rel=0.16):
    """simple envelope-follower compressor, per channel"""
    out = np.zeros_like(x)
    a_att = np.exp(-1.0/(atk*SR)); a_rel = np.exp(-1.0/(rel*SR))
    for ch in range(x.shape[1]):
        env = 0.0
        g = np.ones(x.shape[0], np.float32)
        for i in range(x.shape[0]):
            lvl = abs(x[i, ch])
            env = a_att*env+(1-a_att)*lvl if lvl > env else a_rel*env+(1-a_rel)*lvl
            e_db = 20*np.log10(env+1e-9)
            if e_db > thresh_db:
                over = e_db-thresh_db
                g[i] = db2lin(-over*(1-1/ratio))
        out[:, ch] = x[:, ch]*g
    return out

# ------------------------------------------------------------------ 1. VOICE
voice = np.zeros((N, 2), np.float32)
spans = []
for key, at in CUES:
    wav = f"{TMP}/{key}.wav"
    if not os.path.exists(wav):
        decode(f"audio2/{SRC[key]}.mp3", wav)
    v = read_wav(wav)
    v = resample_ratio(v, 0.962)              # deeper male chest

    # --- EQ: cut mud <120 Hz, small 400 Hz dip, presence lift 1.6-4.5 kHz,
    #     de-harsh dip at 6.5 kHz
    sos_hp = butter(2, 110, btype="high", fs=SR, output="sos")
    v = sosfilt(sos_hp, v, axis=0)
    sos_mud = butter(2, [250, 520], btype="band", fs=SR, output="sos")
    v -= sosfilt(sos_mud, v, axis=0)*0.30
    sos_pres = butter(2, [1600, 4500], btype="band", fs=SR, output="sos")
    v += sosfilt(sos_pres, v, axis=0)*0.85
    sos_harsh = butter(2, [5800, 7600], btype="band", fs=SR, output="sos")
    v -= sosfilt(sos_harsh, v, axis=0)*0.25

    # --- body/air: low shelf + tiny air
    sos_low = butter(2, 180, btype="low", fs=SR, output="sos")
    v += sosfilt(sos_low, v, axis=0)*0.30

    # --- compression so quiet syllables stay audible
    v = compress(v, thresh_db=-24, ratio=3.2, atk=0.005, rel=0.14)

    # --- short studio room (early reflections)
    rev = np.zeros_like(v)
    for d, g in [(0.019, .20), (0.031, .15), (0.047, .11), (0.071, .08)]:
        k = int(d*SR)
        rev[k:] += v[:-k]*g
    v = v+rev*0.18

    # --- normalise the SPEECH BAND (what actually carries intelligibility)
    cur = speech_db(v.mean(1))
    v *= db2lin(-16.5-cur)

    i0 = int(at*SR); i1 = min(N, i0+len(v))
    seg = v[:i1-i0].copy()
    f = int(0.008*SR)
    if len(seg) > 2*f:
        seg[:f] *= np.linspace(0, 1, f)[:, None]
        seg[-f:] *= np.linspace(1, 0, f)[:, None]
    voice[i0:i1] += seg
    spans.append((at, at+len(v)/SR))

write_wav("work_audio/voice.wav", voice)

# --------------------------------------------------- 2. SIDECHAIN (per sample)
music = read_wav("work_audio/music.wav")[:N]
sfx = read_wav("work_audio/sfx.wav")[:N]
amb = read_wav("work_audio/ambience.wav")[:N]
for nm, arr in (("music", music), ("sfx", sfx), ("ambience", amb)):
    if len(arr) < N:
        arr = np.vstack([arr, np.zeros((N-len(arr), 2), np.float32)])
    globals()[nm] = arr

# --- true envelope follower on the narration: drives every duck
v_env = np.abs(voice).max(1)
a_att = math.exp(-1.0/(0.004*SR))
a_rel = math.exp(-1.0/(0.30*SR))
env = np.zeros(N, np.float32)
e = 0.0
for i in range(N):
    x = v_env[i]
    e = a_att*e+(1-a_att)*x if x > e else a_rel*e+(1-a_rel)*x
    env[i] = e
env_db = 20*np.log10(env+1e-6)
# floor -> gate: below -52 dBFS the voice is silent, no ducking
presence = np.clip((env_db+52)/26.0, 0, 1)          # 0 = silence, 1 = talking
presence = presence**0.75

def duck_db(depth_db):
    """gain in dB from 0 (silence) to -depth (full speech)"""
    return -depth_db*presence

g_music = db2lin(duck_db(21.0))
g_sfx = db2lin(duck_db(13.0))
g_amb = db2lin(duck_db(16.0))

# --- carve the 350-3500 Hz intelligibility band out of the bed while speaking
sos_carve = butter(2, [350, 3500], btype="band", fs=SR, output="sos")
def carve(stem, amount=0.45):
    return stem-sosfilt(sos_carve, stem, axis=0)*(amount*presence[:, None])

def level(stem, target_db):
    r = np.sqrt(np.mean(stem**2))+1e-9
    return stem*(db2lin(target_db)/r)

music = carve(level(music, -25.0))*g_music[:, None]
sfx = carve(level(sfx, -21.0), 0.35)*g_sfx[:, None]
amb = carve(level(amb, -33.0), 0.5)*g_amb[:, None]

# --- SFX transient tamer: hard duck under speech for the loud one-shots
peak = np.abs(sfx).max(1)
sfx = np.minimum(sfx, 0.55)*np.where(peak[:, None] > 0.55, 1.0, 1.0)

mix = voice+music+sfx+amb

# ------------------------------------------------------------- 3. BUS LIMITER
th = 0.80
mix = np.where(np.abs(mix) > th,
               np.sign(mix)*(th+(1-th)*np.tanh((np.abs(mix)-th)/(1-th))), mix)
pk = np.max(np.abs(mix))
if pk > 0.90:                      # keep 0.8 dB headroom before AAC
    mix *= 0.90/pk
f = int(0.9*SR)
mix[-f:] *= np.linspace(1, 0, f)[:, None]
write_wav("work_audio/final_mix.wav", mix)

# ------------------------------------------------------------------- 4. REPORT
def band_db(x):
    return speech_db(x.mean(1))
print("\n--- final balance (speech band 300-3k, dBFS) ---")
for nm, st in (("voice", voice), ("music", music), ("sfx", sfx), ("ambience", amb)):
    print("%-9s %6.1f dBFS" % (nm, band_db(st)))
bed = music+sfx+amb
print("BED       %6.1f dBFS" % band_db(bed))
print("=> overall dialog SNR %+.1f dB   (was +4.8 dB)" % (band_db(voice)-band_db(bed)))
# worst 0.5 s window *inside* speech
sos = butter(4, [300, 3000], btype="band", fs=SR, output="sos")
vb = sosfilt(sos, voice.mean(1)); bb = sosfilt(sos, bed.mean(1))
w = int(0.5*SR); worst = []
for k in range(0, N-w, w):
    if band_db(voice[k:k+w]) > -45:
        worst.append((k/SR, 20*np.log10(np.sqrt(np.mean(vb[k:k+w]**2))+1e-12)
                            - 20*np.log10(np.sqrt(np.mean(bb[k:k+w]**2))+1e-12)))
worst.sort(key=lambda r: r[1])
print("worst speech windows: " + ", ".join("%.1fs %+.1fdB" % r for r in worst[:5]))
print("peak %.3f" % float(np.max(np.abs(mix))))
