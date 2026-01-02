from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import FileResponse
from yt_dlp import YoutubeDL
import subprocess
import uuid
import os
import shutil

app = FastAPI(title="YouTube Video Cutter API")

TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# ------------------------
# Health Check
# ------------------------
@app.get("/")
def health():
    return {"status": "ok"}


# ------------------------
# Core Video Processor
# ------------------------
def process_video(
    url: str,
    start: str,
    end: str,
    make_short: bool
) -> str:
    video_id = uuid.uuid4().hex
    temp_video = f"{TEMP_DIR}/{video_id}.mp4"
    output_video = f"{TEMP_DIR}/clip_{video_id}.mp4"

    # 1️⃣ Download ONLY ONCE (best quality, correct audio)
    ydl_opts = {
        "format": "bv*[height<=720]+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": temp_video,
        "quiet": True,
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to download video")

    # 2️⃣ FFmpeg cut command
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", start,
        "-to", end,
        "-i", temp_video,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", "128k",
    ]

    # 3️⃣ Shorts conversion (9:16)
    if make_short:
        cmd += [
            "-vf",
            "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920"
        ]

    cmd.append(output_video)

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="FFmpeg processing failed")
    finally:
        if os.path.exists(temp_video):
            os.remove(temp_video)

    return output_video


# ------------------------
# API Endpoint
# ------------------------
@app.get("/cut")
def cut_video(
    url: str = Query(..., description="YouTube URL"),
    start: str = Query(..., description="Start time HH:MM:SS"),
    end: str = Query(..., description="End time HH:MM:SS"),
    short: bool = Query(False, description="Convert to YouTube Shorts (9:16)")
):
    output = process_video(url, start, end, short)

    return FileResponse(
        output,
        media_type="video/mp4",
        filename="clip.mp4",
        background=lambda: shutil.rmtree(TEMP_DIR, ignore_errors=True)
    )
