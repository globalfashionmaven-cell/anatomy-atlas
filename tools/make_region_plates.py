"""
전 부위 해부학 도판 생성 — 부위별 BodyParts3D 모델(models/*.glb)에서 직접 렌더링

항목마다 만드는 것 (media/plates/<itemId>/):
  근육 (모델에 근육 메쉬가 있는 경우)
    hero.svg        대표 도판 — 그 근육을 빨강으로, 주변 근육은 흐린 색, 뼈는 상아색
                    시점은 6~7개 후보 중 '그 근육이 가장 많이 보이는 방향'을 저해상도 렌더로 골라 사용
    attach.svg      부착 도판 — 뼈만 그리고, 근육 메쉬가 뼈 표면에 맞닿은 정점을 빨강으로 칠함
                    (모델 접촉면으로 계산한 '근사 부착 영역'. 기시/정지 구분은 하단 본문 텍스트로)
  뼈
    hero.svg        그 뼈를 금색으로, 같은 모델의 다른 뼈는 흐리게 (근육 숨김)
  근육 메쉬가 모델에 없는 근육 (배벽 근육·씹기근육·얼굴근육·넓은등근·뭇갈래근 등)
    media/plates/region/<group>.svg  — 해당 부위 뼈대만 렌더링하고 '근육 형상 없음'을 크게 표시
    근육 모양을 그려 넣지 않음 (가짜 형상을 만들지 않기 위해). 위치 설명은 본문 텍스트로만.

data/media.json 에 출처·라이선스·검증 상태(needs-review)와 함께 등록합니다.
기존 어깨세모근 도판(tools/make_deltoid_plates.py)은 건드리지 않습니다.

사용법: python3 tools/make_region_plates.py [itemId ...]   (전체 약 5~10분, 병렬)
"""
import json
import math
import multiprocessing as mp
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plate_renderer as R  # noqa: E402
from make_deltoid_plates import contact_vertices  # noqa: E402
import terms_py as TERMS  # noqa: E402  화면과 같은 표시 용어 (구용어 주 명칭·기시/정지)

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
GEN = "tools/make_region_plates.py"
SIZE = (1200, 1000)
AREA = (250, 40, 950, 880)
AREA_ATT = (250, 40, 950, 800)
CREDIT = "형상: BodyParts3D © DBCLS (CC BY 4.0 / 원본 OBJ 표기 CC BY-SA 2.1 JP) · 도판: 자체 렌더링 · 검토 필요"
TARGET = "#C8323C"
BONE_HI = "#E2BE6A"
MUTED = "#DDB8AF"
BONE = "#F1EADB"
BONE_DIM = "#F5F1E8"
CART = "#C9DEE0"
SKIP_DELTOID = {"m-deltoid"}  # 전용 도판이 이미 있음

CHAPTER_MODEL = {
    "spine-breathing": "trunk", "neck": "trunk", "abdomen": "trunk", "shoulder": "shoulder-right", "chest-back": "shoulder-right",
    "upper-arm": "arm-right", "forearm": "arm-right", "hand": "arm-right", "pelvis-hip": "leg-right", "thigh": "leg-right",
    "lower-leg": "leg-right", "foot": "leg-right", "jaw": "head", "face": "head",
}
VIEWS = {
    "front": ((0, 0, 1), (0, 1, 0), "앞면"),
    "back": ((0, 0, -1), (0, 1, 0), "뒷면"),
    "lateral": ((-1, 0, 0), (0, 1, 0), "가쪽면(오른쪽)"),
    "medial": ((1, 0, 0), (0, 1, 0), "안쪽면"),
    "oblique-front": ((-0.62, 0.25, 0.75), (0, 1, 0), "앞가쪽 사선"),
    "oblique-back": ((-0.62, 0.25, -0.75), (0, 1, 0), "뒤가쪽 사선"),
    "bottom": ((0, -1, 0), (0, 0, 1), "아래(발바닥)에서"),
}

# 근육 메쉬가 없는 근육 → 부위 뼈대 도판 그룹
REGION_GROUPS = {
    "abdomen-front": ("trunk", "front", "배벽 부위 뼈대 (앞면)", ["ribs_r", "ribs_l", "costal_cartilage_r", "costal_cartilage_l", "sternum_body",
                      "vertebra_l1", "vertebra_l2", "vertebra_l3", "vertebra_l4", "vertebra_l5", "hip_bone_r", "hip_bone_l", "sacrum"],
                      ["m-rectus-abdominis", "m-internal-oblique", "m-transversus-abdominis"]),
    "lumbar-back": ("trunk", "back", "허리 부위 뼈대 (뒷면)", ["ribs_r", "ribs_l", "vertebra_t10", "vertebra_t11", "vertebra_t12", "vertebra_l1", "vertebra_l2",
                    "vertebra_l3", "vertebra_l4", "vertebra_l5", "hip_bone_r", "hip_bone_l", "sacrum"],
                    ["m-quadratus-lumborum"]),
    "back-full": ("trunk", "back", "등 부위 뼈대 (뒷면)", None, ["m-latissimus-dorsi", "m-multifidus"]),
    "neck-front": ("trunk", "front", "목 부위 뼈대 (앞면)", ["vertebra_c1", "vertebra_c2", "vertebra_c3", "vertebra_c4", "vertebra_c5", "vertebra_c6",
                   "vertebra_c7", "vertebra_t1", "vertebra_t2", "vertebra_t3", "manubrium", "hyoid"], ["m-longus-colli"]),
    "hand-palm": ("arm-right", "front", "손 부위 뼈대 (손바닥 쪽)", ["metacarpals", "phalanges_hand", "carpal_scaphoid", "carpal_lunate", "carpal_triquetral",
                  "carpal_pisiform", "carpal_trapezium", "carpal_trapezoid", "carpal_capitate", "carpal_hamate"], ["m-interossei-hand"]),
    "jaw-lateral": ("head", "lateral", "턱 부위 뼈대 (가쪽면)", None,
                    ["m-masseter", "m-temporalis", "m-medial-pterygoid", "m-lateral-pterygoid"]),
    "face-front": ("head", "front", "얼굴 부위 뼈대 (앞면)", None,
                   ["m-frontalis", "m-orbicularis-oculi", "m-procerus", "m-nasalis", "m-orbicularis-oris", "m-buccinator",
                    "m-zygomaticus-major", "m-zygomaticus-minor", "m-levator-anguli-oris", "m-depressor-anguli-oris", "m-mentalis"]),
}

MODELS = {}  # id -> (meshes, mapping, bbox)

# 본문(기시·정지) 텍스트에서 뼈를 찾는 정규식 — 뼈 항목/메쉬 그룹별
BONE_RX = {
    "b-scapula": r"어깨뼈|봉우리|부리돌기|관절위결절|관절아래결절|가시위오목|가시아래오목|어깨밑오목",
    "b-clavicle": r"빗장뼈",
    "b-sternum": r"복장뼈|칼돌기",
    "b-ribs": r"갈비",
    "b-humerus": r"위팔뼈|위관절융기|세모근거친면|큰결절|작은결절|결절사이고랑",
    "b-radius": r"노뼈|붓돌기 \(노",
    "b-ulna": r"자뼈|팔꿈치머리|갈고리돌기",
    "b-carpals": r"손목뼈|콩알뼈|갈고리뼈|큰마름뼈|작은마름뼈|손배뼈|알머리뼈|반달뼈|세모뼈|굽힘근지지띠",
    "b-metacarpals": r"손허리뼈",
    "b-phalanges-hand": r"손가락.{0,6}마디|손가락뼈|엄지.{0,6}마디",
    "b-hip-bone": r"볼기뼈|엉덩뼈|궁둥|두덩|AIIS|ASIS|절구",
    "b-sacrum": r"엉치뼈",
    "b-femur": r"넙다리뼈|큰돌기|작은돌기|거친선|볼기근거친면",
    "b-patella": r"무릎뼈",
    "b-tibia": r"정강뼈",
    "b-fibula": r"종아리뼈",
    "b-tarsals": r"목말뼈|발꿈치뼈|발배뼈|입방뼈|쐐기뼈|발목뼈",
    "b-metatarsals": r"발허리뼈",
    "b-phalanges-foot": r"발가락.{0,6}마디|첫마디뼈|중간마디뼈|끝마디뼈 \(발",
    "b-cervical-vertebrae": r"목뼈|C[1-7]|고리뼈|중쇠뼈",
    "b-thoracic-vertebrae": r"등뼈|T\d",
    "b-lumbar-vertebrae": r"허리뼈|L\d",
    "b-hyoid": r"목뿔뼈",
    "b-mandible": r"아래턱뼈",
}


def bone_key(mesh_id, entry):
    if entry.get("anatomyItemId") in BONE_RX:
        return entry["anatomyItemId"]
    for pre, key in (("rib_", "b-ribs"), ("costal", "b-ribs"), ("vertebra_c", "b-cervical-vertebrae"),
                     ("vertebra_t", "b-thoracic-vertebrae"), ("vertebra_l", "b-lumbar-vertebrae")):
        if mesh_id.startswith(pre):
            return key
    return None


def bbox(pts):
    xs, ys, zs = zip(*pts)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def load_models():
    reg = json.load(open(os.path.join(ROOT, "data", "models3d.json"), encoding="utf-8"))
    raw_items = {i["id"]: i for i in json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))}
    for m in reg["models"]:
        meshes = R.read_glb(os.path.join(ROOT, m["url"]))
        mapping = json.load(open(os.path.join(ROOT, m["mapping"]), encoding="utf-8"))["meshes"]
        for e in mapping:  # 표시 이름은 구용어, 본문 대조용 원래 이름은 newKoreanName
            e["newKoreanName"] = e["koreanName"]
            e["koreanName"] = TERMS.mesh_name(e, raw_items.get(e.get("anatomyItemId") or ""))
        boxes = {k: bbox(v["v"]) for k, v in meshes.items()}
        MODELS[m["id"]] = (meshes, mapping, boxes)


def fade_outside(w, h, rgb, area, bg=(253, 252, 249), soft=40):
    """그림 영역 밖(좌우 명칭 열·아래 제목 줄)으로 삐져나온 주변 구조를 배경색 쪽으로 흐리게"""
    x0, x1, y0, y1 = area[0] - 10, area[2] + 10, area[1] - 14, area[3] + 10
    for y in range(h):
        dy = y - y1 if y > y1 else (y0 - y) * 2 if y < y0 else 0
        for x in range(w):
            dx = (x0 - x) if x < x0 else (x - x1) if x > x1 else 0
            d = max(dx, dy)
            if d <= 0:
                continue
            f = min(0.88, d / soft * 0.88)
            o = (y * w + x) * 3
            rgb[o] = int(rgb[o] * (1 - f) + bg[0] * f)
            rgb[o + 1] = int(rgb[o + 1] * (1 - f) + bg[1] * f)
            rgb[o + 2] = int(rgb[o + 2] * (1 - f) + bg[2] * f)


def color_of(entry):
    return BONE if entry["category"] == "bone" else CART if entry["category"] == "cartilage" else MUTED


def context_meshes(model_id, target_names, grow=0.35, min_grow=2.0, cats=None):
    meshes, mapping, boxes = MODELS[model_id]
    lo = [min(boxes[n][0][i] for n in target_names) for i in range(3)]
    hi = [max(boxes[n][1][i] for n in target_names) for i in range(3)]
    diag = math.dist(lo, hi)
    g = max(min_grow, grow * diag)
    lo = [v - g for v in lo]
    hi = [v + g for v in hi]
    out = []
    for e in mapping:
        if e["layer"] == "skin" or e["meshId"] not in meshes:
            continue
        if cats and e["category"] not in cats:
            continue
        b0, b1 = boxes[e["meshId"]]
        if all(b0[i] <= hi[i] and b1[i] >= lo[i] for i in range(3)):
            out.append(e)
    return out, (lo, hi)


def best_view(model_id, target_names, items, allow_bottom=False):
    meshes = MODELS[model_id][0]
    pts = [p for n in target_names for p in meshes[n]["v"]]
    lo, hi = bbox(pts)
    c = [(lo[i] + hi[i]) / 2 for i in range(3)]
    r = math.dist(lo, hi) / 2
    sphere = [tuple(c[j] + (r if j == i else 0) * s for j in range(3)) for i in range(3) for s in (-1, 1)]
    scores = {}
    for key, (d, up, _) in VIEWS.items():
        if key == "bottom" and not allow_bottom:
            continue
        v = R.View(d, up)
        cv, ids, _, _ = R.render(meshes, items, v, (240, 200), (0, 0, 240, 200), ss=1, fit_points=sphere)
        tid = {k for k, n in ids.items() if n in target_names}
        scores[key] = sum(1 for x in cv.id if x in tid) * (1.08 if key in ("front", "lateral", "back") else 1.0)
    return max(scores, key=scores.get), scores


def short(text, n):
    text = " · ".join(text) if isinstance(text, list) else str(text or "")
    return text if len(text) <= n else text[: n - 1] + "…"


def compass(v):
    return R.compass(v, 1130, 905, {"up": "위", "front": "앞", "left": "왼쪽(대상자)"})


def finish(cv, area):
    w, h, rgb = cv.downsample(2)
    fade_outside(w, h, rgb, area)
    return R.png_bytes(w, h, rgb)


def save(rel, text):
    path = os.path.join(ROOT, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    return rel


def base_media(**kw):
    kw.setdefault("provenance", "model-render")
    kw.setdefault("schematic", False)
    kw.setdefault("license", "CC BY-SA 4.0 (BodyParts3D 파생 도판)")
    kw.setdefault("source", "BodyParts3D 4.0 © DBCLS — 형상 원본 / 색·설명선·표시: 자체 제작")
    kw.setdefault("reviewStatus", "needs-review")
    kw.setdefault("generator", GEN)
    return kw


# ------------------------------------------------------------------ 근육
def job_muscle(args):
    model_id, item = args
    meshes, mapping, boxes = MODELS[model_id]
    tnames = [e["meshId"] for e in mapping if e.get("anatomyItemId") == item["id"] and e["meshId"] in meshes]
    ctx, _ = context_meshes(model_id, tnames)
    names = {e["meshId"] for e in ctx} | set(tnames)
    entries = {e["meshId"]: e for e in mapping}
    # 맞닿은 뼈 (접촉 허용 거리를 단계적으로 늘림 — 힘줄 부분이 메쉬에 없을 수 있음)
    bones = [e["meshId"] for e in mapping if e["category"] == "bone" and e["meshId"] in meshes]
    tpts = [p for n in tnames for p in meshes[n]["v"]]
    t_lo, t_hi = bbox(tpts)
    touched, tol_used = {}, None
    for tol in (0.35, 0.8, 1.5):
        for b in bones:
            b0, b1 = boxes[b]
            if not all(b0[i] - tol <= t_hi[i] and b1[i] + tol >= t_lo[i] for i in range(3)):
                continue
            hit = contact_vertices(meshes[b]["v"], tpts, tol)
            if len(hit) >= 6:
                touched[b] = hit
        if touched:
            tol_used = tol
            break
    names |= set(touched)
    allow_bottom = item["chapterId"] == "foot"
    # 시점 선택: 다른 근육을 모두 뺀 상태(뼈 + 대상 근육)에서 대상이 가장 많이 보이는 방향
    skel = [(n, TARGET if n in tnames else color_of(entries[n])) for n in names
            if n in tnames or entries[n]["category"] in ("bone", "cartilage")]
    vkey, _ = best_view(model_id, tnames, skel, allow_bottom)
    d, up, vko = VIEWS[vkey]
    v = R.View(d, up)
    fit = tnames + list(touched)
    # 화면 맞춤: 대상 근육 + (닿은 뼈 중 근육 주변 범위 안의 부분) — 긴 뼈 때문에 근육이 작아지지 않게
    tdiag = math.dist(t_lo, t_hi)
    g = max(2.0, 0.45 * tdiag)
    in_box = lambda p: all(t_lo[i] - g <= p[i] <= t_hi[i] + g for i in range(3))  # noqa: E731
    fit_pts = tpts[::3] + [p for b in touched for p in meshes[b]["v"][::4] if in_box(p)]
    # 가리는 근육 숨기기: 대상이 (뼈만 있을 때) 보이는 픽셀을 다른 근육이 5% 이상 덮으면 숨김
    full = [(n, TARGET if n in tnames else color_of(entries[n])) for n in names]
    lo_size, lo_area = (480, 400), (100, 16, 380, 352)
    cv_a, ids_a, _, _ = R.render(meshes, skel, v, lo_size, lo_area, ss=1, fit_points=fit_pts)
    cv_b, ids_b, _, _ = R.render(meshes, full, v, lo_size, lo_area, ss=1, fit_points=fit_pts)
    ta = {k for k, n in ids_a.items() if n in tnames}
    vis = [k for k, x in enumerate(cv_a.id) if x in ta]
    cover = {}
    for k in vis:
        n = ids_b.get(cv_b.id[k])
        if n and n not in tnames and entries[n]["category"] == "muscle":
            cover[n] = cover.get(n, 0) + 1
    hidden = sorted(n for n, c in cover.items() if vis and c >= 0.05 * len(vis))
    items = [it for it in full if it[0] not in hidden]
    names -= set(hidden)
    out = []

    # 1) 대표 도판
    cv, ids, screen, _ = R.render(meshes, items, v, SIZE, AREA, fit_points=fit_pts)
    an = R.anchors(cv, ids, names)
    labs = []
    tvis = [an[n] for n in tnames if n in an]
    if tvis:
        x, y, _ = max(tvis, key=lambda a: a[2])
        labs.append({"x": x, "y": y, "text": item["koreanName"], "sub": item.get("englishName", ""), "color": TARGET, "swatch": True})
    used = {item["koreanName"]}
    others = sorted([(an[n][2], n) for n in names if n in an and n not in tnames], reverse=True)
    bone_first = [o for o in others if entries[o[1]]["category"] == "bone"][:4] + [o for o in others if entries[o[1]]["category"] == "muscle"][:6]
    for px, n in bone_first:
        if px < 500:
            continue
        e = entries[n]
        text = (e.get("koreanName") or n).replace(" (오른쪽)", "")
        if text in used:
            continue
        used.add(text)
        x, y, _ = an[n]
        labs.append({"x": x, "y": y, "text": text, "sub": e.get("englishName", ""), "color": "#2B2F38"})
        if len(labs) >= 10:
            break
    lay = R.layout_labels(labs, SIZE, AREA, gap=46)
    hid_names = sorted({(entries[n].get("koreanName") or n).replace(" (오른쪽)", "") for n in hidden})
    if hid_names:
        hidden_note = ('<text x="600" y="905" font-size="13" fill="#8A4B00" text-anchor="middle">'
                       f'대상 근육을 가리는 근육 {len(hid_names)}개를 숨김: {R.esc(short(hid_names, 70))}</text>')
    else:
        hidden_note = ""
    hidden_note += "" if tvis else ('<text x="600" y="885" font-size="13" fill="#B23A48" text-anchor="middle">'
                                   '이 시점에서는 대상 근육이 다른 구조에 가려 거의 보이지 않음 — 3D 보기에서 회전해 확인하세요</text>')
    note = ('<text x="600" y="925" font-size="12" fill="#5B6170" text-anchor="middle">'
            f'빨강 = {R.esc(item["koreanName"])} · 시점은 이 근육이 가장 많이 보이는 방향을 자동 선택 · 오른쪽 몸 모델</text>')
    svgt = R.svg(finish(cv, AREA), SIZE, lay, f'{item["koreanName"]} ({item.get("_sub", "")})', f"{vko}에서 본 모습",
                 CREDIT, compass(v), hidden_note + note)
    url = save(f"media/plates/{item['id']}/hero.svg", svgt)
    lab_names = [l["text"] for l in sorted(lay, key=lambda l: (l["side"], l["ty"]))]
    out.append(base_media(id=f"pl-{item['id']}-hero", anatomyItemId=item["id"], type="plate", role="hero", url=url, viewAngle=vkey,
                          labels=lab_names, model=model_id, hiddenStructures=hid_names,
                          title=f"{item['koreanName']} 대표 도판", description=f"{vko}에서 본 {item['koreanName']} (빨강) 과 주변 구조" + (f" · 가리는 근육 {len(hid_names)}개 숨김" if hid_names else ""),
                          altText=f"BodyParts3D 모델로 렌더링한 도판. {vko}에서 본 {item['koreanName']}이(가) 빨간색으로, 주변 근육은 흐린 색, 뼈는 상아색으로 표시됨"))

    # 2) 부착 도판 — 맞닿은 뼈 중 '본문 기시·정지에 이름이 나오는 뼈'만 색칠
    #    (근육이 뼈 위에 단순히 얹혀 있는 면(예: 위팔두갈래근 ↔ 위팔뼈 몸통)을 부착으로 오해하지 않게)
    o_text = " ".join(item.get("origin") or [])
    i_text = " ".join(item.get("insertion") or [])
    groups = {}
    for b in bones:
        key = bone_key(b, entries[b])
        if not key:
            continue
        rx = re.compile(BONE_RX[key])
        kind = ("origin" if rx.search(o_text) else "") + ("insertion" if rx.search(i_text) else "")
        if kind:
            groups.setdefault(key, []).append((b, "both" if kind == "origininsertion" else kind))
    att = {b: k for lst in groups.values() for b, k in lst if b in touched}
    # 본문에 나오지만 모델에서 맞닿지 않는 뼈 (힘줄이 모델에 없는 경우 등) — 그룹마다 대상에 가장 가까운 뼈 하나
    tc = [(t_lo[i] + t_hi[i]) / 2 for i in range(3)]
    missing = {}
    for key, lst in groups.items():
        if any(b in touched for b, _ in lst):
            continue
        named = [x for x in lst if (entries[x[0]].get("newKoreanName") or "@@").replace("오른쪽 ", "") in o_text + i_text]
        b, k = min(named or lst, key=lambda x: math.dist(tc, [(boxes[x[0]][0][i] + boxes[x[0]][1][i]) / 2 for i in range(3)]))
        missing[b] = k
    matched = bool(att)
    if not matched:
        att = {b: "contact" for b in touched}
    if att:
        KCOL = {"origin": TARGET, "insertion": "#1E2A44", "both": "#7B3FA0", "contact": TARGET}
        KLAB = {"origin": "기시 (근사)", "insertion": "정지 (근사)", "both": "기시·정지 (근사)", "contact": "맞닿은 면"}
        vc = {}
        for bname, k in att.items():
            arr = [None] * len(meshes[bname]["v"])
            for i in touched[bname]:
                arr[i] = R.hex_rgb(KCOL[k])
            vc[bname] = arr
        bctx = [e["meshId"] for e in ctx if e["category"] in ("bone", "cartilage")]
        show = set(bctx) | set(att) | set(missing)
        bitems = [(n, BONE if n in att or n in missing else BONE_DIM) for n in show]
        cv, ids, screen, _ = R.render(meshes, bitems, v, SIZE, AREA_ATT, vertex_colors=vc, fit_names=list(att) + list(missing))
        labs = []
        by_group = {}
        for bname, k in att.items():
            by_group.setdefault((bone_key(bname, entries[bname]) or bname, k), []).append(bname)
        GNAME = {"b-cervical-vertebrae": "목뼈", "b-thoracic-vertebrae": "등뼈", "b-lumbar-vertebrae": "허리뼈", "b-ribs": "갈비뼈"}
        for (gkey, k), lst in by_group.items():
            bname = max(lst, key=lambda n: len(touched[n]))
            hit = touched[bname]
            c = [sum(meshes[bname]["v"][i][q] for i in hit) / len(hit) for q in range(3)]
            x, y = screen(c)
            text = (entries[bname].get("koreanName") or bname).replace("오른쪽 ", "")
            if len(lst) > 1:
                text = f"{GNAME.get(gkey, text)} ({len(lst)}개)"
            labs.append({"x": x, "y": y, "text": text, "sub": KLAB[k], "color": KCOL[k], "swatch": True})
        an = R.anchors(cv, ids, set(missing))
        for bname, k in missing.items():
            if bname in an:
                labs.append({"x": an[bname][0], "y": an[bname][1], "text": (entries[bname].get("koreanName") or bname).replace("오른쪽 ", ""),
                             "sub": "본문상 " + KLAB[k].replace(" (근사)", "") + " · 모델 접촉 없음", "color": "#8A8F99"})
        lay = R.layout_labels(labs[:11], SIZE, AREA_ATT, gap=46, bottom=790)
        o_txt = R.esc(short(item.get("origin"), 62))
        i_txt = R.esc(short(item.get("insertion"), 62))
        how = (f"색칠 = 근육 메쉬가 {tol_used}cm 이내로 맞닿은 뼈 표면 중, 본문 기시·정지에 이름이 나오는 뼈만 (근사 영역)" if matched else
               f"색칠 = 근육 메쉬가 {tol_used}cm 이내로 맞닿은 뼈 표면 (본문과 자동 대응 실패 — 단순 접촉면이 포함될 수 있음)")
        extra = ('<g font-size="15" fill="#2B2F38">'
                 f'<rect x="40" y="829" width="14" height="14" rx="3" fill="{TARGET}"/>'
                 f'<text x="62" y="842"><tspan font-weight="700" fill="#1E2A44">기시</tspan>  {o_txt}</text>'
                 '<rect x="40" y="853" width="14" height="14" rx="3" fill="#1E2A44"/>'
                 f'<text x="62" y="866"><tspan font-weight="700" fill="#1E2A44">정지</tspan>  {i_txt}</text></g>'
                 f'<text x="600" y="900" font-size="12" fill="#5B6170" text-anchor="middle">{R.esc(how)} · 힘줄이 메쉬에 없으면 실제와 다를 수 있음</text>')
        svgt = R.svg(finish(cv, AREA_ATT), SIZE, lay, f"{item['koreanName']} · 기시·정지", f"{vko} · 뼈만 표시",
                     CREDIT, compass(v), extra)
        url = save(f"media/plates/{item['id']}/attach.svg", svgt)
        out.append(base_media(id=f"pl-{item['id']}-attach", anatomyItemId=item["id"], type="plate", role="attachment", url=url, viewAngle=vkey,
                              labels=[l["text"] + " — " + l["sub"] for l in lay], model=model_id, contactToleranceCm=tol_used,
                              attachMatchedToText=matched,
                              title="기시·정지 (근사 영역)",
                              description=("모델 접촉면 중 본문에 나오는 뼈만 색칠 — 빨강 기시, 남색 정지" if matched else
                                           "모델 접촉면 (본문 대응 실패, 단순 접촉 포함 가능)"),
                              altText=f"{item['koreanName']}이(가) 붙는 뼈만 그린 도판. 기시은 빨간색, 정지은 남색으로 뼈 표면이 칠해짐"))
    return item["id"], vkey, len(touched), out


# ------------------------------------------------------------------ 뼈
def job_bone(args):
    model_id, item = args
    meshes, mapping, boxes = MODELS[model_id]
    tnames = [e["meshId"] for e in mapping if e.get("anatomyItemId") == item["id"] and e["meshId"] in meshes]
    ctx, _ = context_meshes(model_id, tnames, grow=0.25, cats={"bone", "cartilage"})
    names = {e["meshId"] for e in ctx} | set(tnames)
    entries = {e["meshId"]: e for e in mapping}
    items = [(n, BONE_HI if n in tnames else (CART if entries[n]["category"] == "cartilage" else BONE_DIM)) for n in names]
    vkey, _ = best_view(model_id, tnames, items, item["chapterId"] == "foot")
    if vkey == "medial" and item["chapterId"] not in ("face", "jaw"):
        vkey = "front"
    d, up, vko = VIEWS[vkey]
    v = R.View(d, up)
    cv, ids, screen, _ = R.render(meshes, items, v, SIZE, AREA, fit_names=tnames)
    an = R.anchors(cv, ids, names)
    labs = []
    used = set()
    for n in sorted(tnames, key=lambda n: -(an.get(n, (0, 0, 0))[2])):
        if n not in an:
            continue
        text = (entries[n].get("koreanName") or n).replace(" (오른쪽)", "")
        if text in used:
            continue
        used.add(text)
        labs.append({"x": an[n][0], "y": an[n][1], "text": text, "sub": entries[n].get("englishName", ""), "color": "#9A6B12", "swatch": True})
        if len(labs) >= 8:
            break
    for n in sorted([n for n in names if n not in tnames and n in an], key=lambda n: -an[n][2])[:3]:
        text = (entries[n].get("koreanName") or n).replace(" (오른쪽)", "")
        if text not in used and an[n][2] > 600:
            used.add(text)
            labs.append({"x": an[n][0], "y": an[n][1], "text": text, "sub": "", "color": "#2B2F38"})
    lay = R.layout_labels(labs, SIZE, AREA, gap=46)
    svgt = R.svg(finish(cv, AREA), SIZE, lay, f"{item['koreanName']} ({item.get('_sub', '')})", f"{vko}에서 본 모습 · 금색 = 대상 뼈",
                 CREDIT, compass(v))
    url = save(f"media/plates/{item['id']}/hero.svg", svgt)
    return item["id"], vkey, 0, [base_media(id=f"pl-{item['id']}-hero", anatomyItemId=item["id"], type="plate", role="hero", url=url, viewAngle=vkey,
                                         labels=[l["text"] for l in lay], model=model_id, title=f"{item['koreanName']} 대표 도판",
                                         description=f"{vko}에서 본 {item['koreanName']} (금색)",
                                         altText=f"BodyParts3D 뼈 모델 렌더링. {item['koreanName']}이(가) 금색으로, 주변 뼈는 흐리게 표시됨")]


# ------------------------------------------------------------------ 근육 형상 없는 부위
def job_region(args):
    gid, items_by_id = args
    model_id, vkey, title, mesh_list, muscle_ids = REGION_GROUPS[gid]
    meshes, mapping, boxes = MODELS[model_id]
    entries = {e["meshId"]: e for e in mapping}
    if mesh_list is None:
        mesh_list = [e["meshId"] for e in mapping if e["category"] in ("bone", "cartilage") and e["meshId"] in meshes]
    mesh_list = [n for n in mesh_list if n in meshes]
    items = [(n, CART if entries[n]["category"] == "cartilage" else BONE) for n in mesh_list]
    d, up, vko = VIEWS[vkey]
    v = R.View(d, up)
    cv, ids, screen, _ = R.render(meshes, items, v, SIZE, AREA, fit_names=mesh_list)
    an = R.anchors(cv, ids, set(mesh_list))
    labs, used = [], set()
    for n in sorted(an, key=lambda n: -an[n][2]):
        text = (entries[n].get("koreanName") or n).replace(" (오른쪽)", "").replace(" (왼쪽)", "")
        if text in used or an[n][2] < 800:
            continue
        used.add(text)
        labs.append({"x": an[n][0], "y": an[n][1], "text": text, "sub": entries[n].get("englishName", ""), "color": "#2B2F38"})
        if len(labs) >= 9:
            break
    lay = R.layout_labels(labs, SIZE, AREA, gap=46)
    mus = " · ".join(items_by_id[m]["koreanName"] for m in muscle_ids if m in items_by_id)
    extra = ('<g><rect x="300" y="40" width="600" height="58" rx="10" fill="#FFF4E5" stroke="#E0A84E"/>'
             '<text x="600" y="64" font-size="17" font-weight="700" fill="#8A4B00" text-anchor="middle">근육 형상 없음 — 뼈대만 표시한 부위 도판</text>'
             f'<text x="600" y="86" font-size="13" fill="#8A4B00" text-anchor="middle">{R.esc(short(mus, 70))}</text></g>'
             '<text x="600" y="925" font-size="12" fill="#5B6170" text-anchor="middle">'
             '사용한 3D 모델(BodyParts3D)에 이 근육들의 메쉬가 없어 근육 모양을 그리지 않았습니다 · 기시·정지은 본문 텍스트 참고</text>')
    svgt = R.svg(finish(cv, AREA), SIZE, lay, title, f"{vko} · 근육 형상 없음", CREDIT, compass(v), extra)
    url = save(f"media/plates/region/{gid}.svg", svgt)
    out = []
    for m in muscle_ids:
        it = items_by_id.get(m)
        if not it:
            continue
        out.append(base_media(id=f"pl-{m}-region", anatomyItemId=m, type="plate", role="region", url=url, viewAngle=vkey,
                              provenance="model-render-region", labels=[l["text"] for l in lay], model=model_id,
                              title=f"{title} — {it['koreanName']} 형상 없음",
                              description=f"이 근육은 3D 모델에 형상이 없어, 위치를 이해하기 위한 주변 뼈대만 렌더링한 도판입니다",
                              altText=f"{title}. 근육은 그려져 있지 않고 뼈만 표시됨. 상단에 '근육 형상 없음' 안내"))
    return gid, vkey, 0, out


def run(job):
    kind, args = job
    try:
        return {"muscle": job_muscle, "bone": job_bone, "region": job_region}[kind](args)
    except Exception as e:  # 실패를 숨기지 않고 보고
        import traceback
        return (str(args[1]["id"] if isinstance(args[1], dict) else args[0]), "ERROR", 0, traceback.format_exc())


def main():
    load_models()
    items = json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))
    for it in items:  # 표시 이름 (구용어) + 병기용 '영어 / 신용어'
        it["_sub"] = TERMS.sub_name(it)
        it["koreanName"] = TERMS.item_name(it)
    by_id = {i["id"]: i for i in items}
    only = set(sys.argv[1:])
    jobs = []
    for it in items:
        if it["category"] not in ("muscle", "bone") or it["id"] in SKIP_DELTOID:
            continue
        if only and it["id"] not in only:
            continue
        pref = CHAPTER_MODEL.get(it["chapterId"])
        order = ([pref] if pref else []) + [m for m in MODELS if m != pref]
        model = next((m for m in order if m in MODELS and any(e.get("anatomyItemId") == it["id"] for e in MODELS[m][1])), None)
        if model:
            jobs.append((it["category"], (model, it)))
    for gid, g in REGION_GROUPS.items():
        if not only or only & set(g[4]):
            jobs.append(("region", (gid, by_id)))
    print(len(jobs), "jobs", flush=True)
    ctx = mp.get_context("fork")
    media, errors = [], []
    with ctx.Pool(max(1, (os.cpu_count() or 2) - 1)) as pool:
        for n, (iid, vkey, nt, res) in enumerate(pool.imap_unordered(run, jobs), 1):
            if vkey == "ERROR":
                errors.append((iid, res))
                print("ERROR", iid, res, flush=True)
                continue
            media += res
            print(f"[{n}/{len(jobs)}] {iid} view={vkey} bones={nt}", flush=True)
    mpath = os.path.join(ROOT, "data", "media.json")
    allm = json.load(open(mpath, encoding="utf-8"))
    new_ids = {m["id"] for m in media}
    allm = [m for m in allm if m["id"] not in new_ids]
    order = {i["id"]: k for k, i in enumerate(items)}
    allm += sorted(media, key=lambda m: (order.get(m["anatomyItemId"], 9999), m["id"]))
    json.dump(allm, open(mpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(len(media), "media registered;", len(errors), "errors")
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
