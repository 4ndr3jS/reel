"""REEL's loopback-only download engine. Python 3.11+, yt-dlp, Node and FFmpeg."""
from __future__ import annotations
import argparse
import concurrent.futures
import hmac
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse

ROOT = Path(__file__).resolve().parent
DATA = ROOT / ".data"
DOWNLOADS = DATA / "downloads"
DEPS = Path(os.environ.get("REEL_PYTHON_DEPS", ROOT / ".deps"))
sys.path.insert(0, str(DEPS))
SITE = "https://reel-download-studio-9nov.ampledulse1.chatgpt.site"
PAGES_SITE = "https://4ndr3js.github.io/reel/"
ORIGINS = {SITE, "https://4ndr3js.github.io", "http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:4173", "http://localhost:4173"}
SESSION = secrets.token_urlsafe(32)
JOBS: dict[str, dict] = {}
CACHE: dict[str, tuple[float, dict]] = {}
LOCK = threading.RLock()
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2)
INSPECT_LIMIT = threading.BoundedSemaphore(2)
MAX_BYTES = 1024 * 1024 * 1024
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
YOUTUBE = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
TIKTOK = {"tiktok.com", "www.tiktok.com", "m.tiktok.com", "vm.tiktok.com", "vt.tiktok.com"}

def validate_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ValueError("Paste a valid YouTube or TikTok video link.")
    p = urlparse(value.strip())
    if p.scheme not in ("http", "https") or p.username or p.password or p.port not in (None, 80, 443):
        raise ValueError("Paste a valid YouTube or TikTok video link.")
    if p.hostname in YOUTUBE:
        if p.hostname == "youtu.be":
            video_id = p.path.strip("/")
        elif p.path == "/watch":
            video_id = parse_qs(p.query).get("v", [""])[0]
        else:
            m = re.fullmatch(r"/(?:shorts|live|embed)/([A-Za-z0-9_-]{11})/?", p.path)
            video_id = m[1] if m else ""
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("Use a video or Shorts link, rather than a channel or playlist.")
        return "https://www.youtube.com/watch?v=" + video_id
    if p.hostname in TIKTOK:
        if not (re.fullmatch(r"/@[^/]+/video/\d+/?", p.path) or
                (p.hostname in {"vm.tiktok.com", "vt.tiktok.com"} and re.fullmatch(r"/[A-Za-z0-9]+/?", p.path)) or
                re.fullmatch(r"/t/[A-Za-z0-9]+/?", p.path)):
            raise ValueError("Use a TikTok video or share link, rather than a profile.")
        return "https://" + p.hostname + p.path
    raise ValueError("REEL supports YouTube and TikTok video links.")

def common_options():
    return {
        "quiet": True, "no_warnings": True, "noplaylist": True, "cachedir": False,
        "socket_timeout": 20, "retries": 2, "extractor_retries": 1,
        "fragment_retries": 2, "js_runtimes": {"node": {}},
        "max_filesize": MAX_BYTES,
        "windowsfilenames": True, "restrictfilenames": False,
    }

def check_media(info):
    if not info or info.get("_type") in ("playlist", "multi_video") or info.get("is_live"):
        raise ValueError("Choose a single, finished public video. Playlists and live streams aren’t supported.")
    if (info.get("duration") or 0) > 10800:
        raise ValueError("Choose a video shorter than three hours.")
    if info.get("availability") in ("private", "premium_only", "subscriber_only", "needs_auth"):
        raise ValueError("This video isn’t publicly available.")

def summarize(info, url):
    thumb = info.get("thumbnail") or ""
    if not thumb.startswith("https://"):
        thumb = ""
    return {
        "url": url, "title": str(info.get("title") or "Untitled video")[:300],
        "author": str(info.get("uploader") or info.get("channel") or "")[:150],
        "duration": info.get("duration") or 0, "thumbnail": thumb,
        "platform": "YouTube" if "youtube.com/" in url else "TikTok",
        "heights": sorted({int(f["height"]) for f in info.get("formats", []) if f.get("height")}, reverse=True),
    }

def friendly_error(exc):
    text = str(exc).lower()
    if isinstance(exc, ValueError):
        return str(exc)
    if any(s in text for s in ["sign in", "login", "cookies", "not a bot", "403", "captcha", "unexpected response"]):
        return "The platform is blocking this video on the current connection. Try another public video or try again later."
    if any(s in text for s in ["private", "unavailable", "removed", "not available", "404"]):
        return "This video is unavailable, private, removed, or restricted in your region."
    if "format" in text:
        return "This format isn’t available for that video. Try a lower quality or MP3."
    if "timed out" in text or "timeout" in text:
        return "The platform took too long to respond. Please try again."
    if "ffmpeg" in text:
        return "FFmpeg couldn’t complete the conversion. Check the engine setup and try again."
    return "Couldn’t retrieve this video. Check the link and try again."

def inspect_video(url):
    with LOCK:
        if url in CACHE and time.time() - CACHE[url][0] < 600:
            return CACHE[url][1]
    import yt_dlp
    with yt_dlp.YoutubeDL(common_options()) as ydl:
        info = ydl.extract_info(url, download=False)
    check_media(info)
    result = summarize(info, url)
    with LOCK:
        if len(CACHE) >= 50:
            CACHE.pop(next(iter(CACHE)))
        CACHE[url] = (time.time(), result)
    return result

def emit(value):
    print("REEL:" + json.dumps(value, ensure_ascii=True), flush=True)

def download_worker(request):
    import yt_dlp
    job_id = request["id"]
    if not re.fullmatch("[0-9a-f]{32}", job_id):
        raise ValueError("Invalid job identifier")
    folder = DOWNLOADS / job_id
    folder.mkdir(parents=True, exist_ok=True)
    last_emit = [0.0]
    def progress(d):
        if d["status"] == "finished":
            emit({"state": "converting", "percent": 92, "message": "Finishing your file…"})
        elif d["status"] == "downloading" and time.monotonic() - last_emit[0] > .4:
            last_emit[0] = time.monotonic()
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            if done > MAX_BYTES:
                raise ValueError("This file exceeds the 1 GB per-download limit.")
            percent = min(90, 5 + done / total * 85) if total else 5
            emit({"state": "downloading", "percent": percent, "message": "Downloading from source…"})
    opts = common_options()
    opts.update({"outtmpl": str(folder / "media.%(ext)s"), "progress_hooks": [progress],
                 "postprocessor_hooks": [lambda d: emit({"state": "converting", "percent": 95, "message": "Converting your file…"}) if d["status"] == "started" else None]})
    if request["format"] == "mp3":
        opts.update({"format": "bestaudio/best", "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": request["quality"]}]})
        if request["mono"]:
            opts["postprocessor_args"] = {"extractaudio+ffmpeg_o": ["-af", "aformat=channel_layouts=stereo,pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1"]}
    else:
        q = int(request["quality"])
        opts.update({"format": f"bv*[ext=mp4][height<={q}]+ba[ext=m4a]/b[ext=mp4][height<={q}]/bv*[height<={q}]+ba/b[height<={q}]",
                     "merge_output_format": "mp4", "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}]})
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(request["url"], download=False)
            check_media(info)
            metadata = summarize(info, request["url"])
            emit({"title": metadata["title"], "state": "downloading", "percent": 3, "message": "Found it. Starting download…"})
            ydl.process_ie_result(info, download=True)
        output = folder / ("media." + request["format"])
        if not output.is_file() or output.stat().st_size < 100:
            raise ValueError("The source didn’t return a usable file. Try another format.")
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type", "-of", "json", str(output)], capture_output=True, timeout=30, creationflags=FLAGS)
        if probe.returncode:
            raise ValueError("The file couldn’t be verified. Please try again.")
        details = json.loads(probe.stdout)
        types = {s["codec_type"] for s in details.get("streams", [])}
        if request["format"] == "mp3" and "audio" not in types or request["format"] == "mp4" and "video" not in types:
            raise ValueError("The source didn’t contain the requested media.")
        title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", metadata["title"]).strip(". ")[:140] or "REEL download"
        emit({"state": "complete", "percent": 100, "message": "Ready to save", "title": metadata["title"],
              "filename": title + "." + request["format"], "bytes": output.stat().st_size})
    except Exception as exc:
        (folder / "error.log").write_text(type(exc).__name__ + ": " + str(exc)[:2000], encoding="utf-8")
        emit({"state": "error", "percent": 0, "message": friendly_error(exc)})
        sys.exit(1)

def execute_job(job_id, request):
    with LOCK:
        JOBS[job_id].update(state="fetching", message="Finding your video…", percent=1)
    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--worker"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", creationflags=FLAGS)
    proc.stdin.write(json.dumps({**request, "id": job_id}) + "\n")
    proc.stdin.close()
    timed_out = threading.Event()
    def stop():
        timed_out.set()
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, creationflags=FLAGS)
        else:
            proc.kill()
    timer = threading.Timer(900, stop)
    timer.daemon = True
    timer.start()
    try:
        for line in proc.stdout:
            if not line.startswith("REEL:"):
                continue
            update = json.loads(line[5:])
            with LOCK:
                JOBS[job_id].update(update)
                if update.get("state") == "complete":
                    JOBS[job_id]["download"] = "/api/files/" + job_id
        proc.wait()
        with LOCK:
            if timed_out.is_set():
                JOBS[job_id].update(state="error", percent=0, message="This download took too long. Try a shorter video or lower quality.")
            elif JOBS[job_id]["state"] not in ("complete", "error"):
                JOBS[job_id].update(state="error", percent=0, message="The engine interrupted this download. Please try again.")
    except Exception:
        stop()
        with LOCK:
            JOBS[job_id].update(state="error", percent=0, message="The engine couldn’t finish this download.")
    finally:
        timer.cancel()

class Handler(BaseHTTPRequestHandler):
    server_version = "Reel/1.0"
    def log_message(self, *_args):
        pass
    def allowed(self):
        host = self.headers.get("Host", "")
        origin = self.headers.get("Origin")
        return host in {"127.0.0.1:8941", "localhost:8941"} and (origin is None or origin in ORIGINS)
    def response_headers(self):
        origin = self.headers.get("Origin")
        if origin in ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
    def json(self, code, payload):
        data = json.dumps(payload, ensure_ascii=True).encode()
        self.send_response(code); self.response_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data))); self.end_headers()
        self.wfile.write(data)
    def do_OPTIONS(self):
        if not self.allowed():
            return self.json(403, {"error": "Origin not allowed"})
        self.send_response(204); self.response_headers()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Reel-Session")
        self.send_header("Access-Control-Max-Age", "600"); self.end_headers()
    def do_GET(self):
        if not self.allowed():
            return self.json(403, {"error": "Origin not allowed"})
        path = urlparse(self.path).path
        if path == "/api/health":
            ready = bool(importlib.util.find_spec("yt_dlp") and shutil.which("ffmpeg") and shutil.which("ffprobe") and shutil.which("node"))
            return self.json(200, {"ready": ready, "session": SESSION, "version": "1.0"})
        match = re.fullmatch(r"/api/(jobs|files)/([0-9a-f]{32})", path)
        if not match:
            return self.json(404, {"error": "Not found"})
        with LOCK:
            job = dict(JOBS.get(match[2], {}))
        if not job:
            return self.json(404, {"error": "File belongs to a previous session"})
        if match[1] == "jobs":
            return self.json(200, job)
        if job["state"] != "complete":
            return self.json(409, {"error": "File is not ready"})
        file = DOWNLOADS / match[2] / ("media." + job["format"])
        if not file.is_file():
            return self.json(404, {"error": "This file has expired"})
        total = file.stat().st_size
        start, end, status = 0, total - 1, 200
        range_header = self.headers.get("Range")
        if range_header:
            m = re.fullmatch(r"bytes=(\d+)-(\d*)", range_header)
            if not m:
                return self.json(416, {"error": "Invalid range"})
            start = int(m[1]); end = min(int(m[2]), total - 1) if m[2] else total - 1
            if start > end or start >= total:
                return self.json(416, {"error": "Invalid range"})
            status = 206
        self.send_response(status); self.response_headers()
        self.send_header("Content-Type", "audio/mpeg" if job["format"] == "mp3" else "video/mp4")
        self.send_header("Content-Disposition", "attachment; filename=\"reel-download." + job["format"] + "\"; filename*=UTF-8''" + quote(job["filename"], safe=""))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{total}")
        self.end_headers()
        try:
            with file.open("rb") as f:
                f.seek(start); remaining = end - start + 1
                while remaining:
                    chunk = f.read(min(65536, remaining))
                    if not chunk: break
                    self.wfile.write(chunk); remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
    def do_POST(self):
        if not self.allowed() or not hmac.compare_digest(self.headers.get("X-Reel-Session", ""), SESSION):
            return self.json(403, {"error": "Reconnect to the REEL engine and try again."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > 16384 or self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.json(400, {"error": "Expected a small JSON request"})
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict): raise ValueError("Invalid request")
            url = validate_url(body.get("url"))
            if self.path == "/api/inspect":
                if not INSPECT_LIMIT.acquire(blocking=False):
                    return self.json(429, {"error": "Two videos are already being checked. Try again in a moment."})
                try:
                    return self.json(200, inspect_video(url))
                finally:
                    INSPECT_LIMIT.release()
            if self.path != "/api/jobs":
                return self.json(404, {"error": "Not found"})
            fmt = body.get("format")
            quality = str(body.get("quality"))
            if fmt not in ("mp3", "mp4") or quality not in ({"128", "192", "320"} if fmt == "mp3" else {"480", "720", "1080", "2160"}):
                raise ValueError("Choose an available format and quality.")
            with LOCK:
                active = sum(j["state"] not in ("complete", "error") for j in JOBS.values())
                if active >= 8:
                    return self.json(429, {"error": "Your queue is full. Let a download finish first."})
                used = sum(f.stat().st_size for f in DOWNLOADS.rglob("*") if f.is_file())
                if used >= 4 * MAX_BYTES:
                    return self.json(429, {"error": "The engine cache is full. Save your files and restart the engine to clear it."})
                job_id = secrets.token_hex(16)
                meta = CACHE.get(url, (0, {}))[1]
                job = {"id": job_id, "url": url, "title": meta.get("title") or "Finding your video…", "format": fmt, "state": "queued", "percent": 0, "message": "Waiting on the desk…", "created": time.time()}
                JOBS[job_id] = job
                payload = {"url": url, "format": fmt, "quality": quality, "mono": body.get("mono") is True}
                POOL.submit(execute_job, job_id, payload)
                return self.json(202, dict(job))
        except ValueError as exc:
            self.json(400, {"error": str(exc)})
        except Exception as exc:
            self.json(422, {"error": friendly_error(exc)})

def main():
    if "--worker" in sys.argv:
        download_worker(json.loads(sys.stdin.readline()))
        return
    server = ThreadingHTTPServer(("127.0.0.1", 8941), Handler)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    # Only remove this app's UUID-named temporary folders within the verified cache root.
    root = DOWNLOADS.resolve()
    for folder in root.iterdir():
        if folder.is_dir() and re.fullmatch("[0-9a-f]{32}", folder.name) and folder.resolve().parent == root:
            shutil.rmtree(folder)
    print("REEL engine ready at http://127.0.0.1:8941", flush=True)
    print("Keep this running while using REEL. Ctrl+C to stop.", flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
if __name__ == "__main__":
    main()
