#!/usr/bin/env python3
"""Build 'Angoor Khatte Hain' animated moral story video.
1920x1080, 30fps, Ken Burns animation, Hindi subtitles, real Hindi voiceover.
"""
import subprocess, os, re, sys

FF = subprocess.check_output(
    [sys.executable, "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
    text=True).strip()
FONT = "fonts/NotoSansDevanagari.ttf"
os.makedirs("work", exist_ok=True)
os.makedirs("output", exist_ok=True)

def run(cmd):
    print("RUN:", " ".join(cmd[:6]), "...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-4000:])
        raise SystemExit(f"ffmpeg failed: {cmd[0]}")
    return r

def duration(path):
    r = subprocess.run([FF, "-i", path], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    if not m:
        raise ValueError(f"no duration for {path}: {r.stderr[-500:]}")
    return int(m.group(1))*3600 + int(m.group(2))*60 + float(m.group(3))

def write_text(name, text):
    p = f"work/{name}.txt"
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p

# ---- durations ----
d1 = duration("audio/chunk1.mp3")
d2 = duration("audio/chunk2.mp3")
d3 = duration("audio/chunk3.mp3")
d4 = duration("audio/chunk4.mp3")
d5 = duration("audio/chunk5.mp3")
print(f"chunks: {d1:.2f} {d2:.2f} {d3:.2f} {d4:.2f} {d5:.2f}")

GAP = 0.4
TITLE_DUR = 3.0
OUTRO_DUR = 3.5
segs = [
    # name, image, dur, kenburns, subtitle_lines
    ("title", "assets/scene2_fox_jumping.jpg", TITLE_DUR, "out", None),
    ("s1", "assets/scene1_fox_grapes.jpg", d1 + GAP, "in", ["उसने पूरी कोशिश की... जब अंगूर नहीं मिले,", "तो कह दिया — अंगूर खट्टे हैं!"]),
    ("s2", "assets/scene4_people_blame.jpg", d2 + GAP, "panR", ["आज भी कुछ लोग ऐसे हैं —", "असफलता दूसरों पर थोपते हैं।"]),
    ("s3", "assets/scene3_fox_sour.jpg", d3 + GAP, "in", ["किसी को बर्बाद करके आप", "खुद कामयाब नहीं हो सकते।"]),
    ("s4", "assets/scene5_self_improve.jpg", d4 + GAP, "panL", ["दूसरों की बुराई से बेहतर है —", "अपनी कमियों को सुधारना।"]),
    ("s5", "assets/scene6_final_truth.jpg", d5, "in", ["अंगूर खट्टे नहीं थे...", "बस लोमड़ी की पहुँच से बाहर थे!"]),
    ("outro", "assets/scene1_fox_grapes.jpg", OUTRO_DUR, "out", None),
]

def kenburns(kind, frames):
    if kind == "in":
        z = "min(1+0.0012*on,1.45)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif kind == "out":
        z = "max(1.45-0.0012*on,1)"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
    elif kind == "panR":
        z = "1.25"
        x = f"(iw-iw/zoom)*on/{frames}"
        y = "ih/2-(ih/zoom/2)"
    elif kind == "panL":
        z = "1.25"
        x = f"(iw-iw/zoom)*(1-on/{frames})"
        y = "ih/2-(ih/zoom/2)"
    else:
        raise ValueError(kind)
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1920x1080:fps=30"

def drawtext(tf, size, y, alpha="1"):
    return (f"drawtext=fontfile={FONT}:textfile={tf}:fontsize={size}:"
            f"fontcolor=white:borderw=3:bordercolor=black:"
            f"x=(w-text_w)/2:y={y}:box=1:boxcolor=black@0.55:boxborderw=18")

# ---- build video segments ----
seg_files = []
for name, img, dur, kb, subs in segs:
    frames = int(round(dur * 30))
    out = f"work/seg_{name}.mp4"
    seg_files.append(out)
    vf = [
        "scale=2560:1440:force_original_aspect_ratio=increase",
        "crop=2560:1440",
        kenburns(kb, frames),
        "eq=saturation=1.15:contrast=1.06:brightness=0.02",
        "vignette=PI/4",
    ]
    if name == "title":
        t1 = write_text("title1", "अंगूर खट्टे हैं")
        t2 = write_text("title2", "The Fox & The Grapes — एक सीख भरी कहानी")
        vf.append(drawtext(t1, 120, "h*0.32"))
        vf.append(drawtext(t2, 52, "h*0.32+150"))
    elif name == "outro":
        t1 = write_text("outro1", "सीख: अपनी कमियों को सुधारो,")
        t2 = write_text("outro2", "दूसरों को दोष मत दो।")
        t3 = write_text("outro3", "Like | Share | Subscribe")
        vf.append(drawtext(t1, 72, "h*0.34"))
        vf.append(drawtext(t2, 72, "h*0.34+100"))
        vf.append(drawtext(t3, 44, "h*0.34+220"))
    elif subs:
        for i, line in enumerate(subs):
            tf = write_text(f"{name}_{i}", line)
            y = "h-260" if i == 0 else "h-170"
            vf.append(drawtext(tf, 54, y))
    vf.append(f"fade=t=in:st=0:d=0.35")
    vf.append(f"fade=t=out:st={dur-0.35:.2f}:d=0.35")
    vf.append("format=yuv420p")
    run([FF, "-y", "-i", img, "-vf", ",".join(vf),
         "-frames:v", str(frames), "-r", "30",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", out])
    print(f"built {out} dur={dur:.2f}")

# ---- build full audio ----
def silence(dur, name):
    out = f"work/{name}.mp3"
    run([FF, "-y", "-f", "lavfi", "-i", f"anullsrc=r=48000:cl=stereo",
         "-t", str(dur), "-c:a", "libmp3lame", "-b:a", "128k", out])
    return out

sil_title = silence(TITLE_DUR, "sil_title")
sil_gap = silence(GAP, "sil_gap")
sil_outro = silence(OUTRO_DUR, "sil_outro")

# normalize each chunk to 48k stereo wav for clean concat
norm_chunks = []
for i in range(1, 6):
    out = f"work/chunk{i}_48k.wav"
    run([FF, "-y", "-i", f"audio/chunk{i}.mp3",
         "-af", "aresample=48000,aformat=channel_layouts=stereo,volume=1.4,alimiter=limit=0.95",
         "-c:a", "pcm_s16le", out])
    norm_chunks.append(out)

sil_title_w = "work/sil_title.wav"
sil_gap_w = "work/sil_gap.wav"
sil_outro_w = "work/sil_outro.wav"
for src, dst in [(sil_title, sil_title_w), (sil_gap, sil_gap_w), (sil_outro, sil_outro_w)]:
    run([FF, "-y", "-i", src, "-af", "aresample=48000,aformat=channel_layouts=stereo",
         "-c:a", "pcm_s16le", dst])

order = [sil_title_w, norm_chunks[0], sil_gap_w, norm_chunks[1], sil_gap_w,
         norm_chunks[2], sil_gap_w, norm_chunks[3], sil_gap_w, norm_chunks[4], sil_outro_w]
with open("work/audio_list.txt", "w") as f:
    for p in order:
        f.write(f"file '{os.path.abspath(p)}'\n")
run([FF, "-y", "-f", "concat", "-safe", "0", "-i", "work/audio_list.txt",
     "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
     "-c:a", "aac", "-b:a", "192k", "work/full_audio.m4a"])
print("audio built, dur=", duration("work/full_audio.m4a"))

# ---- concat video ----
with open("work/video_list.txt", "w") as f:
    for p in seg_files:
        f.write(f"file '{os.path.abspath(p)}'\n")
run([FF, "-y", "-f", "concat", "-safe", "0", "-i", "work/video_list.txt",
     "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
     "work/video_only.mp4"])

# ---- mux ----
run([FF, "-y", "-i", "work/video_only.mp4", "-i", "work/full_audio.m4a",
     "-c:v", "copy", "-c:a", "copy", "-shortest",
     "-movflags", "+faststart", "output/Angoor_Khatte_Hain_Fox_and_Grapes.mp4"])
print("FINAL:", duration("output/Angoor_Khatte_Hain_Fox_and_Grapes.mp4"))
