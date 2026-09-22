"""burn_subs.py — burns ASS subtitles onto the v3 video."""
import subprocess, shutil, os
from pathlib import Path

ass_src = Path("workspace/runs/history_of_england_v3/captions.ass")
tmp_ass = Path(os.environ["TEMP"]) / "eng_captions.ass"
shutil.copy(ass_src, tmp_ass)

# FFmpeg Windows path: forward slashes, escaped colon after drive letter
p = str(tmp_ass.resolve()).replace("\\", "/")
drive = p[0]   # e.g. "C"
rest  = p[2:]  # e.g. "/Users/..."
esc   = drive + "\\:" + rest   # -> "C\:/Users/..."
print("Escaped ASS path:", esc)

raw   = "workspace/runs/history_of_england_v3/10_england_v3_final.mp4"
final = "workspace/runs/history_of_england_v3/10_england_v3_subtitled.mp4"

vf = "subtitles='" + esc + "'"
print("VF:", vf)

cmd = [
    "ffmpeg", "-y",
    "-i", raw,
    "-vf", vf,
    "-c:v", "libx264", "-preset", "medium", "-crf", "18",
    "-pix_fmt", "yuv420p",
    "-c:a", "copy",
    final
]
r = subprocess.run(cmd, capture_output=True, text=True)
print("Return code:", r.returncode)
if r.returncode != 0:
    print("STDERR (last 800 chars):")
    print(r.stderr[-800:])
else:
    sz = round(Path(final).stat().st_size / 1024 / 1024, 1)
    print(f"[OK] {final} — {sz} MB")

# Either way, verify output
out = Path(final)
if out.exists():
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(out)],
        capture_output=True, text=True
    )
    print("Duration:", probe.stdout.strip(), "s")
    # Extract QC frames
    for t in [5, 18, 25, 33, 41, 48]:
        fp = Path(f"workspace/runs/history_of_england_v3/qc_frame_{t:02d}s.jpg")
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(t), "-i", str(out),
            "-vframes", "1", "-q:v", "2", str(fp)
        ], capture_output=True)
        if fp.exists():
            print(f"  Frame {t}s -> {round(fp.stat().st_size/1024)}KB")
