from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
import uuid, os, subprocess
from yt_dlp import YoutubeDL

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/cut")
def cut_video(
    url: str,
    start: str,
    end: str,
    shorts: bool = True
):
    job_id = uuid.uuid4().hex
    temp_video = f"/tmp/input_{job_id}.mp4"
    output_video = f"/tmp/output_{job_id}.mp4"

    # 1️⃣ Download video
    ydl_opts = {
        "format": "bv*[height<=720]+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": temp_video,
        "quiet": True,
        "noplaylist": True
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception:
        raise HTTPException(400, "Failed to download video")

    # 2️⃣ Shorts or normal
    vf = "crop=ih*9/16:ih,scale=1080:1920" if shorts else "scale=1280:720"

    # 3️⃣ Cut & encode
    cmd = [
        "ffmpeg", "-y",
        "-ss", start,
        "-to", end,
        "-i", temp_video,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "160k",
        output_video
    ]

    subprocess.run(cmd, check=True)

    return FileResponse(
        output_video,
        media_type="video/mp4",
        filename="short.mp4"
    )
