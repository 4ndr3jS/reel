"""Package authored engine files only, with deterministic ZIP metadata."""
from pathlib import Path
import zipfile
root = Path(__file__).resolve().parent.parent
with zipfile.ZipFile(root / "public/reel-engine.zip", "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for name in ["start-reel.cmd", "engine/server.py", "engine/launcher.py", "engine/requirements.txt", "engine/QUICKSTART.txt"]:
        entry = zipfile.ZipInfo("reel-engine/" + name, date_time=(2026, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = 0o644 << 16
        archive.writestr(entry, (root / name).read_bytes())
