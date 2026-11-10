"""Check the Windows engine setup, install local Python dependencies, and start REEL."""
from pathlib import Path
import importlib.metadata
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
DEPS = Path(os.environ.get("REEL_PYTHON_DEPS", ROOT / ".deps"))

def main():
    print("REEL engine setup", flush=True)
    if sys.version_info < (3, 11):
        print("Python 3.11 or later is required. Install it from https://www.python.org/downloads/", flush=True)
        return 1
    missing = [name for name in ("ffmpeg", "ffprobe", "node") if not shutil.which(name)]
    if missing:
        print("Missing programs: " + ", ".join(missing), flush=True)
        if "ffmpeg" in missing or "ffprobe" in missing:
            print("Install FFmpeg (which includes ffprobe): winget install Gyan.FFmpeg", flush=True)
        if "node" in missing:
            print("Install Node.js 22 or later from https://nodejs.org/", flush=True)
        print("Then open a new terminal and run start-reel.cmd again.", flush=True)
        return 1
    requirements = dict(
        line.strip().split("==", 1)
        for line in (ROOT / "requirements.txt").read_text().splitlines()
        if line.strip() and not line.startswith("#")
    )
    installed = {dist.metadata["Name"].lower().replace("_", "-"): dist.version
                 for dist in importlib.metadata.distributions(path=[str(DEPS)])}
    if any(installed.get(name) != version for name, version in requirements.items()):
        print("Installing the engine's Python dependencies into " + str(DEPS), flush=True)
        result = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
                                 "--upgrade", "--target", str(DEPS), "-r", str(ROOT / "requirements.txt")])
        if result.returncode:
            print("Dependency installation failed. Check your internet connection and try again.", flush=True)
            return result.returncode
    check = subprocess.run(
        [sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import yt_dlp, yt_dlp_ejs, curl_cffi", str(DEPS)],
        capture_output=True, text=True)
    if check.returncode:
        print("The engine's Python dependencies could not load. Re-extract the latest engine ZIP into a new folder and run it again.", flush=True)
        print(check.stderr, flush=True)
        return 1
    print("Python, Node.js, FFmpeg and the downloader are ready.", flush=True)
    if "--check" in sys.argv:
        return 0
    return subprocess.call([sys.executable, str(ROOT / "server.py"), "--open"])

if __name__ == "__main__":
    sys.exit(main())
