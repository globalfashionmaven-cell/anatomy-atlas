"""
3D 모델 품질 검사기 — GLB를 직접 읽어 검사하고 docs/3d-model-qa-<id>.md 로 보고서를 씁니다.

검사 항목
  1. 파일: GLB 존재·크기·헤더, 등록부(models3d.json)의 통계와 일치 여부
  2. 매핑: GLB 노드 ↔ 매핑 파일 meshId 양방향 누락, 원본 FJ 파일 존재, FJ ↔ FMA 개념명 일치,
          anatomyItemId 가 data/items.json 에 존재하는지
  3. 형상: 메쉬별 삼각형 수, 퇴화 삼각형, 부호 있는 부피(면이 바깥을 향하는지 = 표면 깨짐 여부)
  4. 비율: 대표 뼈 길이(cm)를 성인 일반 범위와 비교
  5. 부착: 근육 메쉬와 이는곳·닿는곳 뼈 메쉬 사이 최소 거리 (실제로 맞닿아 있는지)

사용법: python3 tools/inspect_model.py [모델 id]
"""
import collections
import json
import math
import os
import struct
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# 성인 대표 길이 범위(cm) — 대략적인 참고치(교과서·인체계측 일반값). 범위 밖이면 '확인 필요'
BONE_RANGES = {"humerus": (28, 38), "clavicle": (12, 17), "scapula": (13, 19)}

# 근육 → 이는곳/닿는곳 뼈 (data/items.json 의 서술에 근거)
ATTACH = {
    "deltoid_anterior": ["clavicle", "humerus"], "deltoid_middle": ["scapula", "humerus"],
    "deltoid_posterior": ["scapula", "humerus"],
    "supraspinatus": ["scapula", "humerus"], "infraspinatus": ["scapula", "humerus"],
    "teres_minor": ["scapula", "humerus"], "subscapularis": ["scapula", "humerus"],
    "teres_major": ["scapula", "humerus"],
    "pecmaj_clavicular": ["clavicle", "humerus"], "pecmaj_sternocostal": ["sternum_body", "humerus"],
    "pecmaj_abdominal": ["humerus"],
    "pectoralis_minor": ["scapula", "rib_3", "rib_4", "rib_5"],
    "serratus_anterior": ["scapula", "rib_2", "rib_5", "rib_8"],
    "trapezius_descending": ["clavicle"], "trapezius_transverse": ["scapula"], "trapezius_ascending": ["scapula"],
    "coracobrachialis": ["scapula", "humerus"], "biceps_short": ["scapula"], "triceps_long": ["scapula"],
    "triceps_lateral": ["humerus"], "triceps_medial": ["humerus"],
    "levator_scapulae": ["scapula"], "rhomboid_major": ["scapula"], "rhomboid_minor": ["scapula"],
}
TOUCH_CM = 0.5  # 0.5cm 이내면 맞닿은 것으로 판단


def read_glb(path):
    data = open(path, "rb").read()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67 and ver == 2 and total == len(data), "GLB 헤더 오류"
    jlen, _ = struct.unpack_from("<II", data, 12)
    gltf = json.loads(data[20:20 + jlen])
    boff = 20 + jlen + 8
    binary = data[boff:]

    def acc(i):
        a = gltf["accessors"][i]
        bv = gltf["bufferViews"][a["bufferView"]]
        start = bv.get("byteOffset", 0)
        n = a["count"]
        if a["type"] == "VEC3":
            return [struct.unpack_from("<3f", binary, start + 12 * k) for k in range(n)]
        fmt, size = ("<I", 4) if a["componentType"] == 5125 else ("<H", 2)
        return [struct.unpack_from(fmt, binary, start + size * k)[0] for k in range(n)]

    meshes = {}
    for node in gltf["nodes"]:
        prim = gltf["meshes"][node["mesh"]]["primitives"][0]
        pos = acc(prim["attributes"]["POSITION"])
        idx = acc(prim["indices"])
        meshes[node["name"]] = (pos, [tuple(idx[i:i + 3]) for i in range(0, len(idx), 3)])
    return gltf, meshes, len(data)


def signed_volume(v, f):
    vol = 0.0
    for a, b, c in f:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = v[a], v[b], v[c]
        vol += ax * (by * cz - bz * cy) - ay * (bx * cz - bz * cx) + az * (bx * cy - by * cx)
    return vol / 6


def degenerate(v, f):
    n = 0
    for a, b, c in f:
        ux, uy, uz = (v[b][i] - v[a][i] for i in range(3))
        wx, wy, wz = (v[c][i] - v[a][i] for i in range(3))
        if math.sqrt((uy * wz - uz * wy) ** 2 + (uz * wx - ux * wz) ** 2 + (ux * wy - uy * wx) ** 2) < 1e-9:
            n += 1
    return n


def extent(v):
    lo = [min(p[i] for p in v) for i in range(3)]
    hi = [max(p[i] for p in v) for i in range(3)]
    return lo, hi


def min_distance(a, b, cell=0.5):
    grid = collections.defaultdict(list)
    for p in b:
        grid[tuple(int(math.floor(p[i] / cell)) for i in range(3))].append(p)
    best = float("inf")
    for p in a:
        k = tuple(int(math.floor(p[i] / cell)) for i in range(3))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for q in grid.get((k[0] + dx, k[1] + dy, k[2] + dz), ()):
                        d = math.dist(p, q)
                        if d < best:
                            best = d
    return best  # 같은/이웃 칸에 없으면 inf (= cell 이상 떨어짐)


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else None
    reg = json.load(open(os.path.join(ROOT, "data", "models3d.json"), encoding="utf-8"))
    items = {i["id"]: i for i in json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))}
    concepts = collections.defaultdict(set)
    isa = os.path.join(ROOT, "sources", "bodyparts3d", "isa_element_parts.txt")
    if os.path.exists(isa):
        for line in open(isa, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) == 3:
                concepts[p[2]].add((p[0], p[1]))

    for model in reg["models"]:
        if want and model["id"] != want:
            continue
        out = [f"# 3D 모델 검사 보고서 — {model['id']}", "", "`python3 tools/inspect_model.py` 로 생성 (GLB를 직접 읽어 검사)", ""]
        mapping = json.load(open(os.path.join(ROOT, model["mapping"]), encoding="utf-8"))["meshes"]
        glb_path = os.path.join(ROOT, model["url"])
        problems = []

        out.append("## 1. 파일")
        if not os.path.exists(glb_path):
            out.append(f"- ❌ GLB 없음: `{model['url']}`")
            print("\n".join(out))
            continue
        gltf, meshes, size = read_glb(glb_path)
        tris = sum(len(f) for _, f in meshes.values())
        out += [f"- GLB: `{model['url']}` — {size:,} bytes ({size / 1e6:.2f} MB), glTF {gltf['asset']['version']}",
                f"- 노드(Mesh) {len(meshes)}개, 삼각형 {tris:,}개",
                f"- 등록부 통계 일치: {'예' if (model.get('fileSize'), model.get('meshCount'), model.get('triangles')) == (size, len(meshes), tris) else '아니오'}",
                f"- 저작권 표기: {gltf['asset'].get('copyright', '(없음)')}", ""]

        out.append("## 2. 매핑")
        names = set(meshes)
        mids = [m["meshId"] for m in mapping]
        dup = [k for k, c in collections.Counter(mids).items() if c > 1]
        no_map = sorted(names - set(mids))
        no_mesh = sorted(set(mids) - names)
        src_dir = os.path.join(ROOT, "sources", "bodyparts3d", "obj")
        no_src = [m["sourceId"] for m in mapping if not os.path.exists(os.path.join(src_dir, m["sourceId"] + ".obj"))]
        fma_bad = [m["meshId"] for m in mapping if concepts and (m["fmaId"], m["sourceName"]) not in concepts[m["sourceId"]]]
        item_bad = [m["meshId"] for m in mapping if m.get("anatomyItemId") and m["anatomyItemId"] not in items]
        linked = [m for m in mapping if m.get("anatomyItemId")]
        out += [f"- 매핑 항목 {len(mapping)}개 / GLB 노드 {len(meshes)}개",
                f"- GLB에 있으나 매핑 없음: {len(no_map)}개 {no_map or ''}",
                f"- 매핑에 있으나 GLB에 없음: {len(no_mesh)}개 {no_mesh or ''}",
                f"- 중복 meshId: {dup or '없음'}",
                f"- 원본 OBJ 누락: {no_src or '없음'} (sources/bodyparts3d/obj)",
                f"- FJ ↔ FMA 개념명 불일치: {fma_bad or '없음'}",
                f"- 존재하지 않는 anatomyItemId: {item_bad or '없음'}",
                f"- 해부학 자료(items.json)와 연결: {len(linked)}개 (같은 구조 {sum(1 for m in linked if m.get('mappingRelation') == 'same')}, 부분 {sum(1 for m in linked if m.get('mappingRelation') == 'part-of')})",
                f"- 연결 자료 없음(이름만 표시): {len(mapping) - len(linked)}개", ""]
        problems += no_map + no_mesh + dup + no_src + fma_bad + item_bad

        out.append("| meshId | 원본 FJ | FMA | 원본 개념명 | 한글 | 레이어 | 연결 항목 | 관계 | 삼각형 | 면 방향 |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        inverted = []
        for m in mapping:
            v, f = meshes.get(m["meshId"], ([], []))
            vol = signed_volume(v, f) if f else 0
            closed = m["layer"] != "skin"
            orient = "바깥(정상)" if vol > 0 else ("열린 메쉬" if not closed else "뒤집힘")
            if closed and vol <= 0:
                inverted.append(m["meshId"])
            out.append(f"| {m['meshId']} | {m['sourceId']} | {m['fmaId']} | {m['sourceName']} | {m['koreanName']} | {m['layer']} | {m.get('anatomyItemId') or '—'} | {m.get('mappingRelation') or '—'} | {len(f):,} | {orient} |")
        out.append("")

        out.append("## 3. 형상")
        degen = {k: degenerate(*meshes[k]) for k in meshes}
        out += [f"- 면이 안쪽으로 뒤집힌 닫힌 메쉬: {inverted or '없음'}",
                f"- 퇴화(넓이 0) 삼각형: {sum(degen.values())}개 {[(k, n) for k, n in degen.items() if n] or ''}"]
        allv = [p for v, _ in meshes.values() for p in v]
        lo, hi = extent(allv)
        out += [f"- 전체 경계 상자(cm): X {lo[0]:.1f}~{hi[0]:.1f}, Y {lo[1]:.1f}~{hi[1]:.1f}, Z {lo[2]:.1f}~{hi[2]:.1f}",
                f"- 중심: ({(lo[0] + hi[0]) / 2:.2f}, {(lo[1] + hi[1]) / 2:.2f}, {(lo[2] + hi[2]) / 2:.2f}) — 원점 근처면 정상", ""]
        problems += inverted

        out.append("## 4. 비율 (대표 뼈 길이)")
        for bone, (a, b) in BONE_RANGES.items():
            if bone in meshes:
                l, h = extent(meshes[bone][0])
                length = max(h[i] - l[i] for i in range(3))
                ok = a <= length <= b
                out.append(f"- {bone}: 최대 길이 {length:.1f} cm (참고 범위 {a}–{b} cm) {'✓' if ok else '⚠ 확인 필요'}")
                if not ok:
                    problems.append(bone)
        # 방향: 위팔뼈는 어깨(위)에서 팔꿈치(아래)로, 대상자의 오른쪽(-X)에 있어야 함
        hl, hh = extent(meshes["humerus"][0]) if "humerus" in meshes else ((0, 0, 0), (0, 0, 0))
        sl, sh = extent(meshes["sternum_body"][0]) if "sternum_body" in meshes else ((0, 0, 0), (0, 0, 0))
        vl, vh = extent(meshes["vertebra_t4"][0]) if "vertebra_t4" in meshes else ((0, 0, 0), (0, 0, 0))
        out += [f"- 방향: 위팔뼈 중심 X {(hl[0] + hh[0]) / 2:.1f} < 복장뼈 중심 X {(sl[0] + sh[0]) / 2:.1f} → 대상자의 오른쪽이 화면 왼쪽(-X) {'✓' if (hl[0] + hh[0]) < (sl[0] + sh[0]) else '⚠'}",
                f"- 방향: 복장뼈 Z {(sl[2] + sh[2]) / 2:.1f} > 등뼈 Z {(vl[2] + vh[2]) / 2:.1f} → 앞쪽이 +Z {'✓' if (sl[2] + sh[2]) > (vl[2] + vh[2]) else '⚠'}", ""]

        out.append(f"## 5. 근육 ↔ 부착 뼈 접촉 (최소 거리, {TOUCH_CM} cm 이내면 맞닿음)")
        out.append("| 근육 메쉬 | 뼈 메쉬 | 최소 거리 | 판정 |")
        out.append("|---|---|---|---|")
        for mus, bones in ATTACH.items():
            if mus not in meshes:
                continue
            for bone in bones:
                if bone not in meshes:
                    continue
                d = min_distance(meshes[mus][0], meshes[bone][0])
                ok = d <= TOUCH_CM
                out.append(f"| {mus} | {bone} | {'> 0.5 cm' if d == float('inf') else f'{d:.2f} cm'} | {'✓ 맞닿음' if ok else '⚠ 떨어짐'} |")
                if not ok:
                    problems.append(f"{mus}-{bone}")
        # 5-2. 부착 '위치' 검사 (어깨세모근): 접촉 정점이 뼈의 어느 위치에 있는지
        def contacts(mus, bone, tol=0.3):
            grid = collections.defaultdict(list)
            for p in meshes[bone][0]:
                grid[tuple(int(math.floor(p[i] / tol)) for i in range(3))].append(p)
            hit = []
            for p in meshes[mus][0]:
                k = tuple(int(math.floor(p[i] / tol)) for i in range(3))
                if any(math.dist(p, q) <= tol for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
                       for q in grid.get((k[0] + dx, k[1] + dy, k[2] + dz), ())):
                    hit.append(p)
            return hit
        if all(k in meshes for k in ("deltoid_anterior", "clavicle", "humerus")):
            out += ["", "### 어깨세모근 부착 위치"]
            cl, ch = extent(meshes["clavicle"][0])  # 빗장뼈: 안쪽(복장끝, +X)→가쪽(봉우리끝, -X)
            hit = contacts("deltoid_anterior", "clavicle")
            if hit:
                frac = sum((ch[0] - p[0]) / (ch[0] - cl[0]) for p in hit) / len(hit)
                ok = frac >= 0.6
                out.append(f"- 앞섬유 ↔ 빗장뼈 접촉 위치: 안쪽 끝에서 평균 {frac * 100:.0f}% 지점 (기대: 가쪽 1/3 = 67% 이상) {'✓' if ok else '⚠ 확인 필요'}")
                if not ok:
                    problems.append("deltoid_anterior-clavicle-position")
            hl, hh = extent(meshes["humerus"][0])
            for part in ("deltoid_anterior", "deltoid_middle", "deltoid_posterior"):
                hit = contacts(part, "humerus")
                if hit:
                    low = max((hh[1] - p[1]) / (hh[1] - hl[1]) for p in hit)  # 가장 아래 접촉 = 닿는곳 끝
                    ok = 0.25 <= low <= 0.6
                    out.append(f"- {part} ↔ 위팔뼈 가장 아래 접촉: 위끝에서 {low * 100:.0f}% 지점 (기대: 세모근거친면, 몸통 중간 위쪽 약 25–60%) {'✓' if ok else '⚠ 확인 필요'}")
                    if not ok:
                        problems.append(f"{part}-humerus-position")
        out += ["", "## 요약", f"- 문제 {len(problems)}건: {problems or '없음'}"]

        os.makedirs(os.path.join(ROOT, "docs"), exist_ok=True)
        path = os.path.join(ROOT, "docs", f"3d-model-qa-{model['id']}.md")
        open(path, "w", encoding="utf-8").write("\n".join(out) + "\n")
        print(f"{model['id']}: problems={len(problems)} {problems} → {os.path.relpath(path, ROOT)}")


if __name__ == "__main__":
    main()
