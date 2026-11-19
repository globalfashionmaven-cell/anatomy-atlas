"""
해부학 항목 작성 도우미 — 모든 근육·뼈·관절·움직임·개념을 같은 필드 구조로 만듭니다.
(data/items.json 의 기존 스키마와 호환. 새 필드: muscleGroup, bloodSupply, clinicalNotes)

모든 항목은 reviewStatus = "needs-review"(전문가 검수 필요)로 만듭니다.
"""


def _refs(xs):
    out = []
    for x in xs or ():
        if isinstance(x, (tuple, list)):
            out.append({"ref": x[0], "note": x[1]})
        else:
            out.append({"ref": x, "note": ""})
    return out


def _src(src):
    return [{"id": s} for s in src]


def M(id, ch, ko, old, en, la, *, group, layer, pos, origin, insertion, nerve, action, kw, summary,
      syn=(), ant=(), bones=(), joints=(), moves=(), tags=(), src=(), role="", contraction="",
      clinical="", blood="", items=()):
    return {
        "id": id, "chapterId": ch, "category": "muscle",
        "koreanName": ko, "oldKoreanName": list(old), "englishName": en, "latinName": la,
        "muscleGroup": group, "summary": summary, "anatomicalPosition": pos, "layer": layer,
        "origin": list(origin), "insertion": list(insertion), "innervation": nerve,
        "action": list(action), "actionKeywords": list(kw),
        "contraction": contraction, "roleInMovement": role,
        "synergists": _refs(syn), "antagonists": _refs(ant),
        "relatedBones": list(bones), "relatedJoints": list(joints), "relatedMovements": list(moves),
        "relatedItems": list(items), "bloodSupply": blood, "clinicalNotes": clinical,
        "tags": list(tags), "sources": _src(src), "reviewStatus": "needs-review",
    }


def B(id, ch, ko, old, en, la, *, summary, pos, features, bones=(), joints=(), tags=(), src=(), items=(), clinical=""):
    return {
        "id": id, "chapterId": ch, "category": "bone",
        "koreanName": ko, "oldKoreanName": list(old), "englishName": en, "latinName": la,
        "summary": summary, "anatomicalPosition": pos, "features": list(features),
        "relatedBones": list(bones), "relatedJoints": list(joints), "relatedItems": list(items),
        "clinicalNotes": clinical, "tags": list(tags), "sources": _src(src), "reviewStatus": "needs-review",
    }


def J(id, ch, ko, old, en, la, *, summary, jtype, art, moves_allowed, stab, bones=(), moves=(), tags=(), src=(),
      items=(), desc="", kinematics=""):
    return {
        "id": id, "chapterId": ch, "category": "joint",
        "koreanName": ko, "oldKoreanName": list(old), "englishName": en, "latinName": la,
        "summary": summary, "description": desc, "jointType": jtype, "articulatingBones": list(art),
        "movementsAllowed": list(moves_allowed), "stabilizers": stab, "kinematics": kinematics,
        "relatedBones": list(bones), "relatedMovements": list(moves), "relatedItems": list(items),
        "tags": list(tags), "sources": _src(src), "reviewStatus": "needs-review",
    }


def MV(id, ch, ko, old, en, *, summary, mtype, target, assist=(), antag=(), stab=(), joints=(), steps=(), tags=(),
       src=(), items=()):
    return {
        "id": id, "chapterId": ch, "category": "movement",
        "koreanName": ko, "oldKoreanName": list(old), "englishName": en, "latinName": "",
        "summary": summary, "movementType": mtype,
        "targetMuscles": list(target), "assistingMuscles": list(assist), "antagonistMuscles": list(antag),
        "stabilizerMuscles": list(stab), "relatedJoints": list(joints),
        "steps": [{"title": t, "text": x} for t, x in steps],
        "relatedItems": list(items), "tags": list(tags), "sources": _src(src), "reviewStatus": "needs-review",
    }


def C(id, ch, ko, old, en, *, summary, desc, points=(), items=(), tags=(), src=(), clinical=""):
    return {
        "id": id, "chapterId": ch, "category": "concept",
        "koreanName": ko, "oldKoreanName": list(old), "englishName": en, "latinName": "",
        "summary": summary, "description": desc, "keyPoints": list(points), "relatedItems": list(items),
        "clinicalNotes": clinical, "tags": list(tags), "sources": _src(src), "reviewStatus": "needs-review",
    }
