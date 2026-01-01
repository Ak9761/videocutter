import streamlit as st
import uuid
import os
import subprocess
from yt_dlp import YoutubeDL

st.set_page_config(page_title="YouTube Video Cutter", layout="centered")

st.title("🎬 YouTube Video Cutter")
st.write("Paste a YouTube link with timestamp and create a clip or Short.")

# ---------------- INPUTS ----------------
yt_url = st.text_input(
    "YouTube Video URL (can include timestamp)",
    value="https://youtu.be/giT0ytynSqg?t=1h27m50s"
)

duration = st.number_input(
    "Clip duration (seconds)",
    min_value=1,
    max_value=60,
    value=20
)

make_short = st.checkbox("📱 Convert to YouTube Shorts (9:16)", value=True)

# ---------------- HELPERS ----------------
import re
from urllib.parse import urlparse, parse_qs

def parse_timestamp(url):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    if "t" in qs:
        return parse_time_string(qs["t"][0])
    if "start" in qs:
        return int(qs["start"][0])

    return 0  # default start


def parse_time_string(t):
    if t.isdigit():
        return int(t)

    h = m = s = 0
    match = re.match(r'(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?', t)
    if match:
        h, m, s = match.groups(default="0")
        return int(h) * 3600 + int(m) * 60 + int(s)

    return 0


def seconds_to_hms(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02}:{m:02}:{s:02}"


# ---------------- CORE LOGIC ----------------
def process_video(url, start_time, end_time, output_file, shorts):
    temp_id = uuid.uuid4().hex
    temp_video = f"temp_{temp_id}.mp4"

    # 1️⃣ Download merged video + audio (TEMP)
    ydl_opts = {
        "format": "bv*[height<=720]+ba/b",
        "merge_output_format": "mp4",
        "outtmpl": temp_video,
        "quiet": True,
        "noplaylist": True
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    # 2️⃣ Video filter
    if shorts:
        video_filter = "crop=ih*9/16:ih,scale=1080:1920"
    else:
        video_filter = "scale=1280:720"

    # 3️⃣ Cut + encode
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", start_time,
        "-to", end_time,
        "-i", temp_video,
        "-vf", video_filter,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-c:a", "aac",
        "-b:a", "160k",
        output_file
    ]

    subprocess.run(cmd, check=True)

    # 4️⃣ Cleanup
    os.remove(temp_video)


# ---------------- RUN ----------------
if yt_url and st.button("✂️ Create Clip"):
    start_seconds = parse_timestamp(yt_url)
    start_time = seconds_to_hms(start_seconds)
    end_time = seconds_to_hms(start_seconds + duration)

    output_file = f"clip_{uuid.uuid4().hex}.mp4"

    try:
        with st.spinner("Processing video (may take 1–2 minutes)…"):
            process_video(
                yt_url,
                start_time,
                end_time,
                output_file,
                make_short
            )

        st.success("✅ Video created successfully!")

        with open(output_file, "rb") as f:
            st.download_button(
                "⬇️ Download Video",
                data=f,
                file_name="short.mp4" if make_short else "clip.mp4",
                mime="video/mp4"
            )

    except Exception as e:
        st.error("❌ Video processing failed")
        st.exception(e)

    finally:
        if os.path.exists(output_file):
            os.remove(output_file)
