"""
전수조사(감사) 스크립트 — 챕터·항목·이미지·3D 연결 상태를 자동 검사해 마크다운 표로 출력

사용법:
  python3 tools/audit.py                 → 표준출력
  python3 tools/audit.py --out FILE.md   → 파일로 저장

챕터 상태 분류
  완료        : 근육·뼈(또는 관절)·움직임 항목이 있고, 근육 필수 정보가 모두 있고, 모든 근육에 도판이 있음
  보완 필요   : 항목은 있으나 필수 정보·도판·움직임 일부 부족
  미작성      : 항목 0개
  (모든 항목은 전문가 검수 전이므로 별도로 '검증 필요' 열에 표시)
"""
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REQ_MUSCLE = ["origin", "insertion", "innervation", "action", "synergists", "antagonists", "relatedJoints"]


def load(p):
    return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))


def main():
    chapters = load("data/chapters.json")
    items = load("data/items.json")
    media = load("data/media.json")
    reg = load("data/models3d.json")
    mapped = set()
    related3d = set()
    for m in reg["models"]:
        mp = load(m["mapping"])["meshes"]
        mapped |= {x["anatomyItemId"] for x in mp if x.get("anatomyItemId")}
        related3d |= set(m.get("relatedItems", []))
    by_item = defaultdict(list)
    for m in media:
        by_item[m["anatomyItemId"]].append(m)
    missing_files = [m["url"] for m in media if not os.path.exists(os.path.join(ROOT, m["url"]))]
    no_alt = [m["id"] for m in media if not m.get("altText")]
    no_src = [m["id"] for m in media if not (m.get("license") or m.get("source"))]
    ids = Counter(i["id"] for i in items)
    dup = [k for k, c in ids.items() if c > 1]
    known = set(ids)
    bad_refs = []
    for it in items:
        refs = it.get("relatedBones", []) + it.get("relatedJoints", []) + it.get("relatedMovements", []) + it.get("relatedItems", []) \
            + it.get("targetMuscles", []) + it.get("assistingMuscles", []) + it.get("antagonistMuscles", []) \
            + [s["ref"] for s in it.get("synergists", []) + it.get("antagonists", [])]
        for r in refs:
            if r.startswith(("m-", "b-", "j-", "mv-", "c-")) and r not in known:
                bad_refs.append(f"{it['id']} → {r}")
        if it["chapterId"] not in {c["id"] for c in chapters}:
            bad_refs.append(f"{it['id']} → 없는 챕터 {it['chapterId']}")

    out = ["# 전수조사 보고서 (자동 생성: `python3 tools/audit.py`)", ""]
    tot = Counter(i["category"] for i in items)
    out += [f"- 챕터 {len(chapters)}개 · 항목 {len(items)}개 (근육 {tot['muscle']} · 뼈 {tot['bone']} · 관절 {tot['joint']} · 움직임 {tot['movement']} · 개념 {tot['concept']})",
            f"- 미디어 {len(media)}개 · 파일 없음 {len(missing_files)} · 대체 텍스트 없음 {len(no_alt)} · 출처/라이선스 없음 {len(no_src)}",
            f"- 중복 ID {dup or '없음'} · 잘못된 참조 {len(bad_refs)}건", ""]
    out.append("| # | 챕터 | 항목 | 근육 | 뼈·관절 | 움직임 | 근육 필수정보 누락 | 도판 있는 근육 | 3D 연결 | 상태 | 검증 |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")
    detail = []
    for c in chapters:
        its = [i for i in items if i["chapterId"] == c["id"]]
        mus = [i for i in its if i["category"] == "muscle"]
        bj = [i for i in its if i["category"] in ("bone", "joint")]
        mv = [i for i in its if i["category"] == "movement"]
        lack = [(i["id"], [f for f in REQ_MUSCLE if not i.get(f) and f not in i.get("notApplicable", {})]) for i in mus]
        lack = [x for x in lack if x[1]]
        with_img = [i for i in mus if any(m["type"] in ("plate", "image") for m in by_item[i["id"]])]
        in3d = [i for i in its if i["id"] in mapped or i["id"] in related3d]
        concepts = [i for i in its if i["category"] == "concept"]
        if not its:
            status = "미작성"
        elif c.get("category") == "foundation":
            with_cimg = [i for i in concepts if by_item[i["id"]]]
            status = "완료" if len(concepts) >= 5 else "보완 필요"
            status += f" (개념 {len(concepts)}개 · 도식 있는 개념 {len(with_cimg)})"
        elif mus and (bj or all(i.get("relatedJoints") or i.get("relatedBones") for i in mus)) and mv and not lack and len(with_img) == len(mus):
            status = "완료"
        else:
            status = "보완 필요"
        rev = Counter(i.get("reviewStatus", "needs-review") for i in its)
        out.append(f"| {c['order']} | {c['title']} | {len(its)} | {len(mus)} | {len(bj)} | {len(mv)} | {len(lack)} | {len(with_img)}/{len(mus)} | {len(in3d)} | {status} | "
                   + ", ".join(f"{k} {v}" for k, v in rev.items()) + " |")
        if lack or (mus and len(with_img) < len(mus)):
            detail.append(f"### {c['title']}")
            for iid, fs in lack:
                detail.append(f"- {iid}: 누락 {', '.join(fs)}")
            no_img = [i["id"] for i in mus if i not in with_img]
            if no_img:
                detail.append(f"- 도판 없는 근육: {', '.join(no_img)}")
    out += ["", "## 챕터별 부족 항목", ""] + (detail or ["없음"])
    out += ["", "## 미디어 오류", "", f"- 파일 없음: {missing_files or '없음'}", f"- 대체 텍스트 없음: {no_alt or '없음'}",
            f"- 출처·라이선스 없음: {no_src or '없음'}", "", "## 잘못된 참조", ""] + ([f"- {b}" for b in bad_refs] or ["없음"])
    text = "\n".join(out) + "\n"
    if "--out" in sys.argv:
        open(os.path.join(ROOT, sys.argv[sys.argv.index("--out") + 1]), "w", encoding="utf-8").write(text)
    if "--quiet" not in sys.argv:
        print(text)


if __name__ == "__main__":
    main()
