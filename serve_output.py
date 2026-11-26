#!/usr/bin/env python3
"""Static server for output/ with HTTP Range support (206) — required for
video seeking, resumable downloads and iOS/Safari playback."""
import os, re, sys, mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("image/jpeg", ".jpg")

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        # allow embedding in the Arena preview iframe
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_GET(self):
        # friendly short links
        if self.path in ("/download", "/dl", "/video"):
            self.send_response(302)
            self.send_header("Location", "/Angoor_Khatte_Hain_LIVE_ANIMATION.mp4")
            self.end_headers()
            return
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().do_GET()
        size = os.path.getsize(path)
        ctype = self.guess_type(path)

        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng.strip())
            if m:
                start_s, end_s = m.groups()
                if start_s == "" and end_s:                 # suffix range
                    start = max(0, size-int(end_s)); end = size-1
                else:
                    start = int(start_s or 0)
                    end = int(end_s) if end_s else size-1
                end = min(end, size-1)
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
                length = end-start+1
                self.send_response(206)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.send_header("Content-Length", str(length))
                self.end_headers()
                with open(path, "rb") as f:
                    f.seek(start)
                    left = length
                    while left > 0:
                        chunk = f.read(min(256*1024, left))
                        if not chunk: break
                        try:
                            self.wfile.write(chunk)
                        except (BrokenPipeError, ConnectionResetError):
                            return
                        left -= len(chunk)
                return

        # full body
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(size))
        self.end_headers()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(256*1024)
                if not chunk: break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return

    def do_HEAD(self):
        path = self.translate_path(self.path)
        if not os.path.isfile(path):
            return super().do_HEAD()
        size = os.path.getsize(path)
        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Length", str(size))
        self.end_headers()

if __name__ == "__main__":
    os.makedirs(ROOT, exist_ok=True)
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"serving {ROOT} on http://0.0.0.0:{PORT}", flush=True)
    srv.serve_forever()
