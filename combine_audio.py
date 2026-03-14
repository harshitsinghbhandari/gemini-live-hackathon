import sys
import time
import subprocess
from pathlib import Path

# Use local config for sample rates
sys.path.append(str(Path(__file__).parent))
try:
    from configs.agent import config
    SEND_RATE = config.SEND_SAMPLE_RATE
    RECV_RATE = config.RECEIVE_SAMPLE_RATE
except:
    SEND_RATE = 16000
    RECV_RATE = 24000

def stitch(folder, rate, name):
    folder = Path(folder)
    if not folder.exists(): return
    files = sorted(list(folder.glob("*.raw")))
    if not files:
        print(f"No chunks found in {folder}")
        return
    
    # Joining in Python is more robust for raw PCM than ffmpeg concat demuxer
    temp_raw = folder / "joined_temp.raw"
    with open(temp_raw, "wb") as outfile:
        for f in files:
            with open(f, "rb") as infile:
                outfile.write(infile.read())
    
    out = folder.parent / name
    cmd = [
        "ffmpeg", "-y",
        "-f", "s16le",
        "-ar", str(rate),
        "-ac", "1",
        "-i", str(temp_raw),
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",
        str(out)
    ]
    
    print(f"Combining {len(files)} chunks via temporary join...")
    try:
        subprocess.run(cmd, check=True)
        print(f"Done: {out}")
    finally:
        if temp_raw.exists():
            temp_raw.unlink()

if __name__ == "__main__":
    stitch("data/audio/sent", SEND_RATE, f"sent_manual_{int(time.time())}.mp3")
    stitch("data/audio/received", RECV_RATE, f"received_manual_{int(time.time())}.mp3")
