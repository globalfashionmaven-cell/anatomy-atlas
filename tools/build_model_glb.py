"""
BodyParts3D OBJ → 웹용 GLB 변환기 (외부 의존성 없음, Python 3 표준 라이브러리만 사용)

data/models3d.json 에 등록된 각 모델의 매핑 파일(data/mappings/<id>.json)을 읽어,
meshes[].sourceId (BodyParts3D element file id, FJxxxx) OBJ 를
meshes[].meshId 이름을 가진 개별 노드(Mesh)로 하나의 GLB에 담습니다.
변환 후 파일 크기·메쉬 수·삼각형 수를 data/models3d.json 에 기록합니다.
→ 뷰어에서 근육·뼈를 하나씩 선택·숨김·강조할 수 있습니다.

사용법:
  python3 tools/build_model_glb.py [OBJ 폴더 경로] [모델 id]
  (OBJ 폴더 기본값: sources/bodyparts3d/obj — 이 프로젝트에 사용한 원본 OBJ 사본)

OBJ 폴더: 공식 배포 파일 isa_BP3D_4.0_obj_99.zip 의 압축을 푼 폴더
  (https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html, CC BY 4.0)

변환 내용 (models3d.json의 source.modified에도 기록):
  - BodyParts3D 좌표(mm, Z-up)를 Three.js 관례(Y-up, 앞쪽 +Z)로 회전, cm 단위로 축소
  - 모델 전체의 중심을 원점으로 이동
  - 정점 법선을 면적 가중 평균으로 재계산
  - 피부(skin)는 전신 메쉬이므로 다른 구조들의 경계 상자(+여유) 안의 삼각형만 남김
"""
import json
import math
import os
import struct
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SCALE = 0.1  # mm → cm


def find_obj(folder, fj):
    direct = os.path.join(folder, f"{fj}.obj")
    if os.path.exists(direct):
        return direct
    for dirpath, _, files in os.walk(folder):
        for f in files:
            if f.lower() == f"{fj.lower()}.obj":
                return os.path.join(dirpath, f)
    return None


def read_obj(path):
    verts, faces = [], []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("v "):
                _, x, y, z = line.split()[:4]
                verts.append((float(x), float(y), float(z)))
            elif line.startswith("f "):
                idx = [int(p.split("/")[0]) for p in line.split()[1:]]
                idx = [i - 1 if i > 0 else len(verts) + i for i in idx]
                for k in range(1, len(idx) - 1):  # 다각형 → 삼각형 팬
                    faces.append((idx[0], idx[k], idx[k + 1]))
    return verts, faces


def bbox(verts):
    xs, ys, zs = zip(*verts)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def compact(verts, faces):
    used = sorted({i for f in faces for i in f})
    remap = {old: new for new, old in enumerate(used)}
    return [verts[i] for i in used], [tuple(remap[i] for i in f) for f in faces]


def normals(verts, faces):
    acc = [[0.0, 0.0, 0.0] for _ in verts]
    for a, b, c in faces:
        ax, ay, az = verts[a]
        bx, by, bz = verts[b]
        cx, cy, cz = verts[c]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        for i in (a, b, c):
            acc[i][0] += nx
            acc[i][1] += ny
            acc[i][2] += nz
    out = []
    for nx, ny, nz in acc:
        l = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        out.append((nx / l, ny / l, nz / l))
    return out


# BodyParts3D 좌표계(coordinate_system.png): X+ = 대상자의 왼쪽, Y- = 앞쪽, Z+ = 위쪽 (mm)
# Three.js 관례(Y-up, +Z = 관찰자 쪽 = 대상자의 앞)로 회전: (x, y, z) → (x, z, -y)  [행렬식 +1 → 면 방향 보존]
def bp3d_to_three(p):
    return (p[0], p[2], -p[1])


def detect_axes(meshes):
    """어깨 모델로 좌표계를 검증할 때 사용: 위(머리)·앞·오른쪽 축의 부호를 데이터에서 확인."""
    def center(name):
        v = meshes[name][0]
        lo, hi = bbox(v)
        return [(lo[i] + hi[i]) / 2 for i in range(3)]

    rib1, rib8 = center("rib_1"), center("rib_8")
    sternum, vert = center("sternum_body"), center("vertebra_t4")
    humerus = center("humerus")
    up = max(range(3), key=lambda i: abs(rib1[i] - rib8[i]))
    up_sign = 1 if rib1[up] > rib8[up] else -1
    fwd = max((i for i in range(3) if i != up), key=lambda i: abs(sternum[i] - vert[i]))
    fwd_sign = 1 if sternum[fwd] > vert[fwd] else -1
    lat = ({0, 1, 2} - {up, fwd}).pop()
    # 오른쪽 위팔뼈는 정중선(복장뼈)보다 대상자의 오른쪽 → 화면 정면에서 보는 사람의 왼쪽(-X)
    right_sign = 1 if humerus[lat] > sternum[lat] else -1
    print(f"axes: up={'xyz'[up]}{'+' if up_sign > 0 else '-'} forward={'xyz'[fwd]}{'+' if fwd_sign > 0 else '-'} subject-right={'xyz'[lat]}{'+' if right_sign > 0 else '-'}")

    def tf(p):
        # Three.js: +Y 위, +Z 앞(관찰자 쪽), +X 대상자의 왼쪽
        return (-right_sign * p[lat], up_sign * p[up], fwd_sign * p[fwd])

    return tf


def decimate(verts, faces, target):
    """정점 군집화(vertex clustering) 단순화: 격자 칸마다 정점을 평균 하나로 합쳐 삼각형 수를 target 이하로"""
    lo, hi = bbox(verts)
    diag = math.dist(lo, hi) or 1.0
    cell = diag / 400
    while True:
        cid, sums = {}, []
        remap = []
        for p in verts:
            k = (int(p[0] // cell), int(p[1] // cell), int(p[2] // cell))
            if k not in cid:
                cid[k] = len(sums)
                sums.append([0.0, 0.0, 0.0, 0])
            j = cid[k]
            sums[j][0] += p[0]; sums[j][1] += p[1]; sums[j][2] += p[2]; sums[j][3] += 1
            remap.append(j)
        seen, nf = set(), []
        for a, b, c in faces:
            a, b, c = remap[a], remap[b], remap[c]
            if a == b or b == c or a == c:
                continue
            key = tuple(sorted((a, b, c)))
            if key in seen:
                continue
            seen.add(key)
            nf.append((a, b, c))
        if len(nf) <= target or cell > diag / 20:
            nv = [(x / n, y / n, z / n) for x, y, z, n in sums]
            return nv, nf
        cell *= 1.35


def pad4(b, fill=b"\x00"):
    return b + fill * ((4 - len(b) % 4) % 4)


def write_glb(path, nodes_data):
    bin_chunks, buffer_views, accessors, meshes, nodes = [], [], [], [], []
    offset = 0

    def add_view(data, target):
        nonlocal offset
        data = pad4(data)
        buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), "target": target})
        bin_chunks.append(data)
        offset += len(data)
        return len(buffer_views) - 1

    for name, verts, norms, faces in nodes_data:
        pos = b"".join(struct.pack("<3f", *v) for v in verts)
        nor = b"".join(struct.pack("<3f", *n) for n in norms)
        big = len(verts) > 65535
        idx = b"".join(struct.pack("<3I" if big else "<3H", *f) for f in faces)
        lo, hi = bbox(verts)
        vp = add_view(pos, 34962)
        vn = add_view(nor, 34962)
        vi = add_view(idx, 34963)
        accessors.append({"bufferView": vp, "componentType": 5126, "count": len(verts), "type": "VEC3", "min": list(lo), "max": list(hi)})
        accessors.append({"bufferView": vn, "componentType": 5126, "count": len(verts), "type": "VEC3"})
        accessors.append({"bufferView": vi, "componentType": 5125 if big else 5123, "count": len(faces) * 3, "type": "SCALAR"})
        a = len(accessors)
        meshes.append({"name": name, "primitives": [{"attributes": {"POSITION": a - 3, "NORMAL": a - 2}, "indices": a - 1, "material": 0}]})
        nodes.append({"name": name, "mesh": len(meshes) - 1})

    gltf = {
        "asset": {"version": "2.0", "generator": "anatomy-atlas build_model_glb.py",
                  "copyright": "BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International (source OBJ headers: CC Attribution-Share Alike 2.1 Japan). Derived GLB: CC BY-SA 4.0"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": [{"name": "default", "pbrMetallicRoughness": {"baseColorFactor": [0.8, 0.8, 0.8, 1], "metallicFactor": 0, "roughnessFactor": 0.8}}],
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": offset}],
    }
    js = pad4(json.dumps(gltf, separators=(",", ":")).encode(), b" ")
    binary = b"".join(bin_chunks)
    total = 12 + 8 + len(js) + 8 + len(binary)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(binary), 0x004E4942) + binary)
    return total


def build(obj_folder, model):
    raw = {}
    for s in model["meshes"]:
        # sourceId 가 목록이면 여러 OBJ 를 하나의 메쉬로 합침 (예: 손가락뼈 14개)
        verts, faces = [], []
        for fj in (s["sourceId"] if isinstance(s["sourceId"], list) else [s["sourceId"]]):
            p = find_obj(obj_folder, fj)
            if not p:
                raise SystemExit(f"OBJ 없음: {fj} ({s['meshId']})")
            v, f = read_obj(p)
            off = len(verts)
            verts += v
            faces += [(a + off, b + off, c + off) for a, b, c in f]
        raw[s["meshId"]] = (verts, faces)

    tf = bp3d_to_three
    if all(k in raw for k in ("rib_1", "rib_8", "sternum_body", "vertebra_t4", "humerus")):
        probe = detect_axes(raw)
        sample = raw["humerus"][0][0]
        assert probe(sample) == tf(sample), "BodyParts3D 좌표계가 예상과 다릅니다"
    meshes = {k: ([tf(p) for p in v], f) for k, (v, f) in raw.items()}

    # 피부 잘라내기: 다른 구조 전체의 경계 상자 + 여유 3cm(=30mm)
    if "skin" in meshes:
        others = [p for k, (v, _) in meshes.items() if k != "skin" for p in v]
        lo, hi = bbox(others)
        m = 30.0
        lo = [lo[i] - m for i in range(3)]
        hi = [hi[i] + m for i in range(3)]
        v, f = meshes["skin"]
        inside = [all(lo[i] <= p[i] <= hi[i] for i in range(3)) for p in v]
        keep = [t for t in f if inside[t[0]] and inside[t[1]] and inside[t[2]]]
        meshes["skin"] = compact(v, keep)

    allv = [p for v, _ in meshes.values() for p in v]
    lo, hi = bbox(allv)
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]

    nodes, tris = [], 0
    cap = model.get("maxTrianglesPerMesh")
    for s in model["meshes"]:
        v, f = meshes[s["meshId"]]
        if cap and len(f) > cap:
            before = len(f)
            v, f = decimate(v, f, cap)
            print(f"  단순화 {s['meshId']}: {before:,} → {len(f):,} 삼각형")
        v = [tuple((p[i] - c[i]) * SCALE for i in range(3)) for p in v]
        nodes.append((s["meshId"], v, normals(v, f), f))
        tris += len(f)
    out = os.path.join(ROOT, model["url"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    size = write_glb(out, nodes)
    print(f"{model['id']}: {len(nodes)} meshes, {tris:,} triangles, {size / 1e6:.2f} MB → {model['url']}")
    return {"fileSize": size, "meshCount": len(nodes), "triangles": tris}


if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "sources", "bodyparts3d", "obj")
    want = sys.argv[2] if len(sys.argv) > 2 else None
    reg_path = os.path.join(ROOT, "data", "models3d.json")
    cfg = json.load(open(reg_path, encoding="utf-8"))
    for model in cfg["models"]:
        if want and model["id"] != want:
            continue
        mapping = json.load(open(os.path.join(ROOT, model["mapping"]), encoding="utf-8"))
        stats = build(folder, {**model, "meshes": mapping["meshes"]})
        model.update(stats)
    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
