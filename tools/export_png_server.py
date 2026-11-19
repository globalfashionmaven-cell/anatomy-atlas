"""
SVG → PNG 내보내기용 로컬 서버 (공개 공유처럼 SVG를 받지 않는 호스팅용)

  python3 tools/export_png_server.py        → http://localhost:8124/tools/export_png.html 열기

- 프로젝트 폴더를 그대로 제공하고,
- 브라우저가 그린 PNG를 PUT /__export/<경로>.png 로 받아 build/png/<경로>.png 에 저장합니다.
- 저장 위치는 build/png 아래로 제한됩니다. localhost 에서만 받습니다.
"""
import http.server
import os
import socketserver

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "build", "png")


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def do_PUT(self):
        if not self.path.startswith("/__export/") or not self.path.endswith(".png"):
            self.send_error(400, "only /__export/*.png")
            return
        rel = os.path.normpath(self.path[len("/__export/"):]).lstrip("/")
        target = os.path.abspath(os.path.join(OUT, rel))
        if not target.startswith(OUT + os.sep):
            self.send_error(400, "bad path")
            return
        n = int(self.headers.get("Content-Length", 0))
        data = self.rfile.read(n)
        if not data.startswith(b"\x89PNG"):
            self.send_error(400, "not png")
            return
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(data)
        self.send_response(201)
        self.end_headers()


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


if __name__ == "__main__":
    with Server(("127.0.0.1", 8124), Handler) as s:
        print("serving on http://localhost:8124", flush=True)
        s.serve_forever()
