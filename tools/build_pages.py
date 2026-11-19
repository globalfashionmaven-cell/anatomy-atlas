"""
GitHub Pages 배포 폴더 만들기 — 로컬 앱(localhost:8123)과 같은 내용 그대로 (3D 포함, SVG 도판 그대로)

  python3 tools/build_pages.py            → build/gh-pages/ 갱신 + 그 안의 git 저장소에 커밋
  cd build/gh-pages && git push            → 1~2분 뒤 GitHub Pages 주소에 반영

- 앱 실행에 필요한 파일만 복사합니다 (index.html, assets, data, media, models, vendor, 보고서).
- 원본 3D 소스(sources/, 118MB)·빌드 산출물·도구는 올리지 않습니다.
- build/gh-pages 는 프로젝트 저장소와 별개의 git 저장소입니다 (프로젝트 작업 이력은 올라가지 않음).
- .nojekyll 을 넣어 GitHub 가 파일을 가공하지 않게 합니다.
"""
import os
import shutil
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.path.join(ROOT, "build", "gh-pages")
DIRS = ["assets", "data", "media", "models", "vendor"]
FILES = ["index.html", "README.md", "AUDIT_REPORT.md", "CONTENT_COMPLETION_REPORT.md", "IMAGE_ASSET_REPORT.md",
         "3D_MOTION_REPORT.md", "QA_REPORT.md"]


def git(*args, check=True):
    return subprocess.run(["git", "-c", "user.name=anatomy-atlas", "-c", "user.email=atlas@localhost", *args],
                          cwd=OUT, check=check, capture_output=True, text=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    # .git 은 남기고 나머지를 새로 채움
    for name in os.listdir(OUT):
        if name == ".git":
            continue
        p = os.path.join(OUT, name)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    for d in DIRS:
        shutil.copytree(os.path.join(ROOT, d), os.path.join(OUT, d), ignore=shutil.ignore_patterns(".DS_Store"))
    for f in FILES:
        if os.path.exists(os.path.join(ROOT, f)):
            shutil.copy(os.path.join(ROOT, f), os.path.join(OUT, f))
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    if not os.path.isdir(os.path.join(OUT, ".git")):
        git("init", "-q", "-b", "main")
    git("add", "-A")
    rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    r = git("commit", "-q", "-m", f"사이트 갱신 (프로젝트 {rev})", check=False)
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(OUT) if ".git" not in dp for f in fs)
    print(f"build/gh-pages: {size / 1e6:.1f} MB ·", "커밋함" if r.returncode == 0 else "바뀐 것 없음")


if __name__ == "__main__":
    main()
