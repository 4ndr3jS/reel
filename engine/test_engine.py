"""Integration checks against a running engine; --live also verifies a real MP4."""
import json
import sys
import time
import unittest
import array
import subprocess
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BASE = "http://127.0.0.1:8941"
ORIGIN = "http://127.0.0.1:5173"
def request(path, body=None, headers=None):
    h = {"Origin": ORIGIN}
    if body is not None:
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    req = Request(BASE + path, data=json.dumps(body).encode() if body is not None else None, headers=h)
    try:
        with urlopen(req, timeout=120) as r:
            return r.status, dict(r.headers), r.read()
    except HTTPError as e:
        return e.code, dict(e.headers), e.read()

class EngineTests(unittest.TestCase):
    def setUp(self):
        status, _, raw = request("/api/health")
        self.assertEqual(status, 200)
        health = json.loads(raw)
        self.assertTrue(health["ready"])
        self.auth = {"X-Reel-Session": health["session"]}
    def test_other_websites_cannot_access_engine(self):
        self.assertEqual(request("/api/health", headers={"Origin": "https://example.com"})[0], 403)
    def test_github_pages_can_connect(self):
        origin = "https://4ndr3js.github.io"
        status, headers, raw = request("/api/health", headers={"Origin": origin})
        self.assertEqual(status, 200)
        self.assertEqual(headers["Access-Control-Allow-Origin"], origin)
        health = json.loads(raw)
        self.assertEqual(health["service"], "reel")
        self.assertEqual(health["version"], "1.1.0")
        self.assertEqual(health["missing"], [])
        req = Request(BASE + "/api/jobs", method="OPTIONS", headers={
            "Origin": origin, "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-reel-session",
            "Access-Control-Request-Private-Network": "true"})
        with urlopen(req, timeout=5) as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers["Access-Control-Allow-Origin"], origin)
            self.assertEqual(response.headers["Access-Control-Allow-Private-Network"], "true")
    def test_status_page_does_not_expose_session(self):
        status, _, raw = request("/")
        self.assertEqual(status, 200)
        self.assertIn(b"REEL engine 1.1.0", raw)
        self.assertNotIn(self.auth["X-Reel-Session"].encode(), raw)
    def test_missing_session_rejected(self):
        self.assertEqual(request("/api/jobs", {"url": "https://youtu.be/nc2ABcreL7c"})[0], 403)
    def test_invalid_and_private_network_urls_rejected(self):
        for url in ["http://127.0.0.1/secret", "file:///etc/passwd", "https://youtube.com.evil.test/watch?v=nc2ABcreL7c", "https://user:pass@youtube.com/watch?v=nc2ABcreL7c", "https://youtube.com/playlist?list=123", "https://youtube.com:8080/watch?v=nc2ABcreL7c"]:
            with self.subTest(url=url):
                self.assertEqual(request("/api/inspect", {"url": url}, self.auth)[0], 400)
    def test_invalid_format_and_quality_rejected(self):
        for fmt, quality in [("exe", "1080"), ("mp4", "99999"), ("mp3", "999")]:
            self.assertEqual(request("/api/jobs", {"url": "https://youtu.be/nc2ABcreL7c", "format": fmt, "quality": quality}, self.auth)[0], 400)
    def test_missing_file_and_traversal(self):
        for path in ["/api/files/" + "0" * 32, "/api/files/../../server.py"]:
            self.assertEqual(request(path)[0], 404)

def check_download(url, fmt, quality, mono=False):
    auth = {"X-Reel-Session": json.loads(request("/api/health")[2])["session"]}
    code, _, raw = request("/api/jobs", {"url": url, "format": fmt, "quality": quality, "mono": mono}, auth)
    assert code == 202, raw
    job = json.loads(raw)
    for _ in range(150):
        code, _, raw = request("/api/jobs/" + job["id"])
        job = json.loads(raw)
        if job["state"] in ("complete", "error"): break
        time.sleep(2)
    assert job["state"] == "complete", job
    status, headers, data = request(job["download"], headers={"Range": "bytes=0-63"})
    assert status == 206 and len(data) == 64, (status, headers)
    if fmt == "mp4":
        assert b"ftyp" in data
    if mono:
        file = Path(__file__).parent / ".data" / "downloads" / job["id"] / "media.mp3"
        result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(file), "-af", "pan=mono|c0=c0-c1", "-f", "f32le", "-"], capture_output=True, timeout=30)
        assert result.returncode == 0
        samples = array.array("f", result.stdout)
        assert max(map(abs, samples)) < 0.00001, "Left/right channels are different"
    print(json.dumps({"test": ("tiktok" if "tiktok" in url else "youtube") + "_" + fmt + ("_dual_mono" if mono else ""), "status": "PASS", "bytes": job["bytes"]}), flush=True)

def live():
    check_download("https://youtu.be/nc2ABcreL7c", "mp4", "480")
    check_download("https://youtu.be/nc2ABcreL7c", "mp3", "192", True)
    auth = {"X-Reel-Session": json.loads(request("/api/health")[2])["session"]}
    status, _, raw = request("/api/inspect", {"url": "https://www.tiktok.com/@pokemonlife22/video/7059698374567611694"}, auth)
    data = json.loads(raw)
    print(json.dumps({"test": "live_tiktok_metadata", "http_status": status, "title": data.get("title"), "error": data.get("error")}), flush=True)
    assert status == 200, data
    check_download("https://www.tiktok.com/@pokemonlife22/video/7059698374567611694", "mp4", "2160")
if __name__ == "__main__":
    if "--live" in sys.argv: live()
    else: unittest.main()
