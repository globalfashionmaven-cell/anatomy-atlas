"""
정적 자동 검사 (브라우저 없이) — 데이터·이미지·3D 모델·동작 데이터의 무결성

사용법: python3 tools/qa.py [--out docs/qa-static.md]
종료 코드: 오류가 하나라도 있으면 1

검사 항목
  데이터    JSON 구문, 항목 ID 중복, 챕터 소속, 교차 참조(m-/b-/j-/mv-/c-), 출처 ID 존재, 필수 필드
  근육      필수 정보(이는곳·닿는곳·신경·작용·협력근·길항근·관련 관절) — 해당 없음(notApplicable) 사유 허용
            금지 조합: 넓은등근을 어깨뼈 위쪽돌림근으로 표시
  미디어    파일 존재, 0바이트 아님, SVG XML 구문, 내장 PNG 시그니처, 대체 텍스트·출처·라이선스·검증 상태,
            '검증 완료' 표기 금지, 연결 항목 존재
  3D 모델   GLB 매직·버전, 매핑 파일의 meshId 가 GLB 노드에 존재, 연결 항목 존재, 라이선스 표기
  3D 동작   모델 존재, 움직임 항목 존재, 분절 메쉬 존재, 곡선 t∈[0,1] 오름차순·숫자, 근육 역할 참조,
            가상 작용선 기준 메쉬 존재, 단계 설명(0~100%) 존재
"""
import json
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
REQ_MUSCLE = ["origin", "insertion", "innervation", "action", "synergists", "antagonists", "relatedJoints"]
errors, warns, stats = [], [], {}


def load(p):
    try:
        return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        errors.append(f"JSON 구문 오류: {p}: {e}")
        return None


def glb_nodes(path):
    data = open(path, "rb").read()
    if data[:4] != b"glTF":
        errors.append(f"GLB 매직 아님: {path}")
        return set()
    ver = struct.unpack_from("<I", data, 4)[0]
    if ver != 2:
        errors.append(f"GLB 버전 {ver}: {path}")
    jlen = struct.unpack_from("<I", data, 12)[0]
    g = json.loads(data[20:20 + jlen])
    return {n.get("name") for n in g.get("nodes", [])}


def refs_of(it):
    out = it.get("relatedBones", []) + it.get("relatedJoints", []) + it.get("relatedMovements", []) + it.get("relatedItems", []) \
        + it.get("targetMuscles", []) + it.get("assistingMuscles", []) + it.get("antagonistMuscles", []) + it.get("stabilizerMuscles", [])
    out += [s["ref"] for s in it.get("synergists", []) + it.get("antagonists", []) if isinstance(s, dict)]
    return out


def mesh_refs(spec):
    """동작 기준점 스펙에서 참조 메쉬 이름 수집"""
    out = []
    if isinstance(spec, dict):
        for k in ("mesh", "a", "b"):
            v = spec.get(k)
            if isinstance(v, str):
                out.append(v)
            elif isinstance(v, dict):
                out += mesh_refs(v)
    return out


def main():
    chapters = load("data/chapters.json") or []
    items = load("data/items.json") or []
    media = load("data/media.json") or []
    sources = load("data/sources.json") or []
    reg = load("data/models3d.json") or {"models": []}
    mot = load("data/motions3d.json") or {"motions": []}
    motions = mot["motions"] if isinstance(mot, dict) else mot
    load("data/glossary.json")

    # ---------------- 데이터
    ids = Counter(i["id"] for i in items)
    for k, c in ids.items():
        if c > 1:
            errors.append(f"항목 ID 중복: {k} ×{c}")
    known = set(ids)
    chap_ids = {c["id"] for c in chapters}
    src_ids = {s["id"] for s in sources}
    for it in items:
        for f in ("id", "chapterId", "category", "koreanName", "englishName"):
            if not it.get(f):
                errors.append(f"{it.get('id')}: 필수 필드 없음 {f}")
        if it.get("chapterId") not in chap_ids:
            errors.append(f"{it['id']}: 없는 챕터 {it.get('chapterId')}")
        for r in refs_of(it):
            if isinstance(r, str) and r.startswith(("m-", "b-", "j-", "mv-", "c-")) and r not in known:
                errors.append(f"{it['id']}: 잘못된 참조 {r}")
        for s in it.get("sources", []):
            sid = s if isinstance(s, str) else s.get("id")
            if sid not in src_ids:
                errors.append(f"{it['id']}: 없는 출처 {sid}")
        if not it.get("sources"):
            warns.append(f"{it['id']}: 출처 없음")
        if it.get("reviewStatus") not in (None, "needs-review", "draft"):
            errors.append(f"{it['id']}: 검증 상태 '{it.get('reviewStatus')}' — 전문가 검수 전이므로 needs-review 여야 함")
        if it["category"] == "muscle":
            na = it.get("notApplicable", {})
            miss = [f for f in REQ_MUSCLE if not it.get(f) and f not in na]
            if miss:
                errors.append(f"{it['id']}: 근육 필수 정보 누락 {miss}")
    txt = json.dumps(items, ensure_ascii=False)
    for bad in ("검증 완료", "검수 완료", "전문가 인증"):
        if bad in txt:
            errors.append(f"items.json 에 금지 표현 '{bad}'")
    lat = next((i for i in items if i["id"] == "m-latissimus-dorsi"), None)
    if lat and re.search(r"위쪽돌림", " ".join(lat.get("action", [])) if isinstance(lat.get("action"), list) else str(lat.get("action"))):
        errors.append("넓은등근 작용에 '어깨뼈 위쪽돌림'이 들어 있음")
    for mv in items:
        if mv["category"] == "movement" and "m-latissimus-dorsi" in mv.get("targetMuscles", []) + mv.get("assistingMuscles", []) \
                and "upward" in mv["id"]:
            errors.append(f"{mv['id']}: 넓은등근이 위쪽돌림 주동/협력으로 지정됨")
    stats["items"] = len(items)
    stats["muscles"] = sum(1 for i in items if i["category"] == "muscle")

    # ---------------- 미디어
    mtxt_bad = 0
    svg_ok = 0
    seen_urls = set()
    for m in media:
        mid = m.get("id")
        if m.get("anatomyItemId") not in known:
            errors.append(f"미디어 {mid}: 없는 항목 {m.get('anatomyItemId')}")
        for f in ("altText", "license", "source", "reviewStatus"):
            if not m.get(f):
                errors.append(f"미디어 {mid}: {f} 없음")
        if m.get("reviewStatus") not in ("needs-review",):
            errors.append(f"미디어 {mid}: 검증 상태 '{m.get('reviewStatus')}'")
        p = os.path.join(ROOT, m.get("url", ""))
        if not os.path.isfile(p):
            errors.append(f"미디어 {mid}: 파일 없음 {m.get('url')}")
            continue
        if os.path.getsize(p) == 0:
            errors.append(f"미디어 {mid}: 0바이트")
            continue
        if m["url"] in seen_urls:
            continue
        seen_urls.add(m["url"])
        if p.endswith(".svg"):
            try:
                root = ET.parse(p).getroot()
                svg_ok += 1
                for img in root.iter("{http://www.w3.org/2000/svg}image"):
                    href = img.get("href") or img.get("{http://www.w3.org/1999/xlink}href") or ""
                    if href.startswith("data:image/png;base64,"):
                        import base64
                        if base64.b64decode(href[22:30] + "==")[:4] != b"\x89PNG":
                            errors.append(f"미디어 {mid}: 내장 PNG 시그니처 오류")
            except ET.ParseError as e:
                errors.append(f"미디어 {mid}: SVG 구문 오류 {e}")
        body = open(p, "rb").read()
        if b"\xea\xb2\x80\xec\xa6\x9d \xec\x99\x84\xeb\xa3\x8c" in body:  # '검증 완료'
            mtxt_bad += 1
            errors.append(f"미디어 {mid}: 파일에 '검증 완료' 표기")
    stats["media"] = len(media)
    stats["media_files"] = len(seen_urls)
    stats["svg_parsed"] = svg_ok

    # ---------------- 3D 모델
    model_nodes = {}
    for mdl in reg["models"]:
        path = os.path.join(ROOT, mdl["url"])
        if not os.path.isfile(path):
            errors.append(f"모델 {mdl['id']}: 파일 없음 {mdl['url']}")
            continue
        nodes = glb_nodes(path)
        model_nodes[mdl["id"]] = nodes
        if not (mdl.get("source") or {}).get("license"):
            errors.append(f"모델 {mdl['id']}: 라이선스 표기 없음")
        mp = load(mdl["mapping"])
        if not mp:
            continue
        for e in mp["meshes"]:
            if e["meshId"] not in nodes:
                errors.append(f"모델 {mdl['id']}: 매핑 meshId '{e['meshId']}' 가 GLB에 없음")
            if e.get("anatomyItemId") and e["anatomyItemId"] not in known:
                errors.append(f"모델 {mdl['id']}: 메쉬 {e['meshId']} → 없는 항목 {e['anatomyItemId']}")
        for n in nodes - {e["meshId"] for e in mp["meshes"]}:
            warns.append(f"모델 {mdl['id']}: GLB 노드 '{n}' 매핑 없음")
    stats["models"] = len(model_nodes)

    # ---------------- 3D 동작
    mids = Counter(x["id"] for x in motions)
    for k, c in mids.items():
        if c > 1:
            errors.append(f"동작 ID 중복 {k}")
    for x in motions:
        tag = f"동작 {x['id']}"
        nodes = model_nodes.get(x["model"])
        if nodes is None:
            errors.append(f"{tag}: 없는 모델 {x['model']}")
            continue
        if x.get("movementItemId") not in known:
            errors.append(f"{tag}: 없는 움직임 항목 {x.get('movementItemId')}")
        segs = {s["id"] for s in x.get("segments", [])}
        for s in x.get("segments", []):
            for mname in s.get("meshes", []):
                if mname not in nodes:
                    errors.append(f"{tag}: 분절 {s['id']} 메쉬 '{mname}' 없음")
            if s.get("parent") and s["parent"] not in segs:
                errors.append(f"{tag}: 분절 {s['id']} 부모 '{s['parent']}' 없음")
            for mname in mesh_refs(s.get("pivot")):
                if mname not in nodes:
                    errors.append(f"{tag}: 분절 {s['id']} 회전중심 기준 메쉬 '{mname}' 없음")
            for tr in s.get("rotations", []) + s.get("translations", []):
                for mname in mesh_refs(tr.get("axis")):
                    if mname not in nodes:
                        errors.append(f"{tag}: 회전축 기준 메쉬 '{mname}' 없음")
                cur = tr.get("curve", [])
                ts = [c[0] for c in cur]
                if not cur or ts != sorted(ts) or ts[0] != 0 or ts[-1] != 1 or not all(isinstance(c[1], (int, float)) for c in cur):
                    errors.append(f"{tag}: 곡선 형식 오류 {cur}")
        for vm in x.get("virtualMuscles", []):
            for mname in mesh_refs(vm.get("from")) + mesh_refs(vm.get("to")):
                if mname not in nodes:
                    errors.append(f"{tag}: 가상 작용선 '{vm.get('label')}' 기준 메쉬 '{mname}' 없음")
            if vm.get("itemId") and vm["itemId"] not in known:
                errors.append(f"{tag}: 가상 작용선 항목 {vm['itemId']} 없음")
        for rid in list(x.get("roles", {})):
            if rid not in known:
                errors.append(f"{tag}: 역할 지정 항목 {rid} 없음")
        for mname in x.get("meshRoles", {}):
            if mname not in nodes:
                errors.append(f"{tag}: meshRoles 메쉬 '{mname}' 없음")
        ats = [p["at"] for p in x.get("phases", [])]
        if not ats or ats[0] != 0 or ats[-1] != 100:
            errors.append(f"{tag}: 단계 설명이 0%~100%를 덮지 않음 {ats}")
        if not x.get("note"):
            errors.append(f"{tag}: 단순화 고지(note) 없음")
        for s in x.get("sources", []):
            if s not in src_ids:
                errors.append(f"{tag}: 없는 출처 {s}")
    stats["motions"] = len(motions)

    # ---------------- V5: 용어표 · 층별 해부 · 근섬유 · 각도 슬라이더
    terms = load("data/terms.json") or {}
    for pair in terms.get("movementTerms", []):
        if not (isinstance(pair, list) and len(pair) == 2 and all(isinstance(x, str) and x for x in pair)):
            errors.append(f"terms.json: 잘못된 용어 쌍 {pair}")
    for m in [x for x in items if x["category"] in ("muscle", "bone")]:
        if not m.get("oldKoreanName"):
            warns.append(f"{m['id']}: 구용어(oldKoreanName) 없음 → 신용어로 표시")
    for mdl in reg["models"]:
        nodes = model_nodes.get(mdl["id"], set())
        if mdl.get("dissection"):
            dz = load(mdl["dissection"])
            if not dz:
                continue
            for vk, vw in dz["views"].items():
                if not vw["steps"]:
                    errors.append(f"해부 {mdl['id']}/{vk}: 단계 없음")
                for st in vw["steps"]:
                    for m_ in st["remove"] + st["exposes"]:
                        if m_ not in nodes:
                            errors.append(f"해부 {mdl['id']}: 단계 메쉬 '{m_}' 가 GLB에 없음")
                for iid, ap in vw["autoPaths"].items():
                    if iid not in known:
                        errors.append(f"해부 {mdl['id']}: 자동 탐색 항목 {iid} 없음")
                    for m_ in ap["path"] + ap.get("target", []) + ap.get("proxyBones", []):
                        if m_ not in nodes:
                            errors.append(f"해부 {mdl['id']}: 경로 메쉬 '{m_}' 없음")
                    flat = [m_ for st in ap["steps"] for m_ in st]
                    if sorted(flat) != sorted(ap["path"]):
                        errors.append(f"해부 {mdl['id']}: {iid} 경로와 단계가 다름 (빠진 메쉬 {sorted(set(ap['path']) - set(flat))})")
                    if ap.get("proxy") and not ap.get("note"):
                        errors.append(f"해부 {mdl['id']}: {iid} 대리 영역 안내문 없음")
            for m_, rf in dz["reflect"].items():
                if m_ not in nodes:
                    errors.append(f"해부 {mdl['id']}: 젖히기 메쉬 '{m_}' 없음")
                if abs(sum(a * a for a in rf["axis"]) - 1) > 1e-2 or rf["span"] <= 0:
                    errors.append(f"해부 {mdl['id']}: '{m_}' 경첩 정의 오류")
            for iid in mdl.get("autoDissect", []):
                if iid not in dz["views"]["back"]["autoPaths"] or not dz["views"]["back"]["autoPaths"][iid]["path"]:
                    errors.append(f"모델 {mdl['id']}: autoDissect {iid} 에 경로 없음")
            stats["dissection_steps"] = len(dz["views"]["back"]["steps"])
        if mdl.get("fibers"):
            fb = load(mdl["fibers"])
            if not fb:
                continue
            for m_, f in fb["muscles"].items():
                if m_ not in nodes:
                    errors.append(f"근섬유 {mdl['id']}: 메쉬 '{m_}' 없음")
                if f.get("item") not in known:
                    errors.append(f"근섬유 {mdl['id']}: 항목 {f.get('item')} 없음")
                for g in f["glyphs"]:
                    if len(g) != 9 or abs(sum(x * x for x in g[3:6]) - 1) > 0.05:
                        errors.append(f"근섬유 {mdl['id']}: '{m_}' 방향 벡터 오류")
                        break
            stats[f"fibers_{mdl['id']}"] = len(fb["muscles"])
    for x in motions:
        sl = x.get("angleSlider")
        if sl:
            if sl["seg"] not in {s_["id"] for s_ in x["segments"]}:
                errors.append(f"동작 {x['id']}: 각도 슬라이더 분절 {sl['seg']} 없음")
            rom = sl.get("rom", {})
            for k in ("reference", "source", "position", "axis", "plane", "active", "compound", "reviewStatus"):
                if not rom.get(k):
                    errors.append(f"동작 {x['id']}: 가동범위 메타데이터 '{k}' 없음")

    # ---------------- 정적 파일 참조 (index.html → css/js)
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    for ref in re.findall(r'(?:src|href)="([^"#:]+)"', html):
        if not os.path.exists(os.path.join(ROOT, ref.split("?")[0])):
            errors.append(f"index.html: 없는 파일 {ref}")
    for dp, _, fs in os.walk(os.path.join(ROOT, "assets", "js")):
        for f in fs:
            if not f.endswith(".js"):
                continue
            src = open(os.path.join(dp, f), encoding="utf-8").read()
            for ref in re.findall(r"from '(\.[^']+)'", src):
                if not os.path.exists(os.path.normpath(os.path.join(dp, ref))):
                    errors.append(f"{os.path.relpath(os.path.join(dp, f), ROOT)}: import 대상 없음 {ref}")

    lines = ["# 정적 자동 검사 결과 (`python3 tools/qa.py`)", "",
             "| 항목 | 값 |", "|---|---|"] + [f"| {k} | {v} |" for k, v in stats.items()] + \
            [f"| 오류 | {len(errors)} |", f"| 경고 | {len(warns)} |", "", "## 오류", ""] + \
            ([f"- {e}" for e in errors] or ["없음"]) + ["", "## 경고 (참고)", ""] + ([f"- {w}" for w in warns[:80]] or ["없음"])
    text = "\n".join(lines) + "\n"
    if "--out" in sys.argv:
        open(os.path.join(ROOT, sys.argv[sys.argv.index("--out") + 1]), "w", encoding="utf-8").write(text)
    print(text if "--quiet" not in sys.argv else f"errors={len(errors)} warns={len(warns)} {stats}")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
