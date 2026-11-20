"""data/terms.json 표시 규칙의 Python 판 (assets/js/terms.js 와 같은 규칙) — 도판 생성기에서 사용"""
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
T = json.load(open(os.path.join(ROOT, "data", "terms.json"), encoding="utf-8"))
_pairs = sorted(T["movementTerms"], key=lambda p: -len(p[0]))
_map = dict((a, b) for a, b in _pairs)
_rx = re.compile(r"(?<![^\s·(,/~])(" + "|".join(re.escape(a) for a, _ in _pairs) + r")(?=$|[\s·),/~])")
ORIGIN, INSERTION = T["attach"]["origin"], T["attach"]["insertion"]


PROTECT = T.get("protect", [])
OVERRIDES = T.get("itemOverrides", {})


def move(s):
    out = s or ""
    for i, p in enumerate(PROTECT):
        out = out.replace(p, f"\x01{i}\x02")
    out = _rx.sub(lambda m: _map.get(m.group(1), m.group(1)), out)
    for i, p in enumerate(PROTECT):
        out = out.replace(f"\x01{i}\x02", p)
    return out


def item_name(it):
    if it["id"] in OVERRIDES:
        return OVERRIDES[it["id"]]
    if it["category"] in ("muscle", "bone") and it.get("oldKoreanName"):
        return it["oldKoreanName"][0]
    if it["category"] == "movement":
        return move(it["koreanName"])
    return it["koreanName"]


def sub_name(it):
    main = item_name(it)
    parts = [it.get("englishName", "")]
    if main != it["koreanName"]:
        parts.append(it["koreanName"])
    return " / ".join(p for p in parts if p)


def mesh_name(entry, item):
    if not item:
        return entry.get("koreanName", entry["meshId"])
    part = T.get("partLabels", {}).get(entry["meshId"])
    main = item_name(item)
    if part:
        return f"{main} {part}"
    if entry.get("mappingRelation") == "same" and item["category"] in ("muscle", "bone"):
        return main
    if item["koreanName"] != main and item["koreanName"] in entry.get("koreanName", ""):
        return entry["koreanName"].replace(item["koreanName"], main)
    return entry.get("koreanName", "")
