import streamlit as st
import uuid
import os
import subprocess
from yt_dlp import YoutubeDL

st.set_page_config(page_title="YouTube Video Cutter", layout="centered")

st.title("🎬 YouTube Video Cutter (Stream & Cut)")
st.write("Cuts directly from YouTube stream. No full video download.")

# -------- INPUTS --------
yt_url = st.text_input(
    "YouTube Video URL",
    value="https://youtu.be/giT0ytynSqg"
)

start_time = st.text_input("Start Time (HH:MM:SS)", "01:27:50")
end_time = st.text_input("End Time (HH:MM:SS)", "01:28:10")


# -------- CORE FUNCTION --------
def cut_video_stream(url, start, end, output_file):
    # 1️⃣ Extract streaming URLs (NO DOWNLOAD)
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get("formats", [])

        best = None
        for f in formats:
            if f.get("vcodec") != "none" and f.get("acodec") != "none":
                best = f

        if not best:
            raise RuntimeError("No combined audio+video stream found")

        stream_url = best["url"]

    # 2️⃣ Fast cut (keyframe-based)
    cmd = cmd = [
    "ffmpeg",
    "-y",
    "-ss", start,
    "-to", end,
    "-i", stream_url,

    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "23",
    "-pix_fmt", "yuv420p",
    "-profile:v", "main",
    "-level", "4.0",
    "-movflags", "+faststart",

    "-c:a", "aac",
    "-b:a", "128k",

    output_file
]

    subprocess.run(cmd, check=True)


# -------- UI ACTION --------
if yt_url and st.button("✂️ Cut Video"):
    output_file = f"clip_{uuid.uuid4()}.mp4"

    try:
        with st.spinner("⏳ Streaming & cutting (no full download)…"):
            cut_video_stream(yt_url, start_time, end_time, output_file)

        st.success("✅ Clip created successfully!")

    except Exception:
        st.warning("⚠️ Fast cut failed. Retrying with re-encode (slower but guaranteed)…")

        # 🔁 Guaranteed fallback (re-encode)
        fallback_cmd = [
            "ffmpeg",
            "-y",
            "-ss", start_time,
            "-to", end_time,
            "-i", yt_url,
            "-c:v", "libx264",
            "-c:a", "aac",
            output_file
        ]
        subprocess.run(fallback_cmd, check=True)

        st.success("✅ Clip created (re-encoded)")

    # -------- DOWNLOAD --------
    if os.path.exists(output_file):
        with open(output_file, "rb") as f:
            st.download_button(
                "⬇️ Download Clip",
                data=f.read(),
                file_name="clip.mp4",
                mime="video/mp4"
            )

        os.remove(output_file)
