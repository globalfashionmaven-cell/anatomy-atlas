"""
media/ 폴더의 자체 제작 도식을 data/media.json 매니페스트로 기록합니다.
새 이미지를 추가할 때는 이 스크립트를 수정하거나 data/media.json에 직접 항목을 추가하세요.

실행: python3 tools/make_media_manifest.py
"""
import json
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
LICENSE = "자체 제작 개념 도식 (프로젝트 내 자유 사용)"
SCHEMATIC = True

media = []


def add(**kw):
    kw.setdefault("license", LICENSE)
    kw.setdefault("schematic", SCHEMATIC)
    kw.setdefault("source", "자체 제작 (tools/generate_media.py) — 외부 이미지 사용 안 함")
    kw.setdefault("provenance", "schematic")
    kw.setdefault("reviewStatus", "needs-review")
    media.append(kw)


# 해부학적 자세 — 다각도
for angle, label in (("front", "앞면"), ("left", "왼쪽 옆면"), ("back", "뒷면")):
    add(
        id=f"md-anatpos-{angle}", anatomyItemId="c-anatomical-position", type="image",
        title=f"해부학적 자세 · {label}", description="해부학적 자세의 개념 도식",
        url=f"media/basics/anatomical-position/{angle}.svg", viewAngle=angle,
        altText=f"해부학적 자세를 {label}에서 본 단순화된 인체 도식",
    )

add(
    id="md-planes", anatomyItemId="c-planes", type="image", title="해부학적 면",
    description="시상면·관상면·수평면 개념 도식", url="media/basics/planes.svg", viewAngle="front",
    altText="인체 도식 위에 시상면, 관상면, 수평면을 겹쳐 표시한 그림",
)

# 조직 층 — 분리된 투명 레이어
for order, (layer, label) in enumerate(
    (("bone", "뼈"), ("muscle", "근막 · 근육"), ("subcutaneous", "피하조직"), ("skin", "피부"))
):
    add(
        id=f"md-tissue-{layer}", anatomyItemId="c-tissue-layers", type="layer",
        title=label, description="팔다리 가로단면의 층 구조 개념 도식",
        url=f"media/basics/tissue-layers/{layer}.svg", viewAngle="cross-section",
        layer=layer, layerLabel=label, layerOrder=order,
        altText=f"가로단면 도식의 {label} 층",
    )

# 프레임 시퀀스
for i, a in enumerate(range(0, 181, 15)):
    add(
        id=f"md-sh-abd-{i:02d}", anatomyItemId="mv-shoulder-abduction", type="frame",
        title=f"어깨관절 벌림 {a}°", description=("0–90°: 위팔뼈가 몸통에서 멀어짐" if a <= 90 else "90° 이후: 어깨뼈 위쪽돌림의 기여 증가"),
        url=f"media/movements/shoulder-abduction/f{i:02d}.svg", viewAngle="front",
        frameOrder=i, frameLabel=f"{a}°", altText=f"정면에서 본 팔을 {a}도 벌린 단순화 도식",
    )
for i, k in enumerate(range(90, -1, -10)):
    add(
        id=f"md-knee-ext-{i:02d}", anatomyItemId="mv-knee-extension", type="frame",
        title=f"무릎 굽힘 {k}°", description="앉은 자세 무릎 폄",
        url=f"media/movements/knee-extension/f{i:02d}.svg", viewAngle="left",
        frameOrder=i, frameLabel=f"{k}°", altText=f"옆에서 본 무릎 굽힘 {k}도 자세의 단순화 도식",
    )

# 다른 도구(예: tools/make_deltoid_plates.py)가 등록한 항목은 보존하고 이 스크립트의 항목(md-*)만 교체
path = os.path.join(ROOT, "data", "media.json")
others = [m for m in json.load(open(path, encoding="utf-8")) if not m["id"].startswith("md-")] if os.path.exists(path) else []
with open(path, "w", encoding="utf-8") as f:
    json.dump(media + others, f, ensure_ascii=False, indent=2)
print(len(media), "media entries")
