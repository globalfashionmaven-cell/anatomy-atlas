"""
Claude 아티팩트(공개 공유) 배포용 빌드.

공개 공유는 이미지로 JPEG·PNG·GIF·WebP 만 허용하고 .glb 파일을 받지 않으므로:
  1) SVG 도판·도식 → PNG (먼저 tools/export_png_server.py + tools/export_png.html 로 build/png 생성)
  2) data/media.json, data/chapters.json 의 .svg 경로 → .png 로 바꾼 사본
  3) models/*.glb → GLB 바이트를 base64로 담은 models/*.b64.json, data/models3d.json 사본의 url 변경
  4) 업로드할 파일 목록(게시 경로 → 원본 경로)을 build/artifact/files.json 으로 출력
원본(로컬 실행용 SVG·GLB)은 바꾸지 않습니다.

사용법: python3 tools/build_artifact.py
"""
import base64
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
B = os.path.join(ROOT, "build", "artifact")
PNG = os.path.join(ROOT, "build", "png")


def load(p):
    return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))


def dump(obj, name):
    path = os.path.join(B, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return os.path.relpath(path, ROOT)


def main():
    files = {}
    # 앱 코드·데이터·라이브러리
    for d in ("assets", "data", "vendor"):
        for dp, _, fs in os.walk(os.path.join(ROOT, d)):
            for f in fs:
                if f.startswith("."):
                    continue
                rel = os.path.relpath(os.path.join(dp, f), ROOT)
                files[rel] = {"from": rel, "contentType": "text/plain"} if f == "LICENSE" else rel

    # 미디어: PNG 로
    media = load("data/media.json")
    missing = []
    for m in media:
        if m["url"].endswith(".svg"):
            png = m["url"][:-4] + ".png"
            src = os.path.join("build", "png", png)
            if not os.path.exists(os.path.join(ROOT, src)):
                missing.append(src)
            m["url"] = png
            files[png] = src
    if missing:
        raise SystemExit(f"PNG 없음 {len(missing)}개 — 먼저 tools/export_png.html 로 내보내세요: {missing[:3]}")
    files["data/media.json"] = dump(media, "data/media.json")
    chapters = load("data/chapters.json")
    for c in chapters:
        if c.get("thumbnail", "").endswith(".svg"):
            c["thumbnail"] = c["thumbnail"][:-4] + ".png"
    files["data/chapters.json"] = dump(chapters, "data/chapters.json")

    # 3D 모델: base64 JSON
    reg = load("data/models3d.json")
    for m in reg["models"]:
        raw = open(os.path.join(ROOT, m["url"]), "rb").read()
        out = m["url"].replace(".glb", ".b64.json")
        files[out] = dump({"format": "glb-base64", "source": m["url"], "bytes": len(raw),
                           "glb": base64.b64encode(raw).decode()}, out)
        m["url"] = out
    files["data/models3d.json"] = dump(reg, "data/models3d.json")

    # 이미지 형식 검사: 허용 형식 외 이미지가 남아 있으면 중단
    bad = [k for k in files if k.lower().endswith((".svg", ".glb", ".bmp", ".tif", ".tiff"))]
    if bad:
        raise SystemExit(f"허용되지 않는 형식: {bad}")
    json.dump(files, open(os.path.join(B, "files.json"), "w", encoding="utf-8"), ensure_ascii=False)
    size = sum(os.path.getsize(os.path.join(ROOT, v["from"] if isinstance(v, dict) else v)) for v in files.values())
    print(f"{len(files)} files, {size / 1e6:.1f} MB → build/artifact/files.json")


if __name__ == "__main__":
    main()
