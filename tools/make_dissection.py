"""
층별 해부 데이터 생성 (V5 LAYER-001/002) — 3D 모델의 실제 형상에서 '가림 관계'를 계산

  python3 tools/make_dissection.py [모델ID=back]   → data/dissection/<모델ID>.json

1) 가림 그래프 (관찰 방향별)
   메쉬마다 따로 래스터화해 픽셀별 깊이 지도를 만들고, 두 메쉬가 같은 픽셀을 덮을 때
   관찰자 쪽(앞)에 있는 메쉬가 뒤의 메쉬를 '가린다'고 기록합니다.
   - 근육 전체를 한 깊이로 보지 않습니다: 쌍마다 겹치는 픽셀 수·가려지는 비율·겹침 영역(3D 중심점, 화면 범위)을 저장
2) 해부 단계
   남은 근육 중 '다른 근육에 가려지지 않으면서 무언가를 가리고 있는' 근육을 한 단계로 걷어냄 → 반복
   (서로 일부씩 가리는 근육은 순가림량이 큰 쪽을 먼저)
3) 자동 탐색 경로
   목표 근육(또는 메쉬가 없을 때 위치 대리 영역)의 각 픽셀에서 관찰자 쪽에 있는 근육만 모아 단계 순서로 정렬
4) 젖히기(reflection) 정의
   해부 관례에 따라 근육마다 '붙어 남는 쪽'(경첩)을 정하고, 경첩 근처 정점을 PCA로 맞춘 축을 저장.
   화면에서는 정점별로 경첩에서 멀수록 더 크게 회전시켜 근육이 책장처럼 젖혀집니다 (교육용 가상 해부).

좌표: 모델 좌표(cm, Y 위, +Z 앞, +X 대상자의 왼쪽). 오른쪽 몸 근육은 -X 쪽.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plate_renderer as R  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
SIZE = (300, 420)
MIN_PX = 12          # 이보다 적게 겹치면 가림으로 보지 않음 (가장자리 잡음)
EPS = 0.08           # cm, 같은 깊이 판단 여유

# 젖히는 방식 (해부 관례): 경첩 방향(남는 쪽) · 최대 각도 · 설명
LAT, SUP, INFLAT, SUPLAT = (-1, 0, 0), (0, 1, 0), (-0.7, -0.7, 0), (-0.55, 0.83, 0)
REFLECT = {
    "trapezius_descending": (LAT, 150, "척추·뒤통수 쪽 기시를 떼어 가쪽(빗장뼈·견봉 쪽)으로 젖힘"),
    "trapezius_transverse": (LAT, 150, "가시돌기 기시를 떼어 가쪽(견봉·견갑극 쪽)으로 젖힘"),
    "trapezius_ascending": (LAT, 150, "가시돌기 기시를 떼어 가쪽(견갑극 쪽)으로 젖힘"),
    "deltoid_posterior": (INFLAT, 120, "견갑극 기시를 떼어 아래가쪽(상완골 쪽)으로 젖힘"),
    "rhomboid_minor": (LAT, 140, "가시돌기 기시를 떼어 가쪽(견갑골 안쪽모서리 쪽)으로 젖힘"),
    "rhomboid_major": (LAT, 140, "가시돌기 기시를 떼어 가쪽(견갑골 안쪽모서리 쪽)으로 젖힘"),
    "levator_scapulae": (SUP, 110, "견갑골 정지를 떼어 위쪽(목뼈 가로돌기 쪽)으로 젖힘"),
    "serratus_posterior_superior": (LAT, 140, "가시돌기 기시를 떼어 가쪽(갈비뼈 쪽)으로 젖힘"),
    "serratus_posterior_inferior": (LAT, 140, "가시돌기 기시를 떼어 가쪽(갈비뼈 쪽)으로 젖힘"),
    "splenius": (SUPLAT, 120, "가시돌기 기시를 떼어 위가쪽(꼭지돌기 쪽)으로 젖힘"),
    "infraspinatus": (LAT, 110, "가시아래오목 기시를 떼어 가쪽(상완골 쪽)으로 젖힘"),
    "teres_minor": (LAT, 110, "견갑골 기시를 떼어 가쪽으로 젖힘"),
    "teres_major": (LAT, 110, "견갑골 아래각 기시를 떼어 가쪽으로 젖힘"),
    "supraspinatus": (LAT, 100, "가시위오목 기시를 떼어 가쪽으로 젖힘"),
    "iliocostalis": (LAT, 75, "가쪽으로 당겨 젖힘 (척추세움근 바깥 기둥)"),
    "longissimus": (LAT, 75, "가쪽으로 당겨 젖힘 (척추세움근 중간 기둥)"),
    "spinalis": (LAT, 75, "가쪽으로 당겨 젖힘 (척추세움근 안쪽 기둥)"),
    "semispinalis": (LAT, 70, "가쪽으로 당겨 젖힘"),
}
# 메쉬가 없는 근육의 '위치 대리 영역' (그 근육이 놓인 뼈 표면) — 근육을 대신 그리지 않음
PROXY = {
    "m-multifidus": {
        "bones": [f"vertebra_t{i}" for i in range(4, 13)] + [f"vertebra_l{i}" for i in range(1, 6)] + ["sacrum"],
        "exclude": ["interspinales", "intertransversarii"],
        "note": "다열근(뭇갈래근)은 사용 중인 3D 모델(BodyParts3D 4.0)에 형상이 없습니다. 대신 다열근이 채우는 자리 — 가시돌기와 가로돌기 사이의 척추 홈(T4–엉치뼈) — 를 가리는 구조만 걷어내 그 위치를 보여 줍니다. 가시사이근·가로돌기사이근은 다열근과 같거나 더 깊은 층이라 경로에서 제외합니다.",
    },
    "m-latissimus-dorsi": {
        "bones": ["ribs_r"] + [f"vertebra_t{i}" for i in range(7, 13)] + [f"vertebra_l{i}" for i in range(1, 6)],
        "exclude": "deep-only",
        "note": "넓은등근(광배근)은 3D 모델에 형상이 없어 표시할 수 없습니다. 실제로는 아래 등의 가장 얕은 층(승모근 하부 아래쪽)에 있습니다.",
    },
}
VIEWS = {"back": ((0, 0, -1), (0, 1, 0), "뒤에서")}


def mean(ps):
    n = len(ps)
    return [sum(p[i] for p in ps) / n for i in range(3)]


def pca_axis(ps):
    c = mean(ps)
    xx = [[0.0] * 3 for _ in range(3)]
    for p in ps:
        d = [p[i] - c[i] for i in range(3)]
        for i in range(3):
            for j in range(3):
                xx[i][j] += d[i] * d[j]
    v = [1.0, 0.3, 0.2]
    for _ in range(50):  # 거듭제곱법
        w = [sum(xx[i][j] * v[j] for j in range(3)) for i in range(3)]
        n = math.sqrt(sum(x * x for x in w)) or 1
        v = [x / n for x in w]
    return c, v


def rot(p, axis, ang):
    """원점 기준 축 회전 (Rodrigues)"""
    k = axis
    c, s = math.cos(ang), math.sin(ang)
    dot = sum(p[i] * k[i] for i in range(3))
    cr = [k[1] * p[2] - k[2] * p[1], k[2] * p[0] - k[0] * p[2], k[0] * p[1] - k[1] * p[0]]
    return [p[i] * c + cr[i] * s + k[i] * dot * (1 - c) for i in range(3)]


def hinge_of(verts, hdir, max_deg, toward=(0, 0, -1)):
    """경첩 = 근육의 hdir 쪽 가장자리. 회전축 = hdir × (관찰자 쪽 방향) → 책장을 넘기듯 관찰자 쪽으로 들리며 경첩 너머로 넘어감.
    (경첩 정점을 PCA로 맞추면 힘줄이 모이는 근육에서 축이 불안정해 쓰지 않음)"""
    h = R.norm(hdir)
    proj = [sum(v[i] * h[i] for i in range(3)) for v in verts]
    hi, lo = max(proj), min(proj)
    span = hi - lo
    edge = [v for v, q in zip(verts, proj) if q >= hi - 0.12 * span]
    c = mean(edge)
    ax = R.norm(R.cross(h, R.norm(toward)))
    far = mean([v for v, q in zip(verts, proj) if q <= lo + 0.2 * span])
    rel = [far[i] - c[i] for i in range(3)]
    t = R.norm(toward)
    moved = rot(rel, ax, 0.3)
    sign = 1 if sum((moved[i] - rel[i]) * t[i] for i in range(3)) > 0 else -1
    return {"point": [round(x, 3) for x in c], "axis": [round(x, 4) for x in ax], "dir": [round(x, 4) for x in h],
            "hi": round(hi, 3), "span": round(span, 3), "angle": max_deg, "sign": sign}


def main():
    mid = sys.argv[1] if len(sys.argv) > 1 else "back"
    reg = json.load(open(os.path.join(ROOT, "data", "models3d.json"), encoding="utf-8"))
    model = next(m for m in reg["models"] if m["id"] == mid)
    meshes = R.read_glb(os.path.join(ROOT, model["url"]))
    mapping = json.load(open(os.path.join(ROOT, model["mapping"]), encoding="utf-8"))["meshes"]
    entry = {e["meshId"]: e for e in mapping}
    muscles = [e["meshId"] for e in mapping if e["category"] == "muscle" and e["meshId"] in meshes]
    bones = [e["meshId"] for e in mapping if e["category"] in ("bone", "cartilage") and e["meshId"] in meshes]
    allpts = [p for n in meshes for p in meshes[n]["v"][::7]]
    out = {"modelId": mid, "generator": "tools/make_dissection.py", "reviewStatus": "needs-review",
           "note": "교육용 가상 해부 연출입니다. 근육을 실제로 자르거나 생리적으로 움직이는 것이 아니라, 겹침 관계를 이해하도록 근육을 책장처럼 젖혀 아래 구조를 보여 줍니다. 단계와 가림 관계는 3D 모델 형상에서 계산한 값이며 전문가 검토가 필요합니다.",
           "missingMeshes": [{"itemId": k, "note": v["note"]} for k, v in PROXY.items()],
           "views": {}, "reflect": {}}
    for vkey, (d, up, vko) in VIEWS.items():
        v = R.View(d, up)
        zmap = {}
        cx = cy = scale = None
        for n in muscles + bones:
            cv, ids, screen, sc = R.render(meshes, [(n, "#888888")], v, SIZE, (0, 0, SIZE[0], SIZE[1]), ss=1, fit_points=allpts)
            cx, cy = screen((0, 0, 0))
            scale = sc
            zmap[n] = {k: z for k, z in enumerate(cv.z) if cv.id[k]}

        def unproject(k, z):
            x, y = k % SIZE[0] + 0.5, k // SIZE[0] + 0.5
            q0, q1 = (x - cx) / scale, (cy - y) / scale
            return [q0 * v.r[i] + q1 * v.u[i] + z * v.d[i] for i in range(3)]

        # 가림 그래프
        cover = {}
        for a in muscles:
            za = zmap[a]
            for b in muscles + bones:
                if a == b:
                    continue
                zb = zmap[b]
                ks = [k for k in za.keys() & zb.keys() if za[k] > zb[k] + EPS]
                if len(ks) < MIN_PX:
                    continue
                xs = [k % SIZE[0] for k in ks]
                ys = [k // SIZE[0] for k in ks]
                c3 = mean([unproject(k, zb[k]) for k in ks[::3]])
                cover.setdefault(a, {})[b] = {"px": len(ks), "frac": round(len(ks) / max(1, len(zb)), 3),
                                              "center": [round(x, 2) for x in c3],
                                              "box": [round(min(xs) / SIZE[0], 3), round(min(ys) / SIZE[1], 3), round(max(xs) / SIZE[0], 3), round(max(ys) / SIZE[1], 3)]}
        # 단계 계산
        remaining = set(muscles)
        steps = []

        def covered_px(m, pool):
            return sum(cover.get(a, {}).get(m, {}).get("px", 0) for a in pool if a != m)

        def covers_px(m, pool):
            return sum(x["px"] for b, x in cover.get(m, {}).items() if b in pool)

        while True:
            blockers = [m for m in remaining if covers_px(m, remaining) >= MIN_PX]
            if not blockers:
                break
            free = [m for m in blockers if covered_px(m, remaining) < max(MIN_PX, 0.03 * len(zmap[m]))]
            if not free:  # 서로 일부씩 가리는 경우: 순가림량이 가장 큰 근육
                free = [max(blockers, key=lambda m: covers_px(m, remaining) - covered_px(m, remaining))]
            steps.append(sorted(free, key=lambda m: -len(zmap[m])))
            remaining -= set(free)
        rank = {m: i + 1 for i, s in enumerate(steps) for m in s}
        for m in remaining:
            rank[m] = len(steps) + 1

        def exposes(step_meshes, before):
            """이 단계로 새로 드러나는 구조: 걷어낸 근육이 가리던 것 중 이제 남은 근육에게 가려지지 않는 것"""
            pool = before - set(step_meshes)
            got = set()
            for m in step_meshes:
                for b in cover.get(m, {}):
                    if b in step_meshes:
                        continue
                    if b in bones or b in pool:
                        if covered_px(b, pool) < 0.5 * len(zmap[b]):
                            got.add(b)
            return sorted(got)

        steps_out, pool = [], set(muscles)
        for i, s in enumerate(steps):
            steps_out.append({"n": i + 1, "remove": s, "exposes": exposes(s, pool),
                              "title": " · ".join(dict.fromkeys(entry[m]["koreanName"] for m in s))})
            pool -= set(s)

        # 자동 탐색 경로 (항목별)
        def path_to(target_meshes, exclude=()):
            need = set()
            for t in target_meshes:
                for k, zt in zmap[t].items():
                    for a in muscles:
                        if a in target_meshes or a in exclude:
                            continue
                        za = zmap[a].get(k)
                        if za is not None and za > zt + EPS:
                            need.add(a)
            # 겹친 픽셀이 너무 적은 근육은 제외
            need = {a for a in need if sum(1 for t in target_meshes for k in zmap[t] if k in zmap[a] and zmap[a][k] > zmap[t][k] + EPS) >= MIN_PX}
            return sorted(need, key=lambda m: (rank.get(m, 99), -len(zmap[m])))

        def path_steps(p):
            st = [[m for m in s_ if m in p] for s_ in steps if any(m in p for m in s_)]
            rest = [m for m in p if not any(m in s_ for s_ in st)]  # 전체 단계에 없는 가장 깊은 층
            return st + ([rest] if rest else [])

        paths = {}
        items = {}
        for e in mapping:
            if e.get("anatomyItemId") and e["meshId"] in muscles:
                items.setdefault(e["anatomyItemId"], []).append(e["meshId"])
        for iid, ms in items.items():
            p = path_to(ms)
            paths[iid] = {"target": ms, "path": p, "proxy": False,
                          "steps": path_steps(p)}
        for iid, pr in PROXY.items():
            tb = [b for b in pr["bones"] if b in zmap]
            excl = pr["exclude"] if isinstance(pr["exclude"], list) else []
            p = path_to(tb, excl)
            if pr["exclude"] == "deep-only":
                p = []  # 표층 근육: 해부 경로 없이 위치만 안내
            paths[iid] = {"target": [], "proxyBones": tb, "path": p, "proxy": True, "note": pr["note"], "steps": path_steps(p)}
        out["views"][vkey] = {"dir": d, "up": up, "label": vko, "size": SIZE, "steps": steps_out,
                              "rank": rank, "deepest": sorted(remaining), "cover": cover, "autoPaths": paths}
        print(vkey, "steps:")
        for s in steps_out:
            print(" ", s["n"], s["title"], "→ 드러남:", ", ".join(entry[b]["koreanName"] for b in s["exposes"][:8]))
        print("  남음:", ", ".join(entry[m]["koreanName"] for m in remaining))
        for iid in ("m-multifidus", "m-erector-spinae", "m-rhomboids", "m-supraspinatus", "m-levator-scapulae"):
            if iid in paths:
                print("  경로", iid, [entry[m]["koreanName"] for m in paths[iid]["path"]])

    for m in muscles:
        if m in REFLECT:
            hd, ang, why = REFLECT[m]
            out["reflect"][m] = {**hinge_of(meshes[m]["v"], hd, ang), "how": why}
    os.makedirs(os.path.join(ROOT, "data", "dissection"), exist_ok=True)
    json.dump(out, open(os.path.join(ROOT, "data", "dissection", f"{mid}.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("→ data/dissection/%s.json" % mid, os.path.getsize(os.path.join(ROOT, "data", "dissection", f"{mid}.json")) // 1024, "KB")


if __name__ == "__main__":
    main()
