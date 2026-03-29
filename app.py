import subprocess, sys, os, tempfile, re

def install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

for pkg in ["flask", "flask-cors", "yt-dlp", "static-ffmpeg"]:
    try:
        __import__(pkg.replace("-", "_"))
    except ImportError:
        print(f"Installing {pkg}...")
        install(pkg)

import static_ffmpeg
static_ffmpeg.add_paths()

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return "SoundDrop API is running ✅"

@app.route("/info", methods=["POST"])
def get_info():
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        with yt_dlp.YoutubeDL({"quiet": True, "noplaylist": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title":     info.get("title",     "Unknown"),
                "thumbnail": info.get("thumbnail", ""),
                "duration":  info.get("duration",  0),
                "uploader":  info.get("uploader",  "Unknown"),
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/download", methods=["POST"])
def download():
    data = request.get_json()
    url = data.get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400
    try:
        tmp_dir = tempfile.mkdtemp()
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tmp_dir, "%(title)s.%(ext)s"),
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "quiet": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "audio")

        mp3_file = next(
            (os.path.join(tmp_dir, f) for f in os.listdir(tmp_dir) if f.endswith(".mp3")),
            None
        )
        if not mp3_file:
            return jsonify({"error": "MP3 conversion failed."}), 500

        safe_title = re.sub(r'[^\w\s-]', '', title).strip()[:80]
        return send_file(
            mp3_file,
            as_attachment=True,
            download_name=f"{safe_title}.mp3",
            mimetype="audio/mpeg"
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n🎵 SoundDrop API → http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
