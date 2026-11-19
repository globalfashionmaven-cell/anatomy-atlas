"""
공개판(2D 전용) 빌드 — build_artifact.py 결과에서 3D 관련 파일을 뺀 업로드 목록과 로컬 확인용 사본을 만듭니다.

  python3 tools/build_artifact.py   (먼저)
  python3 tools/build_public.py

결과
  build/public/files.json   게시 경로 → 원본 경로
  artifact-public.html      Three.js import map 을 뺀 공개 페이지
  build/site-public/        로컬 확인용 (python3 -m http.server -d build/site-public 8125)
3D 모델 목록을 비운 등록부를 넣어 3D 탭·3D 링크가 자동으로 숨겨집니다.
"""
import json
import os
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.chdir(ROOT)
f = json.load(open("build/artifact/files.json"))
pub = {}
for k, v in f.items():
    if k.startswith(("vendor/", "models/", "data/mappings/")) or k in ("assets/js/viewer3d/viewer3d.js", "assets/js/viewer3d/motion.js"):
        continue
    pub[k] = v
reg = json.load(open("data/models3d.json", encoding="utf-8"))
reg["models"] = []
os.makedirs("build/public/data", exist_ok=True)
json.dump(reg, open("build/public/data/models3d.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
pub["data/models3d.json"] = "build/public/data/models3d.json"
json.dump({"version": 1, "note": "공개판에는 3D 동작이 없습니다", "motions": []},
          open("build/public/data/motions3d.json", "w", encoding="utf-8"), ensure_ascii=False)
pub["data/motions3d.json"] = "build/public/data/motions3d.json"

s = open("artifact.html", encoding="utf-8").read()
i = s.index("<!-- Three.js")
j = s.index("</script>", i) + len("</script>")
s = s[:i] + s[j:]
open("artifact-public.html", "w", encoding="utf-8").write(s.replace("<title>해부 아틀라스</title>", "<title>해부 아틀라스 공개판</title>"))
json.dump(pub, open("build/public/files.json", "w"), ensure_ascii=False)

src = lambda v: v["from"] if isinstance(v, dict) else v  # noqa: E731
size = sum(os.path.getsize(src(v)) for v in pub.values())
print(len(pub), "files", round(size / 1e6, 1), "MB", sorted({os.path.splitext(k)[1] for k in pub}))
shutil.rmtree("build/site-public", ignore_errors=True)
for k, v in pub.items():
    os.makedirs(os.path.dirname("build/site-public/" + k), exist_ok=True)
    shutil.copy(src(v), "build/site-public/" + k)
shutil.copy("artifact-public.html", "build/site-public/index.html")
