"""
삼각근 해부학 도판 생성 — BodyParts3D 모델(models/shoulder-right.glb)에서 직접 렌더링

만드는 것 (media/plates/deltoid/):
  hero.svg                대표 도판 (앞가쪽 사선)
  view-*.svg              다각도 7장 (앞·뒤·가쪽·안쪽·앞가쪽 사선·뒤가쪽 사선·위)
  parts.svg               앞·중간·뒤섬유 구분 (가쪽면, 주변 구조 흐리게)
  origin.svg              기시 (위에서 본 빗장뼈·봉우리·어깨뼈가시, 접촉면 계산)
  insertion.svg           정지 (가쪽에서 본 위팔뼈, 접촉면 계산)
  abduction/f*.svg        어깨관절 벌림 0–90°  (앞면)
  flexion/f*.svg          어깨관절 굽힘 0–90°  (가쪽면)
  extension/f*.svg        어깨관절 폄 0–50°    (가쪽면)
그리고 data/media.json 에 출처·라이선스·검증 상태와 함께 등록합니다.

움직임 도판의 단순화 (도판에 명시):
  - 위팔뼈만 '위팔뼈머리 중심(구 맞춤으로 계산)'을 축으로 강체 회전. 어깨뼈·빗장뼈는 고정
    (실제로는 어깨위팔리듬으로 어깨뼈가 함께 돌아감)
  - 근육은 변형하지 않고 '작용선'(기시 접촉면 중심 → 정지 접촉면 중심)으로 표시
  - 작용선 길이 변화는 기하학 계산값이며 근육 활성도를 뜻하지 않음

사용법: python3 tools/make_deltoid_plates.py   (약 4–6분)
"""
import collections
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plate_renderer as R  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
OUT = os.path.join(ROOT, "media", "plates", "deltoid")
GEN = "tools/make_deltoid_plates.py"
SIZE = (1200, 1000)
AREA = (250, 40, 950, 900)
CREDIT = "형상: BodyParts3D © DBCLS (CC BY 4.0 / 원본 OBJ 표기 CC BY-SA 2.1 JP) · 도판: 자체 렌더링 · 검토 필요"

PART = {
    "deltoid_anterior": ("#D1495B", "삼각근 앞섬유", "빗장부분 · clavicular part"),
    "deltoid_middle": ("#E89B2E", "삼각근 중간섬유", "봉우리부분 · acromial part"),
    "deltoid_posterior": ("#2E86AB", "삼각근 뒤섬유", "가시부분 · spinal part"),
}
MUTED_MUSCLE = "#DDB8AF"
FADED_MUSCLE = "#EFE6E3"
BONE = "#F1EADB"
CART = "#C9DEE0"

LABELS = [  # (meshId, 명칭, 보조 명칭) — 우선순위 순
    ("deltoid_anterior",), ("deltoid_middle",), ("deltoid_posterior",),
    ("clavicle", "빗장뼈", "clavicle"), ("scapula", "어깨뼈", "scapula"), ("humerus", "위팔뼈", "humerus"),
    ("pecmaj_sternocostal", "큰가슴근", "pectoralis major"), ("trapezius_descending", "등세모근", "trapezius"),
    ("infraspinatus", "가시아래근", "infraspinatus"), ("teres_minor", "작은원근", "teres minor"),
    ("teres_major", "큰원근", "teres major"), ("supraspinatus", "가시위근", "supraspinatus"),
    ("biceps_long", "위팔두갈래근", "biceps brachii"), ("triceps_lateral", "위팔세갈래근", "triceps brachii"),
    ("serratus_anterior", "앞톱니근", "serratus anterior"), ("subscapularis", "어깨밑근", "subscapularis"),
    ("pectoralis_minor", "작은가슴근", "pectoralis minor"), ("sternum_body", "복장뼈", "sternum"),
    ("rhomboid_major", "큰마름근", "rhomboid major"), ("levator_scapulae", "어깨올림근", "levator scapulae"),
]

VIEWS = {  # id: (방향, 위쪽, 한글 이름, 설명)
    "front": ((0, 0, 1), (0, 1, 0), "앞면", "앞에서 본 오른쪽 어깨"),
    "back": ((0, 0, -1), (0, 1, 0), "뒷면", "뒤에서 본 오른쪽 어깨"),
    "right": ((-1, 0, 0), (0, 1, 0), "가쪽면", "오른쪽 바깥에서 본 모습 — 세 섬유가 모두 보임"),
    "left": ((1, 0, 0), (0, 1, 0), "안쪽면", "몸 안쪽(왼쪽)에서 본 모습 — 이 모델은 오른쪽 어깨만 포함"),
    "oblique-front": ((-0.62, 0.25, 0.75), (0, 1, 0), "앞가쪽 사선", "앞쪽 바깥에서 비스듬히 본 모습"),
    "oblique-back": ((-0.62, 0.25, -0.75), (0, 1, 0), "뒤가쪽 사선", "뒤쪽 바깥에서 비스듬히 본 모습"),
    "top": ((0, 1, 0), (0, 0, 1), "위에서", "위에서 내려다본 모습 — 화면 위쪽이 몸의 앞쪽"),
}


def base_colors(mapping, style="normal"):
    items = []
    for m in mapping:
        if m["layer"] == "skin":
            continue
        mid = m["meshId"]
        if mid in PART:
            c = PART[mid][0]
        elif m["category"] == "bone":
            c = BONE
        elif m["category"] == "cartilage":
            c = CART
        else:
            c = FADED_MUSCLE if style == "faded" else MUTED_MUSCLE
        items.append((mid, c))
    return items


def labels_for(cv, ids, wanted, limit=11, min_px=450):
    names = [w[0] for w in wanted]
    an = R.anchors(cv, ids, set(names))
    out = []
    used_text = set()
    for w in wanted:
        mid = w[0]
        if mid not in an or an[mid][2] < min_px:
            continue
        if mid in PART:
            color, text, sub = PART[mid]
            sw = True
        else:
            text, sub, color, sw = w[1], w[2], "#2B2F38", False
        if text in used_text:
            continue
        used_text.add(text)
        x, y, _ = an[mid]
        out.append({"x": x, "y": y, "text": text, "sub": sub, "color": color, "swatch": sw})
        if len(out) >= limit:
            break
    return out


def save(name, svg_text, png=None):
    path = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(svg_text)
    return f"media/plates/deltoid/{name}"


def plate(meshes, mapping, view_key, title, subtitle, style="normal", label_set=None, extra="", vertex_colors=None,
          items=None, fit=None):
    d, up, _, _ = VIEWS[view_key]
    v = R.View(d, up)
    items = items or base_colors(mapping, style)
    cv, ids, screen, scale = R.render(meshes, items, v, SIZE, AREA, vertex_colors=vertex_colors, fit_names=fit)
    labs = labels_for(cv, ids, label_set or LABELS)
    w, h, rgb = cv.downsample(2)
    png = R.png_bytes(w, h, rgb)
    lay = R.layout_labels(labs, SIZE, AREA, gap=46)
    comp = R.compass(v, 1130, 905, {"up": "위", "front": "앞", "left": "안쪽"})
    names = [l["text"] for l in sorted(lay, key=lambda l: (l["side"], l["ty"]))]
    return R.svg(png, SIZE, lay, title, subtitle, CREDIT, comp, extra), names, v


# ------------------------------------------------------------------ 기하 계산
def grid_of(pts, cell):
    g = collections.defaultdict(list)
    for i, p in enumerate(pts):
        g[(int(p[0] // cell), int(p[1] // cell), int(p[2] // cell))].append(i)
    return g


def contact_vertices(bone_pts, muscle_pts, tol=0.3):
    """근육 메쉬와 tol(cm) 이내로 맞닿은 뼈 정점 인덱스"""
    g = grid_of(muscle_pts, tol)
    hit = []
    for i, p in enumerate(bone_pts):
        k = (int(p[0] // tol), int(p[1] // tol), int(p[2] // tol))
        found = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in g.get((k[0] + dx, k[1] + dy, k[2] + dz), ()):
                        if math.dist(p, muscle_pts[j]) <= tol:
                            found = True
                            break
                    if found:
                        break
                if found:
                    break
            if found:
                break
        if found:
            hit.append(i)
    return hit


def centroid(pts):
    n = len(pts)
    return tuple(sum(p[i] for p in pts) / n for i in range(3))


def solve4(a, b):
    m = [row[:] + [b[i]] for i, row in enumerate(a)]
    n = 4
    for c in range(n):
        piv = max(range(c, n), key=lambda r: abs(m[r][c]))
        m[c], m[piv] = m[piv], m[c]
        for r in range(n):
            if r != c:
                f = m[r][c] / m[c][c]
                for k in range(c, n + 1):
                    m[r][k] -= f * m[c][k]
    return [m[i][n] / m[i][i] for i in range(n)]


def sphere_fit(pts):
    """대수적 최소제곱 구 맞춤: x²+y²+z² = 2ax+2by+2cz+d"""
    ata = [[0.0] * 4 for _ in range(4)]
    atb = [0.0] * 4
    for x, y, z in pts:
        row = [2 * x, 2 * y, 2 * z, 1.0]
        rhs = x * x + y * y + z * z
        for i in range(4):
            atb[i] += row[i] * rhs
            for j in range(4):
                ata[i][j] += row[i] * row[j]
    a, b, c, d = solve4(ata, atb)
    return (a, b, c), math.sqrt(d + a * a + b * b + c * c)


def main():
    meshes = R.read_glb(os.path.join(ROOT, "models", "shoulder-right.glb"))
    mapping = json.load(open(os.path.join(ROOT, "data", "mappings", "shoulder-right.json"), encoding="utf-8"))["meshes"]
    media = []

    def add(**kw):
        kw.setdefault("provenance", "model-render")
        kw.setdefault("schematic", False)
        kw.setdefault("license", "CC BY-SA 4.0 (BodyParts3D 파생 도판)")
        kw.setdefault("source", "BodyParts3D 4.0 © DBCLS — 형상 원본 / 색·설명선·표시: 자체 제작")
        kw.setdefault("reviewStatus", "needs-review")
        kw.setdefault("generator", GEN)
        media.append(kw)

    # 1) 대표 도판
    svg, names, _ = plate(meshes, mapping, "oblique-front", "삼각근 (Deltoid)",
                          "앞가쪽에서 본 오른쪽 어깨 · 세 섬유를 색으로 구분")
    url = save("hero.svg", svg)
    add(id="pl-deltoid-hero", anatomyItemId="m-deltoid", type="plate", role="hero", url=url, labels=names,
        title="삼각근 대표 도판", description="앞가쪽 사선에서 본 오른쪽 어깨. 앞섬유(빨강)·중간섬유(주황)·뒤섬유(파랑)",
        altText="BodyParts3D 모델로 렌더링한 오른쪽 어깨 도판. 삼각근 세 부분이 색으로 구분되고 주변 근육·뼈에 명칭이 표시됨")
    print("hero")

    # 2) 다각도
    for key, (_, _, ko, desc) in VIEWS.items():
        svg, names, _ = plate(meshes, mapping, key, f"삼각근 · {ko}", desc)
        url = save(f"view-{key}.svg", svg)
        add(id=f"pl-deltoid-view-{key}", anatomyItemId="m-deltoid", type="image", viewAngle=key, url=url, labels=names,
            title=f"{ko}", description=desc, altText=f"BodyParts3D 모델의 오른쪽 어깨를 {ko}에서 렌더링한 도판")
        print("view", key)

    # 3) 섬유 구분 (가쪽면, 주변 흐리게) + 부분별 기시 설명
    part_labels = [("deltoid_anterior",), ("deltoid_middle",), ("deltoid_posterior",),
                   ("clavicle", "빗장뼈", "clavicle"), ("scapula", "어깨뼈 (봉우리·가시)", "scapula"), ("humerus", "위팔뼈", "humerus")]
    extra = ('<g font-size="14" fill="#2B2F38">'
             '<rect x="24" y="760" width="430" height="128" rx="10" fill="#fff" stroke="#D2CCBE"/>'
             '<rect x="40" y="778" width="14" height="14" rx="3" fill="#D1495B"/><text x="62" y="790">앞섬유: 빗장뼈 가쪽 1/3 → 굽힘·안쪽돌림</text>'
             '<rect x="40" y="808" width="14" height="14" rx="3" fill="#E89B2E"/><text x="62" y="820">중간섬유: 봉우리 → 벌림 (주동)</text>'
             '<rect x="40" y="838" width="14" height="14" rx="3" fill="#2E86AB"/><text x="62" y="850">뒤섬유: 어깨뼈가시 → 폄·가쪽돌림</text>'
             '<text x="40" y="876" fill="#5B6170" font-size="12">정지은 세 부분 공통: 위팔뼈 세모근거친면</text></g>')
    svg, names, _ = plate(meshes, mapping, "right", "삼각근의 세 부분", "가쪽면 · 주변 근육은 흐리게 표시",
                      style="faded", label_set=part_labels, extra=extra)
    url = save("parts.svg", svg)
    add(id="pl-deltoid-parts", anatomyItemId="m-deltoid", type="plate", role="parts", url=url, labels=names,
        title="앞·중간·뒤섬유 구분", description="가쪽면에서 본 세 부분과 각 부분의 기시·주요 기능",
        altText="가쪽에서 본 삼각근. 앞섬유·중간섬유·뒤섬유가 서로 다른 색으로 칠해짐")
    print("parts")

    # 4) 기시·정지 (모델 접촉면 계산)
    hum = meshes["humerus"]["v"]
    hy = [p[1] for p in hum]
    htop, hbot = max(hy), min(hy)
    vc_origin = {"clavicle": [None] * len(meshes["clavicle"]["v"]), "scapula": [None] * len(meshes["scapula"]["v"])}
    vc_insert = {"humerus": [None] * len(hum)}
    origin_pts, insert_pts = {}, {}
    for part, (color, _, _) in PART.items():
        mv = meshes[part]["v"]
        rgb = R.hex_rgb(color)
        for bone in ("clavicle", "scapula"):
            hit = contact_vertices(meshes[bone]["v"], mv)
            for i in hit:
                vc_origin[bone][i] = rgb
            if hit:
                origin_pts.setdefault(part, []).extend(meshes[bone]["v"][i] for i in hit)
        hit = [i for i in contact_vertices(hum, mv) if (htop - hum[i][1]) / (htop - hbot) > 0.22]
        for i in hit:
            vc_insert["humerus"][i] = R.hex_rgb("#1E2A44")
        insert_pts[part] = [hum[i] for i in hit]
    bones_items = [("clavicle", BONE), ("scapula", BONE), ("humerus", BONE)]  # 교재처럼 세 뼈만 따로
    fit = ["clavicle", "scapula", "humerus"]
    o_labels = [("deltoid_anterior",), ("deltoid_middle",), ("deltoid_posterior",)]

    def attach_plate(key, title, subtitle, legend, fit_names, vc):
        d, up, _, _ = VIEWS[key]
        v = R.View(d, up)
        cv, ids, screen, _ = R.render(meshes, bones_items, v, SIZE, AREA, vertex_colors=vc, fit_names=fit_names)
        labs = []
        for part, (color, text, sub) in PART.items():
            pts = origin_pts.get(part) if "기시" in title else insert_pts.get(part)
            if pts:
                x, y = screen(centroid(pts))
                labs.append({"x": x, "y": y, "text": text, "sub": legend[part], "color": color if "기시" in title else "#1E2A44", "swatch": True})
        for mid, ko, en in (("clavicle", "빗장뼈", "clavicle"), ("scapula", "어깨뼈", "scapula"), ("humerus", "위팔뼈", "humerus")):
            an = R.anchors(cv, ids, {mid})
            if mid in an:
                labs.append({"x": an[mid][0], "y": an[mid][1], "text": ko, "sub": en, "color": "#2B2F38"})
        w, h, rgb = cv.downsample(2)
        lay = R.layout_labels(labs, SIZE, AREA, gap=46)
        note = ('<text x="600" y="925" font-size="12" fill="#5B6170" text-anchor="middle">'
                '색칠한 부위 = 모델에서 근육 메쉬가 뼈 표면에 0.3cm 이내로 맞닿은 정점 (근사 부착 영역)</text>')
        names = [f'{l["text"]} — {l["sub"]}' if l.get("swatch") else l["text"] for l in sorted(lay, key=lambda l: (l["side"], l["ty"]))]
        return R.svg(R.png_bytes(w, h, rgb), SIZE, lay, title, subtitle, CREDIT,
                     R.compass(v, 1130, 905, {"up": "위", "front": "앞", "left": "안쪽"}), note), names

    svg, names = attach_plate("top", "삼각근의 기시", "위에서 본 빗장뼈·봉우리·어깨뼈가시 (화면 위쪽 = 앞)",
                       {"deltoid_anterior": "빗장뼈 가쪽 1/3", "deltoid_middle": "어깨뼈의 봉우리", "deltoid_posterior": "어깨뼈가시"},
                       fit, vc_origin)
    url = save("origin.svg", svg)
    add(id="pl-deltoid-origin", anatomyItemId="m-deltoid", type="plate", role="attachment", url=url, labels=names,
        title="기시 (Origin)", description="세 부분의 기시을 부분별 색으로 표시 — 모델 접촉면으로 계산한 근사 영역",
        altText="위에서 본 빗장뼈와 어깨뼈. 빗장뼈 가쪽, 봉우리, 어깨뼈가시에 세 가지 색 영역이 칠해짐")
    svg, names = attach_plate("right", "삼각근의 정지", "가쪽에서 본 위팔뼈 · 세모근거친면 (세 부분 공통)",
                       {"deltoid_anterior": "→ 세모근거친면", "deltoid_middle": "→ 세모근거친면", "deltoid_posterior": "→ 세모근거친면"},
                       ["humerus", "scapula", "clavicle"], vc_insert)
    url = save("insertion.svg", svg)
    add(id="pl-deltoid-insertion", anatomyItemId="m-deltoid", type="plate", role="attachment", url=url, labels=names,
        title="정지 (Insertion)", description="위팔뼈 가쪽면의 세모근거친면 — 모델 접촉면으로 계산한 근사 영역",
        altText="가쪽에서 본 위팔뼈. 몸통 중간 위쪽 가쪽면에 진한 남색 영역이 칠해짐")
    print("attachments")

    # 5) 움직임 도판
    head_pts = [p for p in hum if (htop - p[1]) / (htop - hbot) < 0.10]
    center, radius = sphere_fit(head_pts)
    print("humeral head center", [round(c, 2) for c in center], "r", round(radius, 2))

    def action_ends(muscle, origin_bones, distal_min):
        mv = meshes[muscle]["v"]
        o = []
        for b in origin_bones:
            o += [meshes[b]["v"][i] for i in contact_vertices(meshes[b]["v"], mv)]
        ins = [hum[i] for i in contact_vertices(hum, mv) if (htop - hum[i][1]) / (htop - hbot) >= distal_min]
        return (centroid(o) if o else None), (centroid(ins) if ins else None)

    LINES = {
        "deltoid_anterior": (action_ends("deltoid_anterior", ["clavicle"], 0.22), "#D1495B", "전면"),
        "deltoid_middle": (action_ends("deltoid_middle", ["scapula"], 0.22), "#E89B2E", "측면"),
        "deltoid_posterior": (action_ends("deltoid_posterior", ["scapula"], 0.22), "#2E86AB", "후면"),
        "supraspinatus": (action_ends("supraspinatus", ["scapula"], 0.0), "#6A994E", "가시위근"),
        "pecmaj_clavicular": (action_ends("pecmaj_clavicular", ["clavicle"], 0.10), "#9B5DE5", "큰가슴근 빗장부분"),
        "teres_major": (action_ends("teres_major", ["scapula"], 0.10), "#5C677D", "큰원근"),
    }
    seqs = {
        "abduction": ("mv-shoulder-abduction", "front", (0, 0, -1), list(range(0, 91, 15)), "벌림",
                      ["deltoid_anterior", "deltoid_middle", "deltoid_posterior", "supraspinatus"]),
        "flexion": ("mv-shoulder-flexion", "right", (-1, 0, 0), list(range(0, 91, 15)), "굽힘",
                    ["deltoid_anterior", "deltoid_middle", "deltoid_posterior", "pecmaj_clavicular"]),
        "extension": ("mv-shoulder-extension", "right", (1, 0, 0), list(range(0, 51, 10)), "폄",
                      ["deltoid_anterior", "deltoid_middle", "deltoid_posterior", "teres_major"]),
    }
    bones_only = [(m["meshId"], BONE if m["category"] == "bone" else CART) for m in mapping
                  if m["category"] in ("bone", "cartilage")]
    for seq, (item_id, vkey, axis, angles, ko, line_ids) in seqs.items():
        d, up, _, _ = VIEWS[vkey]
        v = R.View(d, up)
        # 모든 프레임의 화면 맞춤을 같게: 회전 범위 전체의 위팔뼈 위치를 포함하는 기준 구조
        base_len = {}
        torso = ["scapula", "clavicle", "rib_1", "rib_8", "sternum_body", "vertebra_c7", "vertebra_t8"]
        fit_pts = [p for n in torso for p in meshes[n]["v"][::10]]
        for a in (angles[0], angles[len(angles) // 2], angles[-1]):
            fit_pts += [R.rotate_point(p, center, axis, a) for p in hum[::10]]
        for fi, ang in enumerate(angles):
            tf = {"humerus": (lambda p, a=ang: R.rotate_point(p, center, axis, a), lambda n, a=ang: R.rotate_vec(n, axis, a))}
            items = [it for it in bones_only if it[0] != "humerus"] + [("humerus", "#E9DABA")]
            cv, ids, screen, scale = R.render(meshes, items, v, SIZE, AREA, transforms=tf, fit_points=fit_pts)
            # 작용선
            svg_lines, legend = [], []
            for k in line_ids:
                (o, ins), color, name = LINES[k]
                if not o or not ins:
                    continue
                ins_r = R.rotate_point(ins, center, axis, ang)
                length = math.dist(o, ins_r)
                base_len.setdefault(k, length)
                ch = (length - base_len[k]) / base_len[k] * 100
                (x1, y1), (x2, y2) = screen(o), screen(ins_r)
                svg_lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="5" stroke-linecap="round" opacity=".9"/>'
                                 f'<circle cx="{x1:.1f}" cy="{y1:.1f}" r="7" fill="#fff" stroke="{color}" stroke-width="3"/>'
                                 f'<circle cx="{x2:.1f}" cy="{y2:.1f}" r="7" fill="{color}" stroke="#fff" stroke-width="2"/>')
                legend.append((color, name, length, ch))
            hx, hy2 = screen(center)
            arc = ""
            if ang:
                arc = (f'<circle cx="{hx:.1f}" cy="{hy2:.1f}" r="10" fill="none" stroke="#1E2A44" stroke-width="2"/>'
                       f'<text x="{hx:.1f}" y="{hy2 - 18:.1f}" font-size="20" font-weight="700" fill="#1E2A44" text-anchor="middle">{ang}°</text>')
            else:
                arc = f'<circle cx="{hx:.1f}" cy="{hy2:.1f}" r="10" fill="none" stroke="#1E2A44" stroke-width="2"/>'
            leg = ['<g font-size="14" fill="#2B2F38"><rect x="24" y="40" width="300" height="' + str(46 + 26 * len(legend)) + '" rx="10" fill="#fff" stroke="#D2CCBE"/>',
                   '<text x="40" y="64" font-weight="700" fill="#1E2A44">작용선 길이 (0° 대비)</text>']
            for i, (color, name, length, ch) in enumerate(legend):
                y = 92 + 26 * i
                leg.append(f'<rect x="40" y="{y - 12}" width="14" height="14" rx="3" fill="{color}"/>'
                           f'<text x="62" y="{y}">{name}</text><text x="308" y="{y}" text-anchor="end">{length:.1f} cm ({ch:+.0f}%)</text>')
            leg.append("</g>")
            note = ('<text x="600" y="925" font-size="12" fill="#5B6170" text-anchor="middle">'
                    '단순화: 위팔뼈만 위팔뼈머리 중심에서 회전, 어깨뼈·빗장뼈 고정 · 선 = 기시→정지 작용선(근육 변형 아님) · 높은 각도에서 뼈가 겹쳐 보일 수 있음</text>')
            w, h, rgb = cv.downsample(2)
            title = f"어깨관절 {ko} {ang}°"
            sub = {"abduction": "앞면 · 관상면 움직임", "flexion": "가쪽면 · 시상면 움직임 (팔이 앞으로)", "extension": "가쪽면 · 시상면 움직임 (팔이 뒤로)"}[seq]
            svg = R.svg(R.png_bytes(w, h, rgb), SIZE, [], title, sub, CREDIT,
                        R.compass(v, 1130, 905, {"up": "위", "front": "앞", "left": "안쪽"}),
                        "".join(svg_lines) + arc + "".join(leg) + note)
            url = save(f"{seq}/f{fi:02d}.svg", svg)
            add(id=f"pl-{seq}-{fi:02d}", anatomyItemId=item_id, type="frame", sequence="bp3d", sequenceLabel="모델 도판 (BodyParts3D)",
                frameOrder=fi, frameLabel=f"{ang}°", url=url, viewAngle=vkey, title=title,
                description="위팔뼈 회전 + 근육 작용선 (단순화 도판)",
                altText=f"BodyParts3D 뼈 모델에서 위팔뼈를 {ang}도 {ko}시킨 도판과 삼각근 작용선")
            print(seq, ang)

    # data/media.json 에 병합 (이 스크립트가 만든 항목만 교체)
    mpath = os.path.join(ROOT, "data", "media.json")
    allm = [m for m in json.load(open(mpath, encoding="utf-8")) if m.get("generator") != GEN]
    allm += media
    json.dump(allm, open(mpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(len(media), "media registered")


if __name__ == "__main__":
    main()
