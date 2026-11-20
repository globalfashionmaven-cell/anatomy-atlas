"""
근섬유 방향·기시/정지 위치 데이터 (V5 MUSCLE-001/002) — 3D 모델 형상과 본문 기시·정지에서 계산

  python3 tools/make_fibers.py [모델ID ...]   (기본: shoulder-right back)  → data/fibers/<모델ID>.json

메쉬마다:
  origin / insertion : 근육 메쉬가 뼈에 맞닿은 정점 중, 본문 기시·정지 텍스트에 이름이 나오는 뼈의 접촉점 → 기시·정지 영역 중심
                       (make_region_plates.py 와 같은 대응 규칙)
  glyphs             : 근육 표면에서 고르게 뽑은 점마다의 '근섬유 방향' 단위벡터 (표면 접선)
                       방향 = (점 - 가장 가까운 기시점) 과 (가장 가까운 정지점 - 점) 의 평균을 표면에 투영
                       → 부채꼴 근육(삼각근)은 정지로 모이고, 넓은 판상근(승모근)은 부위별로 다른 방향이 나옴
  force              : 정지 중심 → 기시 중심 (수축 시 정지에 작용하는 당김 방향의 근사)
한계: 근섬유 배열을 해부·영상으로 측정한 값이 아니라, 부착부 위치에서 추정한 교육용 근사입니다 (검토 필요).
       힘줄이 메쉬에 없으면 그쪽 부착점이 비어 있을 수 있음 → 그때는 메쉬 주축 방향을 씀 (method 로 표시).
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plate_renderer as R  # noqa: E402
from make_deltoid_plates import contact_vertices  # noqa: E402
from make_region_plates import BONE_RX, bone_key  # noqa: E402
from make_dissection import pca_axis  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BONE_RX = dict(BONE_RX)
BONE_RX["occipital"] = r"뒤통수뼈|위목덜미선|목덜미인대"


def key_of(mesh_id, entry):
    if mesh_id == "occipital":
        return "occipital"
    return bone_key(mesh_id, entry)


def unit(v):
    n = math.sqrt(sum(x * x for x in v)) or 1
    return [x / n for x in v]


def nearest(p, pts):
    return min(pts, key=lambda q: (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 + (q[2] - p[2]) ** 2)


def farthest_sample(pts, k):
    if len(pts) <= k:
        return list(range(len(pts)))
    chosen = [0]
    d = [math.dist(pts[0], p) for p in pts]
    for _ in range(k - 1):
        i = max(range(len(pts)), key=lambda j: d[j])
        chosen.append(i)
        for j, p in enumerate(pts):
            dd = math.dist(pts[i], p)
            if dd < d[j]:
                d[j] = dd
    return chosen


def main():
    ids = sys.argv[1:] or ["shoulder-right", "back"]
    reg = json.load(open(os.path.join(ROOT, "data", "models3d.json"), encoding="utf-8"))
    items = {i["id"]: i for i in json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))}
    for mid in ids:
        model = next(m for m in reg["models"] if m["id"] == mid)
        meshes = R.read_glb(os.path.join(ROOT, model["url"]))
        mapping = json.load(open(os.path.join(ROOT, model["mapping"]), encoding="utf-8"))["meshes"]
        entry = {e["meshId"]: e for e in mapping}
        bones = [e["meshId"] for e in mapping if e["category"] == "bone" and e["meshId"] in meshes]
        boxes = {b: (tuple(map(min, zip(*meshes[b]["v"]))), tuple(map(max, zip(*meshes[b]["v"])))) for b in bones}
        out = {"modelId": mid, "generator": "tools/make_fibers.py", "reviewStatus": "needs-review",
               "note": "근섬유 방향은 모델의 부착부(기시·정지 접촉면) 위치에서 추정한 교육용 근사입니다. 실제 근섬유 측정값이 아닙니다.",
               "muscles": {}}
        for e in mapping:
            m = e["meshId"]
            it = items.get(e.get("anatomyItemId") or "")
            if e["category"] != "muscle" or m not in meshes or not it or it["category"] != "muscle":
                continue
            vs = meshes[m]["v"]
            lo = tuple(map(min, zip(*vs)))
            hi = tuple(map(max, zip(*vs)))
            o_txt, i_txt = " ".join(it.get("origin") or []), " ".join(it.get("insertion") or [])
            O, I = [], []
            I_bones = set()
            for b in bones:
                bl, bh = boxes[b]
                if not all(bl[k] - 1 <= hi[k] and bh[k] + 1 >= lo[k] for k in range(3)):
                    continue
                key = key_of(b, entry[b])
                if not key or key not in BONE_RX:
                    continue
                rx = re.compile(BONE_RX[key])
                isO, isI = bool(rx.search(o_txt)), bool(rx.search(i_txt))
                if not (isO or isI):
                    continue
                hit = None
                for tol in (0.35, 0.8):
                    hit = contact_vertices(meshes[b]["v"], vs, tol)
                    if len(hit) >= 4:
                        break
                if not hit or len(hit) < 4:
                    continue
                pts = [meshes[b]["v"][i] for i in hit]
                if isO and isI:  # 같은 뼈에 기시·정지가 모두 있으면(예: 견갑골) 메쉬 주축의 양 끝으로 나눔
                    c, ax = pca_axis(vs[::5])
                    proj = [sum((p[k] - c[k]) * ax[k] for k in range(3)) for p in pts]
                    med = sorted(proj)[len(proj) // 2]
                    O += [p for p, q in zip(pts, proj) if q < med]
                    I += [p for p, q in zip(pts, proj) if q >= med]
                elif isO:
                    O += pts
                else:
                    I += pts
                    I_bones.add(key)
            # 긴뼈에 '얹혀' 닿은 면(예: 삼각근이 위팔뼈머리를 덮는 면)은 정지가 아님 → 기시에서 가장 먼 25%만 정지로
            if O and I and len(I) > 8 and any(k in (I_bones or ()) for k in ("b-humerus", "b-femur", "b-tibia", "b-radius", "b-ulna", "b-fibula")):
                oc = [sum(q[k] for q in O) / len(O) for k in range(3)]
                ds = sorted(math.dist(p, oc) for p in I)
                cut = ds[int(len(ds) * 0.75)]
                I = [p for p in I if math.dist(p, oc) >= cut]
            c, ax = pca_axis(vs[::5])
            method = "attachments" if O and I else "axis"
            nrm = meshes[m]["n"]
            idx = farthest_sample(vs[::3], 36)
            glyphs = []
            for j in idx:
                vi = j * 3
                p, n = vs[vi], unit(nrm[vi])
                if method == "attachments":
                    o, i = nearest(p, O), nearest(p, I)
                    if math.dist(p, o) < 0.6 or math.dist(p, i) < 0.6:
                        continue
                    d = [a + b for a, b in zip(unit([p[k] - o[k] for k in range(3)]), unit([i[k] - p[k] for k in range(3)]))]
                else:
                    d = ax[:]
                    if O:  # 기시 쪽에서 멀어지는 방향으로
                        oc = [sum(q[k] for q in O) / len(O) for k in range(3)]
                        if sum((p[k] - oc[k]) * d[k] for k in range(3)) < 0:
                            d = [-x for x in d]
                dn = sum(d[k] * n[k] for k in range(3))
                d = unit([d[k] - dn * n[k] for k in range(3)])
                glyphs.append([round(x, 2) for x in p] + [round(x, 3) for x in d] + [round(x, 3) for x in n])
            cen = lambda P: [round(sum(q[k] for q in P) / len(P), 2) for k in range(3)] if P else None  # noqa: E731
            out["muscles"][m] = {"item": it["id"], "method": method, "origin": cen(O), "insertion": cen(I),
                                 "originPts": [[round(x, 2) for x in O[j]] for j in farthest_sample(O, 12)] if O else [],
                                 "insertionPts": [[round(x, 2) for x in I[j]] for j in farthest_sample(I, 12)] if I else [],
                                 "glyphs": glyphs}
            print(mid, m, method, "O", len(O), "I", len(I), "glyphs", len(glyphs))
        os.makedirs(os.path.join(ROOT, "data", "fibers"), exist_ok=True)
        json.dump(out, open(os.path.join(ROOT, "data", "fibers", f"{mid}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
