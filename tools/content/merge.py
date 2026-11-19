"""
tools/content/part*.py 의 항목을 data/items.json 에 병합합니다.
- 이미 있는 id 는 건너뜀(기존 자료 보존). 단, 아래 PATCH 는 기존 항목에 필드를 추가
- 챕터별 order 를 이어서 부여
- 새 출처를 data/sources.json 에 추가
실행: python3 tools/content/merge.py
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
import part1_trunk, part2_arm, part3_leg, part4_head  # noqa

SOURCES = [
    {"id": "os-7-2", "title": "OpenStax Anatomy and Physiology 2e — 7.2 The Skull", "publisher": "OpenStax (CC BY 4.0)", "url": "https://openstax.org/books/anatomy-and-physiology-2e/pages/7-2-the-skull", "note": ""},
    {"id": "os-7-3", "title": "OpenStax Anatomy and Physiology 2e — 7.3 The Vertebral Column", "publisher": "OpenStax (CC BY 4.0)", "url": "https://openstax.org/books/anatomy-and-physiology-2e/pages/7-3-the-vertebral-column", "note": ""},
    {"id": "os-8-4", "title": "OpenStax Anatomy and Physiology 2e — 8.4 The Pelvic Girdle and Pelvis", "publisher": "OpenStax (CC BY 4.0)", "url": "https://openstax.org/books/anatomy-and-physiology-2e/pages/8-4-the-pelvic-girdle-and-pelvis", "note": ""},
    {"id": "os-11-3", "title": "OpenStax Anatomy and Physiology 2e — 11.3 Axial Muscles of the Head, Neck, and Back", "publisher": "OpenStax (CC BY 4.0)", "url": "https://openstax.org/books/anatomy-and-physiology-2e/pages/11-3-axial-muscles-of-the-head-neck-and-back", "note": ""},
    {"id": "os-11-4", "title": "OpenStax Anatomy and Physiology 2e — 11.4 Axial Muscles of the Abdominal Wall and Thorax", "publisher": "OpenStax (CC BY 4.0)", "url": "https://openstax.org/books/anatomy-and-physiology-2e/pages/11-4-axial-muscles-of-the-abdominal-wall-and-thorax", "note": ""},
    {"id": "os-22-3", "title": "OpenStax Anatomy and Physiology 2e — 22.3 The Process of Breathing", "publisher": "OpenStax (CC BY 4.0)", "url": "https://openstax.org/books/anatomy-and-physiology-2e/pages/22-3-the-process-of-breathing", "note": ""},
]

PATCH = {
    "m-pectoralis-minor": {"relatedJoints": ["j-scapulothoracic"]},
    "m-serratus-anterior": {"relatedJoints": ["j-scapulothoracic"], "relatedMovements": ["mv-scapular-upward-rotation"]},
    "m-trapezius": {"relatedJoints": ["j-scapulothoracic"], "relatedMovements": ["mv-scapular-upward-rotation", "mv-neck-extension"]},
    "m-latissimus-dorsi": {"relatedMovements": ["mv-shoulder-extension"]},
    "m-teres-major": {"relatedMovements": ["mv-shoulder-extension"]},
    "b-humerus": {"relatedJoints": ["j-elbow"]},
    "b-femur": {"relatedJoints": ["j-hip"]},
    "b-tibia": {"relatedJoints": ["j-ankle"]},
    "j-hip": {"relatedMovements": ["mv-hip-flexion", "mv-hip-extension", "mv-hip-abduction"]},
    "j-knee": {"relatedMovements": ["mv-knee-flexion"]},
    "m-biceps-femoris": {"relatedMovements": ["mv-knee-flexion", "mv-hip-extension"]},
    "m-semitendinosus": {"relatedMovements": ["mv-knee-flexion", "mv-hip-extension"]},
    "m-rectus-femoris": {"relatedMovements": ["mv-hip-flexion"]},
    "m-sartorius": {"relatedMovements": ["mv-hip-flexion", "mv-knee-flexion"]},
}


def main():
    p = os.path.join(ROOT, "data", "items.json")
    items = json.load(open(p, encoding="utf-8"))
    have = {i["id"] for i in items}
    new = part1_trunk.ITEMS + part2_arm.ITEMS + part3_leg.ITEMS + part4_head.ITEMS
    dup = [i["id"] for i in new if [x["id"] for x in new].count(i["id"]) > 1]
    if dup:
        raise SystemExit(f"중복 id: {set(dup)}")
    order = {}
    for it in items:
        order[it["chapterId"]] = max(order.get(it["chapterId"], 0), it.get("order", 0))
    added = 0
    for it in new:
        if it["id"] in have:
            continue
        order[it["chapterId"]] = order.get(it["chapterId"], 0) + 1
        it["order"] = order[it["chapterId"]]
        items.append(it)
        added += 1
    byid = {i["id"]: i for i in items}
    for iid, fields in PATCH.items():
        for k, vals in fields.items():
            cur = byid[iid].setdefault(k, [])
            for v in vals:
                if v not in cur:
                    cur.append(v)
    json.dump(items, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    sp = os.path.join(ROOT, "data", "sources.json")
    src = json.load(open(sp, encoding="utf-8"))
    ids = {s["id"] for s in src}
    src += [s for s in SOURCES if s["id"] not in ids]
    json.dump(src, open(sp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"added {added}, total {len(items)}")


if __name__ == "__main__":
    main()
