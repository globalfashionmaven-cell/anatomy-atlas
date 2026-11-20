"""
3D 움직임 정의 생성기 → data/motions3d.json

각 동작:
  id, model, movementItemId(근육 역할의 출처), title, load(부하 조건: gravity|resisted|none),
  segments: 함께 움직이는 뼈 묶음 (parent 로 연쇄), pivot(관절 중심 계산법), rotations/translations(진행률 t→각도/이동량),
  angles: 화면에 보일 관절각, phases: 0·25·50·75·100% 해설과 관절면 운동학, note: 단순화 범위, sources.
좌표: 모델 공간 (+X 대상자의 왼쪽, +Y 위, +Z 앞), 단위 cm.
실행: python3 tools/make_motions.py
"""
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
X, NX, Y, NY, Z, NZ = [1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]


def fixed(v):
    return {"type": "fixed", "v": v}


def contact(a, b, tol=0.4):
    return {"type": "contact", "a": a, "b": b, "tol": tol}


def rot(axis, *pts):
    return {"axis": axis, "curve": [list(p) for p in pts]}


def seg(id, meshes, pivot, rotations=(), parent=None, translations=()):
    return {"id": id, "meshes": meshes, "parent": parent, "pivot": pivot, "rotations": list(rotations), "translations": list(translations)}


def ph(at, title, text, kin=""):
    return {"at": at, "title": title, "text": text, "kinematics": kin}


COMMON_NOTE = ("교육용 단순화 시뮬레이션: 뼈는 실제 BodyParts3D 메쉬를 관절 중심(형상에서 계산)에서 강체 회전·이동합니다. "
               "관절을 가로지르는 근육은 변형 데이터가 없어 메쉬 대신 이는곳→닿는곳 작용선으로 표시하며, 길이 변화는 작용선 길이로 계산한 추정치입니다. "
               "수축 유형은 동작의 부하 조건을 가정해 판정한 교육용 표시입니다.")

# ------------------------------------------------------------------ 어깨 (shoulder-right)
SH_PIVOTS = {
    "sc": contact("clavicle", "manubrium", 0.5),
    "ac": contact("clavicle", "scapula", 0.4),
    "gh": {"type": "sphere", "mesh": "humerus", "end": "top", "frac": 0.10},
}


def shoulder(id, item, title, hum_rots, scap=None, clav=None, load="gravity", phases=(), angles=None, extra_note=""):
    segs = [
        # 빗장뼈 올림: 오른쪽 빗장뼈의 가쪽 끝이 올라가는 방향 = -Z 축 기준 양의 회전
        # (V5 검증에서 발견: 이전에는 +Z 축이라 '올림' 값이 실제로는 가쪽 끝을 내리고 있었음 → 수정)
        seg("clavicle", ["clavicle"], SH_PIVOTS["sc"], [rot(NZ, *(clav or [(0, 0), (1, 0)]))]),
        seg("scapula", ["scapula"], SH_PIVOTS["ac"], [rot(NZ, *(scap or [(0, 0), (1, 0)]))], parent="clavicle"),
        seg("humerus", ["humerus"], SH_PIVOTS["gh"], hum_rots, parent="scapula"),
    ]
    return {"id": id, "model": "shoulder-right", "movementItemId": item, "title": title, "load": load, "duration": 3.5,
            "segments": segs, "angles": angles or [{"label": "어깨관절(오목위팔)", "seg": "humerus"}, {"label": "어깨뼈 위쪽돌림", "seg": "scapula"}, {"label": "빗장뼈 올림", "seg": "clavicle"}],
            "phases": list(phases), "note": COMMON_NOTE + " 어깨뼈·빗장뼈 움직임은 위팔뼈 각도에 연동한 교육용 근사이며(전체 범위에서 위팔뼈:어깨뼈 ≈ 2:1), 실제로는 구간과 개인에 따라 다릅니다. " + extra_note,
            "sources": ["os-9-5", "os-11-5"]}


ABD_SLIDER = {"label": "위팔-가슴 거상각 (어깨 복합체 전체)", "max": 180, "seg": "humerus", "mesh": "humerus",
              "rom": {"reference": "어깨 복합체 외전 약 180° (교과서 참고값)", "source": "os-9-5", "position": "선 자세, 팔 옆에 붙인 자세에서 시작",
                      "axis": "앞뒤 방향 축 (관상면 운동)", "plane": "관상면", "active": "능동 운동 가정", "compound": "복합 관절 (오목위팔 + 어깨가슴 + 복장빗장·봉우리빗장)",
                      "reviewStatus": "needs-review", "note": "개인·나이·측정 방법에 따라 다르며 모든 사람의 정상 범위가 같지 않습니다. 화면의 각도는 3D 모델에서 위팔뼈 장축이 처음 위치에서 기운 각을 직접 측정한 값입니다."}}

MOTIONS = [
    shoulder("sh-abduction", "mv-shoulder-abduction", "어깨 · 벌림 (Abduction)",
             # V5 JOINT-001: 어깨 복합체 전체 0→약 180° (t = 목표 위팔-가슴 거상각 / 180, 실제 각도는 화면에서 형상으로 측정)
             # 구간별 비율이 다름: 초기(약 30°까지)는 대부분 오목위팔관절, 이후 어깨뼈 위쪽돌림 비중 증가 — 전 범위 고정 2:1 아님
             [rot(NZ, (0, 0), (1 / 6, 28), (2 / 6, 48), (3 / 6, 65), (4 / 6, 82), (5 / 6, 100), (1, 120))],
             scap=[(0, 0), (1 / 6, 2), (2 / 6, 10), (3 / 6, 20), (4 / 6, 30), (5 / 6, 38), (1, 45)],
             clav=[(0, 0), (1 / 6, 1), (2 / 6, 4), (3 / 6, 8), (4 / 6, 11), (5 / 6, 13), (1, 15)],
             phases=[ph(0, "시작 자세", "팔이 몸통 옆. 어깨세모근·가시위근은 이완, 돌림근띠는 위팔뼈머리를 접시오목에 붙잡고 있습니다.", "위팔뼈머리는 접시오목 중앙에 놓입니다."),
                     ph(15, "벌림 초기", "어깨세모근 중간섬유와 가시위근이 단축성 수축으로 위팔뼈를 들어 올립니다. 이 구간은 주로 오목위팔관절에서 움직입니다 (어깨뼈 거의 고정).",
                        "볼록한 위팔뼈머리가 오목한 접시오목 위에서 위로 굴러가는(roll) 동안, 아래로 미끄러져(glide) 머리가 봉우리 쪽으로 올라붙지 않습니다. 돌림근띠가 이 아래 미끄러짐을 돕습니다."),
                     ph(40, "벌림 진행", "앞톱니근과 등세모근 위·아래섬유가 짝힘으로 어깨뼈를 위쪽으로 돌리기 시작합니다. 빗장뼈도 올라갑니다. 넓은등근은 이 위쪽돌림의 주동근이 아닙니다 (모음·폄 근육).",
                        "어깨가슴관절에서 어깨뼈가 가슴우리 위를 미끄러지며 돕니다. 복장빗장관절에서 빗장뼈가 올라가고 뒤로 돕니다(뒤돌림은 이 시뮬레이션에서 생략)."),
                     ph(75, "벌림 후반", "어깨세모근이 계속 작용하고, 어깨뼈 위쪽돌림의 비중이 커집니다. 실제로는 큰결절이 봉우리 아래에 걸리지 않도록 위팔뼈 가쪽돌림이 함께 일어나는 경우가 많습니다 (이 시뮬레이션에서는 생략).",
                        "위팔뼈머리의 아래 미끄러짐과 어깨뼈 위쪽돌림·뒤기울임이 함께 공간을 확보합니다."),
                     ph(100, "최종 자세", "위팔뼈-가슴 거상각 약 180°는 어깨 복합체 전체(오목위팔관절 + 어깨뼈 위쪽돌림 + 빗장뼈 올림)의 참고 위치이며, 오목위팔관절 단독 가동범위가 아닙니다. 내릴 때는 같은 근육들이 신장성 수축으로 속도를 조절합니다 (역재생).", "")]),
    shoulder("sh-flexion", "mv-shoulder-flexion", "어깨 · 굽힘 (Flexion)",
             [rot(NX, (0, 0), (1, 110))], scap=[(0, 0), (0.2, 0), (1, 45)], clav=[(0, 0), (0.2, 0), (1, 12)],
             phases=[ph(0, "시작 자세", "팔이 몸통 옆에 있습니다."),
                     ph(25, "굽힘 초기", "어깨세모근 앞섬유와 큰가슴근 빗장부분, 부리위팔근이 위팔뼈를 앞으로 듭니다. 어깨세모근 뒤섬유는 길항근으로 늘어납니다.",
                        "시상면 움직임으로 위팔뼈머리는 접시오목 안에서 주로 제자리 돌기(spin)에 가깝게 움직인다고 설명합니다."),
                     ph(50, "굽힘 진행", "앞톱니근·등세모근이 어깨뼈를 위쪽으로 돌려 팔이 더 올라가게 합니다."),
                     ph(100, "최종 자세", "팔이 머리 위로. 넓은등근·큰원근·어깨세모근 뒤섬유가 늘어납니다.")]),
    shoulder("sh-extension", "mv-shoulder-extension", "어깨 · 폄 (Extension)",
             [rot(X, (0, 0), (1, 50))], scap=[(0, 0), (1, -8)], clav=[(0, 0), (1, 0)], load="resisted",
             phases=[ph(0, "시작 자세", "팔이 몸통 옆. 당기기(로우) 동작처럼 저항에 맞서 팔을 뒤로 보내는 상황을 가정합니다."),
                     ph(50, "폄 진행", "넓은등근·큰원근·어깨세모근 뒤섬유가 단축성 수축합니다. 위팔세갈래근 긴갈래가 돕습니다.", "위팔뼈머리가 접시오목 안에서 앞쪽으로 약간 미끄러지는 경향이 있으며 앞쪽 관절주머니가 팽팽해집니다."),
                     ph(100, "최종 자세", "약 50° 뒤로. 어깨뼈는 약간 아래쪽으로 돌고 들임됩니다 (마름근 — 자료 준비 중).")],
             extra_note="넓은등근은 BodyParts3D 모델에 메쉬가 없어 작용선을 표시할 수 없습니다."),
    shoulder("sh-adduction", "mv-shoulder-abduction", "어깨 · 모음 (Adduction, 저항에 맞서 내리기)",
             [rot(NZ, (0, 90), (1, 0))], scap=[(0, 30), (1, 0)], clav=[(0, 8), (1, 0)], load="resisted",
             phases=[ph(0, "시작 자세 (벌림 90°)", "팔을 옆으로 든 자세에서 케이블·밴드 같은 저항에 맞서 팔을 끌어내리는 상황을 가정합니다."),
                     ph(50, "모음 진행", "이 조건에서는 큰가슴근·큰원근(·넓은등근)이 단축성 수축하는 주동근입니다. 표에서 '주동근'으로 표시된 벌림근(어깨세모근·가시위근)은 이 동작에서 길항근 쪽 역할이며 늘어납니다.",
                        "벌림의 반대로, 위팔뼈머리는 아래로 구르며 위로 미끄러집니다."),
                     ph(100, "최종 자세", "팔이 몸통 옆으로 돌아옵니다. 저항 없이 중력으로 내릴 때는 오히려 벌림근이 신장성 수축으로 속도를 조절합니다 (어깨 벌림 동작의 역재생).")],
             extra_note="역할 색은 '벌림' 기준 데이터를 사용하므로, 이 동작에서는 빨강(벌림근)이 늘어나고 파랑 계열 근육이 일합니다. 해설을 함께 보세요."),
    shoulder("sh-internal-rotation", "mv-shoulder-flexion", "어깨 · 안쪽돌림 (Medial rotation)",
             [rot({"type": "between", "a": SH_PIVOTS["gh"], "b": {"type": "bbox", "mesh": "humerus", "at": [0.5, 0, 0.5]}, "sign": -1}, (0, 0), (1, 70))],
             load="resisted",
             phases=[ph(0, "시작 자세", "팔이 몸통 옆, 위팔뼈 긴축 둘레로 돕니다 (아래팔이 있다면 손이 배 쪽으로 오는 방향)."),
                     ph(50, "돌림 진행", "어깨밑근·큰가슴근·넓은등근·큰원근·어깨세모근 앞섬유가 안쪽돌림근입니다. 가시아래근·작은원근이 늘어납니다.", "위팔뼈머리가 접시오목 안에서 제자리 돌기(spin)가 주이며, 앞으로 구르고 뒤로 미끄러지는 성분이 함께 있다고 설명합니다."),
                     ph(100, "최종 자세", "약 70°. 이 시뮬레이션의 역할 색은 굽힘 데이터를 쓰므로 표의 역할보다 해설을 기준으로 보세요.")],
             angles=[{"label": "위팔뼈 안쪽돌림", "seg": "humerus"}], extra_note="돌림 동작의 근육 역할은 해설에 정리했습니다."),
    shoulder("sh-external-rotation", "mv-shoulder-flexion", "어깨 · 가쪽돌림 (Lateral rotation)",
             [rot({"type": "between", "a": SH_PIVOTS["gh"], "b": {"type": "bbox", "mesh": "humerus", "at": [0.5, 0, 0.5]}, "sign": 1}, (0, 0), (1, 60))],
             load="resisted",
             phases=[ph(0, "시작 자세", "팔이 몸통 옆."),
                     ph(50, "돌림 진행", "가시아래근·작은원근(+ 어깨세모근 뒤섬유)이 가쪽돌림의 주동근입니다. 어깨밑근·큰가슴근이 늘어납니다.", "위팔뼈머리가 뒤로 구르며 앞으로 미끄러지는 성분이 있다고 설명합니다."),
                     ph(100, "최종 자세", "약 60°.")],
             angles=[{"label": "위팔뼈 가쪽돌림", "seg": "humerus"}]),
    shoulder("sh-horizontal-adduction", "mv-shoulder-flexion", "어깨 · 수평모음 (Horizontal adduction)",
             [rot(NZ, (0, 90), (1, 90)), rot(Y, (0, 0), (1, 120))], scap=[(0, 25), (1, 25)], clav=[(0, 8), (1, 8)], load="resisted",
             phases=[ph(0, "시작 자세 (벌림 90°)", "팔을 옆으로 수평으로 든 자세."),
                     ph(50, "수평모음 진행", "큰가슴근(특히 복장갈비부분)과 어깨세모근 앞섬유가 팔을 몸 앞으로 모읍니다. 어깨세모근 뒤섬유·가시아래근이 늘어납니다. 어깨뼈는 내밈됩니다(앞톱니근).", "수평면 움직임입니다."),
                     ph(100, "최종 자세", "팔이 몸 앞을 가로지릅니다 (벤치프레스·플라이 동작의 마무리).")],
             angles=[{"label": "벌림 유지", "seg": "humerus", "rot": 0}, {"label": "수평모음", "seg": "humerus", "rot": 1}]),
    shoulder("sh-horizontal-abduction", "mv-shoulder-extension", "어깨 · 수평벌림 (Horizontal abduction)",
             [rot(NZ, (0, 90), (1, 90)), rot(Y, (0, 90), (1, -20))], scap=[(0, 25), (1, 20)], clav=[(0, 8), (1, 8)], load="resisted",
             phases=[ph(0, "시작 자세 (팔을 앞으로 90°)", "팔을 몸 앞에 수평으로 뻗은 자세."),
                     ph(50, "수평벌림 진행", "어깨세모근 뒤섬유·가시아래근·작은원근이 팔을 뒤로 벌립니다. 등세모근 중간섬유·마름근이 어깨뼈를 들임합니다.", ""),
                     ph(100, "최종 자세", "팔이 몸통 선보다 약간 뒤. 큰가슴근이 늘어납니다.")],
             angles=[{"label": "수평 위치 (앞 +)", "seg": "humerus", "rot": 1}]),
]

# ------------------------------------------------------------------ 팔 (arm-right)
FOREARM = ["radius", "ulna", "carpal_scaphoid", "carpal_lunate", "carpal_triquetral", "carpal_pisiform", "carpal_trapezium", "carpal_trapezoid", "carpal_capitate", "carpal_hamate", "metacarpals", "phalanges_hand"]
HAND = FOREARM[2:]
ELBOW = contact("ulna", "humerus", 0.5)
WRIST = {"type": "mid", "a": contact("radius", "carpal_scaphoid", 0.4), "b": contact("radius", "carpal_lunate", 0.4)}
RADIAL_AXIS = {"type": "between", "a": contact("radius", "humerus", 0.5), "b": {"type": "bbox", "mesh": "ulna", "at": [0.5, 0, 0.5]}, "sign": -1}  # 검수: 엎침 때 엄지쪽(큰마름뼈)이 앞을 지나 안쪽으로 가도록


def arm(id, item, title, segs, load, phases, angles, extra=""):
    return {"id": id, "model": "arm-right", "movementItemId": item, "title": title, "load": load, "duration": 3, "segments": segs,
            "angles": angles, "phases": phases, "note": COMMON_NOTE + " " + extra, "sources": ["os-9-6", "os-11-5"]}


MOTIONS += [
    arm("el-flexion", "mv-elbow-flexion", "팔꿉 · 굽힘", [seg("forearm", FOREARM, ELBOW, [rot(NX, (0, 0), (1, 140))])], "gravity",
        [ph(0, "시작 자세 (폄)", "팔꿈치가 펴져 있고 손바닥이 앞을 향합니다(뒤침).", "자뼈 도르래패임이 위팔뼈 도르래를 감싸고 있습니다."),
         ph(25, "굽힘 초기", "위팔근·위팔두갈래근이 단축성 수축을 시작합니다. 위팔세갈래근은 늘어납니다.", "오목한 자뼈 도르래패임이 볼록한 위팔뼈 도르래 위를 앞으로 구르고 같은 방향으로 미끄러집니다 (오목-볼록 규칙)."),
         ph(50, "굽힘 중간 (약 70°)", "중력에 대해 가장 큰 힘이 필요한 구간입니다. 위팔노근이 함께 작용합니다."),
         ph(100, "최종 자세 (약 140°)", "연부조직이 맞닿아 멈춥니다. 역재생은 신장성 수축으로 내려놓는 과정입니다.")],
        [{"label": "팔꿉 굽힘", "seg": "forearm"}], "운반각과 굽힘 중 축의 미세한 이동은 반영하지 않았습니다."),
    arm("el-extension", "mv-elbow-extension", "팔꿉 · 폄 (저항에 맞서 밀기)", [seg("forearm", FOREARM, ELBOW, [rot(NX, (0, 140), (1, 0))])], "resisted",
        [ph(0, "시작 자세 (굽힘)", "팔꿈치를 굽힌 자세에서 미는 동작을 가정합니다."),
         ph(50, "폄 진행", "위팔세갈래근이 단축성 수축합니다. 굽힘근은 늘어납니다.", "자뼈가 위팔뼈 도르래 위를 뒤로 구르며 같은 방향으로 미끄러집니다."),
         ph(100, "최종 자세", "팔꿈치머리가 팔꿈치오목에 맞물려 멈춥니다.")],
        [{"label": "팔꿉 굽힘 각", "seg": "forearm"}]),
    arm("fa-pronation", "mv-pronation", "아래팔 · 엎침", [seg("radius_hand", ["radius"] + HAND, contact("radius", "humerus", 0.5), [rot(RADIAL_AXIS, (0, 0), (1, 80))])], "resisted",
        [ph(0, "시작 자세 (뒤침)", "손바닥이 앞. 노뼈와 자뼈가 나란합니다."),
         ph(50, "엎침 진행", "네모엎침근이 먼저, 이어 원엎침근이 단축성 수축합니다. 손뒤침근·위팔두갈래근은 늘어납니다.", "몸쪽노자관절에서 노뼈머리는 제자리에서 돌고(spin), 먼쪽에서는 노뼈가 자뼈머리 둘레를 미끄러지며 돕니다."),
         ph(100, "최종 자세 (엎침)", "노뼈가 자뼈 앞을 가로질러 X자로 교차합니다.")],
        [{"label": "엎침", "seg": "radius_hand"}], "회전축은 노뼈머리 중심과 자뼈 먼쪽 끝을 잇는 선으로 근사했습니다."),
    arm("fa-supination", "mv-supination", "아래팔 · 뒤침", [seg("radius_hand", ["radius"] + HAND, contact("radius", "humerus", 0.5), [rot(RADIAL_AXIS, (0, 80), (1, 0))])], "resisted",
        [ph(0, "시작 자세 (엎침)", "손바닥이 뒤(아래)."),
         ph(50, "뒤침 진행", "손뒤침근이, 팔꿈치를 굽혀 힘을 줄 때는 위팔두갈래근이 크게 작용합니다.", "엎침의 반대 방향으로 노뼈가 돕니다."),
         ph(100, "최종 자세", "노뼈와 자뼈가 다시 나란해집니다.")],
        [{"label": "엎침 각 (0 = 뒤침)", "seg": "radius_hand"}]),
    arm("wr-flexion", "mv-wrist-flexion", "손목 · 굽힘", [seg("hand", HAND, WRIST, [rot(NX, (0, 0), (1, 70))])], "resisted",
        [ph(0, "시작 자세", "손목 중립."), ph(50, "굽힘 진행", "노쪽·자쪽손목굽힘근이 단축성 수축합니다. 손목폄근은 늘어납니다.",
                                              "볼록한 손목뼈가 오목한 노뼈 면 위에서 손바닥 쪽으로 구르고 등쪽으로 미끄러집니다. 실제로는 손목관절과 손목뼈중간관절이 나눠 맡지만, 여기서는 손 전체를 한 덩어리로 돌렸습니다."),
         ph(100, "최종 자세 (약 70°)", "")], [{"label": "손목 굽힘", "seg": "hand"}]),
    arm("wr-extension", "mv-wrist-extension", "손목 · 폄", [seg("hand", HAND, WRIST, [rot(X, (0, 0), (1, 60))])], "resisted",
        [ph(0, "시작 자세", "손목 중립."), ph(50, "폄 진행", "긴·짧은노쪽손목폄근과 자쪽손목폄근이 단축성 수축합니다.", "손목뼈가 등쪽으로 구르고 손바닥 쪽으로 미끄러집니다."),
         ph(100, "최종 자세 (약 60°)", "")], [{"label": "손목 폄", "seg": "hand"}]),
    arm("wr-radial-deviation", "mv-wrist-flexion", "손목 · 노쪽치우침", [seg("hand", HAND, WRIST, [rot(NZ, (0, 0), (1, 20))])], "resisted",
        [ph(0, "시작 자세", "손목 중립."), ph(50, "노쪽치우침", "노쪽손목굽힘근과 긴·짧은노쪽손목폄근이 짝을 이뤄 손을 엄지 쪽으로 기울입니다. (역할 색은 손목 굽힘 데이터 기준)", "손목뼈 몸쪽 줄이 자쪽으로 미끄러집니다."),
         ph(100, "최종 자세 (약 20°)", "")], [{"label": "노쪽치우침", "seg": "hand"}]),
    arm("wr-ulnar-deviation", "mv-wrist-flexion", "손목 · 자쪽치우침", [seg("hand", HAND, WRIST, [rot(Z, (0, 0), (1, 30))])], "resisted",
        [ph(0, "시작 자세", "손목 중립."), ph(50, "자쪽치우침", "자쪽손목굽힘근과 자쪽손목폄근이 짝을 이뤄 손을 새끼손가락 쪽으로 기울입니다. (역할 색은 손목 굽힘 데이터 기준)"),
         ph(100, "최종 자세 (약 30°)", "")], [{"label": "자쪽치우침", "seg": "hand"}]),
]

# ------------------------------------------------------------------ 다리 (leg-right)
FOOT = ["tarsal_talus", "tarsal_calcaneus", "tarsal_navicular", "tarsal_cuboid", "tarsal_medial_cuneiform", "tarsal_intermediate_cuneiform", "tarsal_lateral_cuneiform", "metatarsals", "phalanges_foot"]
SHANK = ["tibia", "fibula"] + FOOT
LEG = ["femur", "patella"] + SHANK
HIP = contact("femur", "hip_bone", 0.5)
KNEE = contact("tibia", "femur", 0.6)
ANKLE = contact("tarsal_talus", "tibia", 0.4)
SUBTALAR = contact("tarsal_calcaneus", "tarsal_talus", 0.4)
MECH = {"type": "between", "a": KNEE, "b": HIP, "sign": 1}


def leg(id, item, title, segs, load, phases, angles, extra=""):
    return {"id": id, "model": "leg-right", "movementItemId": item, "title": title, "load": load, "duration": 3, "segments": segs,
            "angles": angles, "phases": phases, "note": COMMON_NOTE + " " + extra, "sources": ["os-9-6", "os-11-6"]}


MOTIONS += [
    leg("hip-flexion", "mv-hip-flexion", "엉덩관절 · 굽힘", [seg("leg", LEG, HIP, [rot(NX, (0, 0), (1, 100))])], "gravity",
        [ph(0, "시작 자세", "선 자세."), ph(30, "굽힘 초기", "엉덩허리근·넙다리곧은근이 단축성 수축합니다. 큰볼기근·뒤넙다리근이 늘어납니다.",
                                          "넙다리뼈머리가 절구 안에서 주로 돌기(spin)에 가깝게 움직입니다 (구관절)."),
         ph(70, "굽힘 후반", "무릎을 편 채로 들면 뒤넙다리근이 많이 늘어나 범위가 제한됩니다. 실제로는 골반 뒤기울임이 함께 일어납니다 (생략)."),
         ph(100, "최종 자세 (100°)", "")], [{"label": "엉덩관절 굽힘", "seg": "leg"}], "무릎은 편 상태로 고정했습니다."),
    leg("hip-extension", "mv-hip-extension", "엉덩관절 · 폄", [seg("leg", LEG, HIP, [rot(X, (0, 0), (1, 20))])], "resisted",
        [ph(0, "시작 자세", "선 자세."), ph(50, "폄 진행", "큰볼기근·뒤넙다리근이 단축성 수축합니다.", "엉덩넙다리인대가 앞에서 팽팽해져 범위를 제한합니다."),
         ph(100, "최종 자세 (약 20°)", "")], [{"label": "엉덩관절 폄", "seg": "leg"}]),
    leg("hip-abduction", "mv-hip-abduction", "엉덩관절 · 벌림", [seg("leg", LEG, HIP, [rot(NZ, (0, 0), (1, 40))])], "gravity",
        [ph(0, "시작 자세", "두 다리가 나란합니다."), ph(50, "벌림 진행", "중간·작은볼기근, 넙다리근막긴장근이 단축성 수축합니다. 모음근이 늘어납니다.", "넙다리뼈머리가 절구 안에서 위로 구르며 아래로 미끄러집니다."),
         ph(100, "최종 자세 (약 40°)", "")], [{"label": "엉덩관절 벌림", "seg": "leg"}]),
    leg("hip-adduction", "mv-hip-abduction", "엉덩관절 · 모음 (저항에 맞서)", [seg("leg", LEG, HIP, [rot(NZ, (0, 40), (1, -15))])], "resisted",
        [ph(0, "시작 자세 (벌림 40°)", ""), ph(50, "모음 진행", "긴모음근·큰모음근·두덩정강근이 단축성 수축합니다. 표의 '주동근'(벌림근)은 이 동작에서 늘어납니다 — 역할 색은 벌림 데이터 기준입니다."),
         ph(100, "최종 자세 (중심선 넘어 15°)", "")], [{"label": "엉덩관절 벌림(+)/모음(−)", "seg": "leg"}]),
    leg("hip-internal-rotation", "mv-hip-flexion", "엉덩관절 · 안쪽돌림", [seg("leg", LEG, HIP, [rot(MECH, (0, 0), (1, 35))])], "resisted",
        [ph(0, "시작 자세", "발끝이 앞."), ph(50, "안쪽돌림", "작은볼기근, 중간볼기근 앞섬유, 넙다리근막긴장근이 안쪽돌림근입니다. 궁둥구멍근 등 가쪽돌림근이 늘어납니다. (역할 색은 굽힘 데이터 기준)",
                                            "넙다리뼈머리가 절구 안에서 돌기(spin)합니다."), ph(100, "최종 자세 (약 35°)", "")],
        [{"label": "안쪽돌림", "seg": "leg"}], "회전축은 넙다리뼈머리 중심과 무릎 중심을 잇는 역학적 축으로 근사했습니다."),
    leg("hip-external-rotation", "mv-hip-extension", "엉덩관절 · 가쪽돌림", [seg("leg", LEG, HIP, [rot(MECH, (0, 0), (1, -45))])], "resisted",
        [ph(0, "시작 자세", "발끝이 앞."), ph(50, "가쪽돌림", "궁둥구멍근 등 깊은 가쪽돌림근과 큰볼기근이 작용합니다. (역할 색은 폄 데이터 기준)"), ph(100, "최종 자세 (약 45°)", "")],
        [{"label": "돌림 (− = 가쪽)", "seg": "leg"}]),
    leg("knee-flexion", "mv-knee-flexion", "무릎 · 굽힘 (열린사슬)", [seg("shank", SHANK, KNEE, [rot(X, (0, 0), (1, 120))]),
                                                              seg("patella", ["patella"], KNEE, [rot(X, (0, 0), (1, 60))])], "gravity",
        [ph(0, "시작 자세 (폄)", "발이 땅에서 떨어진 열린사슬. 완전히 편 무릎은 정강뼈가 약간 가쪽으로 돈 '잠금' 상태로 설명합니다."),
         ph(15, "잠금 풀기", "오금근이 정강뼈를 안쪽으로 돌려 잠금을 풉니다 (오금근 자료 준비 중, 이 시뮬레이션에서 돌림은 생략).",
            "열린사슬에서 오목한 정강뼈 관절면이 볼록한 넙다리뼈 관절융기 위를 뒤로 구르고 뒤로 미끄러집니다 (같은 방향)."),
         ph(50, "굽힘 진행", "뒤넙다리근이 단축성 수축합니다. 장딴지근이 돕고 넙다리네갈래근이 늘어납니다."),
         ph(100, "최종 자세 (120°)", "닫힌사슬(스쿼트)에서는 넙다리뼈가 정강뼈 위에서 뒤로 구르며 앞으로 미끄러지고, 넙다리네갈래근이 신장성으로 내려가는 속도를 조절합니다.")],
        [{"label": "무릎 굽힘", "seg": "shank"}], "무릎뼈는 굽힘 각의 절반만큼 같은 축으로 돌려 근사했습니다 (실제 무릎뼈 경로 아님)."),
    leg("knee-extension", "mv-knee-extension", "무릎 · 폄 (열린사슬)", [seg("shank", SHANK, KNEE, [rot(X, (0, 90), (1, 0))]),
                                                                 seg("patella", ["patella"], KNEE, [rot(X, (0, 45), (1, 0))])], "gravity",
        [ph(0, "시작 자세 (90°)", "엉덩관절은 편 채 무릎을 90° 굽힌 열린사슬 자세 (이 모델은 선 자세 기준이라 정강이가 뒤로 놓임). 앉아서 펴는 동작과 무릎의 관절 운동은 같습니다."), ph(50, "폄 진행", "넙다리네갈래근이 단축성 수축합니다. 뒤넙다리근이 늘어납니다.", "정강뼈가 넙다리뼈 위에서 앞으로 구르고 앞으로 미끄러집니다."),
         ph(90, "마지막 폄", "완전히 펴지는 마지막 범위에서 정강뼈가 약간 가쪽으로 도는 '잠금 회전'이 일어난다고 설명합니다 (생략)."),
         ph(100, "최종 자세 (0°)", "")], [{"label": "무릎 굽힘 각", "seg": "shank"}]),
    leg("ankle-dorsiflexion", "mv-ankle-dorsiflexion", "발목 · 발등굽힘", [seg("foot", FOOT, ANKLE, [rot(NX, (0, 0), (1, 20))])], "gravity",
        [ph(0, "시작 자세", "발이 정강이와 직각."), ph(50, "발등굽힘", "앞정강근이 단축성 수축합니다. 장딴지근·가자미근이 늘어납니다.", "목말뼈 도르래가 발목장부 안에서 앞으로 구르며 뒤로 미끄러집니다. 넓은 앞쪽이 끼어 안정됩니다."),
         ph(100, "최종 자세 (20°)", "")], [{"label": "발등굽힘", "seg": "foot"}]),
    leg("ankle-plantarflexion", "mv-ankle-plantarflexion", "발목 · 발바닥굽힘", [seg("foot", FOOT, ANKLE, [rot(X, (0, 0), (1, 45))])], "gravity",
        [ph(0, "시작 자세", "중립."), ph(50, "발바닥굽힘", "장딴지근·가자미근이 단축성 수축합니다. 앞정강근이 늘어납니다.", "목말뼈가 뒤로 구르며 앞으로 미끄러집니다. 좁은 뒤쪽이 장부에 놓여 덜 안정적입니다."),
         ph(100, "최종 자세 (45°)", "")], [{"label": "발바닥굽힘", "seg": "foot"}]),
    leg("foot-inversion", "mv-ankle-inversion", "발 · 안쪽번짐", [seg("foot_sub", FOOT[1:], SUBTALAR, [rot({"type": "fixed", "v": [0.205, 0.669, 0.715]}, (0, 0), (1, 25))])], "resisted",
        [ph(0, "시작 자세", "발바닥이 바닥과 나란."), ph(50, "안쪽번짐", "뒤정강근·앞정강근이 수축합니다. 긴·짧은종아리근이 늘어납니다.", "목말밑관절의 비스듬한 축(앞위안쪽 방향) 둘레로 발꿈치뼈가 돕니다 — 세 면이 섞인 뒤침(supination)."),
         ph(100, "최종 자세", "")], [{"label": "번짐 각", "seg": "foot_sub"}], "목말밑관절 축은 문헌의 평균 방향(수평에서 약 42°, 안쪽 약 16°)으로 근사했고, 가로발목뼈관절은 한 덩어리로 처리했습니다."),
    leg("foot-eversion", "mv-ankle-eversion", "발 · 가쪽번짐", [seg("foot_sub", FOOT[1:], SUBTALAR, [rot({"type": "fixed", "v": [0.205, 0.669, 0.715]}, (0, 0), (1, -15))])], "resisted",
        [ph(0, "시작 자세", ""), ph(50, "가쪽번짐", "긴·짧은종아리근이 수축합니다.", "안쪽번짐과 같은 축에서 반대 방향 — 엎침(pronation)."), ph(100, "최종 자세", "")],
        [{"label": "번짐 각", "seg": "foot_sub"}]),
    leg("pelvis-anterior-tilt", "mv-hip-flexion", "골반 · 앞기울임", [seg("pelvis", ["hip_bone", "sacrum"], HIP, [rot(X, (0, 0), (1, 15))])], "none",
        [ph(0, "시작 자세", "넙다리뼈를 고정하고 골반이 움직입니다 (닫힌사슬)."), ph(50, "앞기울임", "위앞엉덩뼈가시가 앞아래로 내려가며 엉덩관절은 굽힘 위치가 됩니다. 엉덩허리근·척추세움근이 관여합니다.", ""),
         ph(100, "최종 자세 (15°)", "허리 앞굽이가 커집니다 (척추는 이 모델에 없음).")], [{"label": "골반 앞기울임", "seg": "pelvis"}], "이 모델은 오른쪽 볼기뼈와 엉치뼈만 포함합니다."),
    leg("pelvis-posterior-tilt", "mv-hip-extension", "골반 · 뒤기울임", [seg("pelvis", ["hip_bone", "sacrum"], HIP, [rot(X, (0, 0), (1, -12))])], "none",
        [ph(0, "시작 자세", ""), ph(50, "뒤기울임", "배곧은근·큰볼기근·뒤넙다리근이 관여합니다. 엉덩관절은 폄 위치가 됩니다."), ph(100, "최종 자세", "")],
        [{"label": "골반 기울임 (− = 뒤)", "seg": "pelvis"}]),
]

# ------------------------------------------------------------------ 몸통 (trunk)
LUMB = ["vertebra_l5", "vertebra_l4", "vertebra_l3", "vertebra_l2", "vertebra_l1"]
CERV = ["vertebra_c7", "vertebra_c6", "vertebra_c5", "vertebra_c4", "vertebra_c3", "vertebra_c2", "vertebra_c1"]
THORAX = [f"vertebra_t{i}" for i in range(1, 13)] + ["ribs_r", "ribs_l", "manubrium", "sternum_body", "costal_cartilage_r", "costal_cartilage_l", "diaphragm",
                                                       "external_intercostals", "internal_intercostals"]


def spine_chain(axis, lumb_deg, thorax_deg, neck_deg=0):
    segs = []
    below = {"vertebra_l5": "sacrum", "vertebra_l4": "vertebra_l5", "vertebra_l3": "vertebra_l4", "vertebra_l2": "vertebra_l3", "vertebra_l1": "vertebra_l2"}
    parent = None
    for v in LUMB:
        segs.append(seg(v, [v], contact(v, below[v], 0.6), [rot(axis, (0, 0), (1, lumb_deg))], parent=parent))
        parent = v
    segs.append(seg("thorax", THORAX + CERV + ["hyoid"], contact("vertebra_t12", "vertebra_l1", 0.6), [rot(axis, (0, 0), (1, thorax_deg))], parent=parent))
    return segs


def neck_chain(axis, degs):
    segs, parent = [], None
    below = {"vertebra_c7": "vertebra_t1", "vertebra_c6": "vertebra_c7", "vertebra_c5": "vertebra_c6", "vertebra_c4": "vertebra_c5",
             "vertebra_c3": "vertebra_c4", "vertebra_c2": "vertebra_c3", "vertebra_c1": "vertebra_c2"}
    for v, d in zip(CERV, degs):
        segs.append(seg(v, [v] + (["hyoid"] if v == "vertebra_c3" else []), contact(v, below[v], 0.6), [rot(axis, (0, 0), (1, d))], parent=parent))
        parent = v
    return segs


def trunk(id, item, title, segs, load, phases, angles, extra=""):
    return {"id": id, "model": "trunk", "movementItemId": item, "title": title, "load": load, "duration": 3.5, "segments": segs,
            "angles": angles, "phases": phases, "note": COMMON_NOTE + " 허리뼈는 분절마다 돌리고, 등뼈·갈비뼈·복장뼈는 한 덩어리로 처리했습니다 (갈비뼈가 하나의 메쉬로 합쳐져 있음). " + extra,
            "sources": ["os-7-3", "os-11-3", "os-11-4"]}


SP_ANG = [{"label": f"{v[-2:].upper()} 분절", "seg": v} for v in LUMB] + [{"label": "등뼈 덩어리", "seg": "thorax"}]
MOTIONS += [
    trunk("sp-flexion", "mv-trunk-flexion", "척추 · 굽힘", spine_chain(X, 8, 25), "gravity",
          [ph(0, "시작 자세", "바른 자세. 누워서 상체를 드는 상황을 가정합니다."),
           ph(50, "굽힘 진행", "배곧은근·배빗근이 단축성 수축합니다. 척추세움근·뭇갈래근이 늘어납니다.", "각 분절에서 위 척추뼈가 아래 척추뼈 위로 앞으로 기울며 미끄러지고, 척추사이원반 앞쪽이 눌립니다. 뒤쪽 돌기사이관절면은 위로 미끄러져 벌어집니다."),
           ph(100, "최종 자세", "허리 분절 각 약 8°, 합계 약 40° + 등뼈 부분. 서서 숙일 때는 반대로 척추세움근이 신장성 수축합니다.")], SP_ANG,
          "배곧은근·배속빗근·배가로근·뭇갈래근은 BodyParts3D 모델에 메쉬가 없어 작용선을 그릴 수 없습니다."),
    trunk("sp-extension", "mv-trunk-extension", "척추 · 폄", spine_chain(NX, 4, 10), "gravity",
          [ph(0, "시작 자세", ""), ph(50, "폄 진행", "척추세움근(엉덩갈비근·가장긴근·가시근)이 단축성 수축합니다.", "위 척추뼈가 뒤로 기울며 돌기사이관절면이 아래로 미끄러져 맞물립니다. 원반 뒤쪽이 눌립니다."), ph(100, "최종 자세", "")],
          SP_ANG),
    trunk("sp-lateral-flexion", "mv-trunk-lateral-flexion", "척추 · 가쪽굽힘 (오른쪽)", spine_chain(Z, 4, 12), "gravity",
          [ph(0, "시작 자세", ""), ph(50, "가쪽굽힘", "같은쪽(오른쪽) 배바깥빗근·척추세움근·허리네모근이 수축하고 반대쪽이 늘어납니다.", "같은쪽 돌기사이관절이 닫히고 반대쪽이 열립니다. 허리뼈에서는 가쪽굽힘에 약간의 돌림이 짝지어 일어난다고 설명합니다 (생략)."),
           ph(100, "최종 자세", "")], SP_ANG),
    trunk("sp-rotation", "mv-trunk-rotation", "척추 · 돌림 (왼쪽)", spine_chain(Y, 1, 30), "resisted",
          [ph(0, "시작 자세", ""), ph(50, "돌림", "몸통을 왼쪽으로 돌릴 때 오른쪽 배바깥빗근과 왼쪽 배속빗근(메쉬 없음)이 함께 일합니다.", "허리뼈는 돌기사이관절면이 시상면에 가까워 분절당 약 1–2°만 돌고, 대부분의 돌림은 등뼈에서 일어납니다."),
           ph(100, "최종 자세", "")], SP_ANG),
    trunk("nk-flexion", "mv-neck-flexion", "목 · 굽힘", neck_chain(X, [6, 7, 7, 7, 6, 5, 10]), "gravity",
          [ph(0, "시작 자세", "중립. 누워서 머리를 드는 상황을 가정합니다."), ph(50, "굽힘", "목빗근·목긴근·머리긴근이 단축성 수축합니다.", "목뼈 분절이 앞으로 기울며 미끄러집니다. 고리뒤통수관절에서 끄덕임이 더해집니다 (머리뼈는 이 모델에 없음)."),
           ph(100, "최종 자세", "")], [{"label": v.replace("vertebra_", "").upper(), "seg": v} for v in CERV]),
    trunk("nk-extension", "mv-neck-extension", "목 · 폄", neck_chain(NX, [8, 9, 9, 9, 8, 6, 10]), "gravity",
          [ph(0, "시작 자세", ""), ph(50, "폄", "널판근·반가시근·척추세움근 목부분·등세모근 위섬유가 수축합니다."), ph(100, "최종 자세", "")],
          [{"label": v.replace("vertebra_", "").upper(), "seg": v} for v in CERV]),
    trunk("nk-rotation", "mv-neck-rotation", "목 · 돌림 (왼쪽)", neck_chain(Y, [3, 4, 4, 4, 4, 4, 35]), "resisted",
          [ph(0, "시작 자세", ""), ph(50, "돌림", "얼굴을 왼쪽으로 돌릴 때 오른쪽 목빗근이 수축합니다.", "돌림의 약 절반이 고리중쇠관절(C1–C2)에서 일어나며, 고리뼈가 치아돌기 둘레를 돕니다."),
           ph(100, "최종 자세", "")], [{"label": "C1–C2", "seg": "vertebra_c1"}, {"label": "C3–C7 각 분절", "seg": "vertebra_c3"}]),
    trunk("nk-lateral-flexion", "mv-neck-lateral-flexion", "목 · 가쪽굽힘 (오른쪽)", neck_chain(Z, [5, 5, 5, 5, 5, 4, 4]), "gravity",
          [ph(0, "시작 자세", ""), ph(50, "가쪽굽힘", "같은쪽 목갈비근·목빗근·어깨올림근이 수축합니다."), ph(100, "최종 자세", "")],
          [{"label": v.replace("vertebra_", "").upper(), "seg": v} for v in CERV]),
    {"id": "breathing", "model": "trunk", "movementItemId": "mv-breathing", "title": "호흡 · 들숨 (가로막 하강·갈비뼈 올림)", "load": "gravity", "duration": 2.5,
     "segments": [seg("chest", ["ribs_r", "ribs_l", "manubrium", "sternum_body", "costal_cartilage_r", "costal_cartilage_l", "external_intercostals", "internal_intercostals"],
                      {"type": "bbox", "mesh": "vertebra_t4", "at": [0.5, 0.5, 0.5]}, [rot(NX, (0, 0), (1, 4))]),
                  seg("diaphragm_seg", ["diaphragm"], {"type": "bbox", "mesh": "diaphragm", "at": [0.5, 0.5, 0.5]}, [], translations=[{"v": [0, -1.8, 0], "curve": [[0, 0], [1, 1]]}])],
     "angles": [{"label": "가슴우리 올림 (펌프손잡이 근사)", "seg": "chest"}],
     "phases": [ph(0, "날숨 끝", "가로막이 돔 모양으로 위에 있습니다."),
                ph(50, "들숨 중간", "가로막이 수축해 내려가고(여기서는 평행이동으로 표현), 바깥갈비사이근이 갈비뼈를 들어 올립니다.", "갈비척추관절 축 둘레로 위쪽 갈비뼈는 앞끝이 들리는 펌프손잡이 운동을 합니다. 아래쪽의 양동이손잡이 운동은 생략했습니다."),
                ph(100, "들숨 끝", "가슴안 부피가 가장 큽니다. 역재생 = 조용한 날숨 (가로막 이완, 탄성 되돌림).")],
     "note": COMMON_NOTE + " 가로막의 실제 수축은 돔이 평평해지는 변형이지만, 여기서는 아래로 평행이동해 표현했습니다. 갈비뼈 12쌍은 하나의 메쉬라 함께 돕니다.", "sources": ["os-22-3", "os-11-4"]},
]

# ------------------------------------------------------------------ 머리 (head) — 씹기근육은 메쉬 없음 → 가상 작용선
TMJ_R = contact("mandible", "temporal_r", 0.5)
TMJ_L = contact("mandible", "temporal_l", 0.5)
TMJ_AXIS = {"type": "between", "a": TMJ_R, "b": TMJ_L, "sign": 1}
VM = [
    {"label": "깨물근 (오른쪽)", "itemId": "m-masseter", "from": {"type": "extreme", "mesh": "zygomatic_r", "dir": [-0.2, -1, 0], "k": 20},
     "to": {"type": "extreme", "mesh": "mandible", "dir": [-0.6, -0.6, -0.5], "side": -1, "k": 20}, "toSeg": "mandible"},
    {"label": "관자근 (오른쪽)", "itemId": "m-temporalis", "from": {"type": "extreme", "mesh": "temporal_r", "dir": [-0.6, 0.8, 0.2], "k": 20},
     "to": {"type": "extreme", "mesh": "mandible", "dir": [-0.2, 0.9, 0.4], "side": -1, "k": 15}, "toSeg": "mandible"},
    {"label": "가쪽날개근 (오른쪽)", "itemId": "m-lateral-pterygoid", "from": {"type": "extreme", "mesh": "sphenoid", "dir": [-0.5, -0.5, 0.6], "side": -1, "k": 20},
     "to": TMJ_R, "toSeg": "mandible"},
    {"label": "안쪽날개근 (오른쪽)", "itemId": "m-medial-pterygoid", "from": {"type": "extreme", "mesh": "sphenoid", "dir": [-0.3, -1, 0.3], "side": -1, "k": 20},
     "to": {"type": "extreme", "mesh": "mandible", "dir": [-0.3, -0.7, -0.6], "side": -1, "k": 20, "offset": [0.6, 0, 0]}, "toSeg": "mandible"},
]


def jaw(id, item, title, segs, phases, angles, extra=""):
    return {"id": id, "model": "head", "movementItemId": item, "title": title, "load": "resisted", "duration": 2.5, "segments": segs, "virtualMuscles": VM,
            "angles": angles, "phases": phases,
            "note": COMMON_NOTE + " 씹기근육은 BodyParts3D에 메쉬가 없어, 머리뼈·아래턱뼈 형상에서 고른 기준점 사이의 '가상 작용선'으로만 표시합니다 (위치는 근사). 관절원반은 모델에 없습니다. " + extra,
            "sources": ["os-9-6", "os-11-3"]}


MOTIONS += [
    jaw("jaw-open", "mv-mouth-opening", "턱 · 입 벌림 (회전 → 미끄러짐)",
        [seg("mandible", ["mandible"], {"type": "mid", "a": TMJ_R, "b": TMJ_L}, [rot(TMJ_AXIS, (0, 0), (0.35, 12), (1, 28))],
             translations=[{"v": [0, -0.25, 1.0], "curve": [[0, 0], [0.35, 0], [1, 1]]}])],
        [ph(0, "다문 자세", "이가 맞물려 있습니다."),
         ph(20, "벌림 초기 (회전)", "아래 관절안에서 턱뼈머리가 관절원반 아래에서 경첩처럼 돕니다. 목뿔위근육이 아래턱을 끌어내립니다.", "회전(roll/spin) 성분이 주입니다 — 처음 약 1/3 구간."),
         ph(60, "벌림 후반 (미끄러짐)", "가쪽날개근이 턱뼈머리와 원반을 관절결절 쪽으로 앞으로 당깁니다.", "위 관절안에서 턱뼈머리+원반이 앞아래로 미끄러집니다(glide/translation). 회전과 이동이 함께 일어나 회전 중심이 아래로 내려간 것처럼 보입니다."),
         ph(100, "최대 벌림", "깨물근·관자근·안쪽날개근이 늘어납니다. 역재생 = 입 닫음 (이 근육들이 수축).")],
        [{"label": "아래턱 회전", "seg": "mandible"}]),
    jaw("jaw-protrusion", "mv-jaw-protrusion", "턱 · 내밈 (전진)",
        [seg("mandible", ["mandible"], {"type": "mid", "a": TMJ_R, "b": TMJ_L}, [], translations=[{"v": [0, -0.15, 0.7], "curve": [[0, 0], [1, 1]]}])],
        [ph(0, "시작", ""), ph(50, "내밈", "양쪽 가쪽·안쪽날개근이 아래턱을 앞으로 미끄러뜨립니다.", "두 턱뼈머리가 함께 관절결절 쪽으로 미끄러지는 순수한 이동(translation)입니다."),
         ph(100, "최대 내밈", "역재생 = 들임 (관자근 뒤섬유).")], []),
    jaw("jaw-lateral", "mv-jaw-lateral", "턱 · 왼쪽으로 옆 움직임",
        [seg("mandible", ["mandible"], TMJ_L, [rot(Y, (0, 0), (1, 7))])],
        [ph(0, "중심", ""), ph(50, "옆 움직임", "오른쪽 가쪽·안쪽날개근이 오른쪽 턱뼈머리를 앞안쪽으로 당기고, 왼쪽 관자근 뒤섬유가 왼쪽 턱뼈머리를 제자리에 둡니다.",
                                            "왼쪽(작업쪽) 턱뼈머리는 제자리에서 돌고(spin), 오른쪽(균형쪽) 턱뼈머리는 앞안쪽으로 미끄러집니다."),
         ph(100, "최대", "")], [{"label": "아래턱 수평 회전", "seg": "mandible"}]),
]


def _post(motions):
    for m in motions:
        if m["id"] == "sh-abduction":
            m["angleSlider"] = ABD_SLIDER
    return motions


def main():
    MESH_ROLES = {
        "sh-flexion": {"deltoid_posterior": "antagonist", "pecmaj_clavicular": "synergist", "pecmaj_sternocostal": "antagonist", "pecmaj_abdominal": "antagonist"},
        "sh-extension": {"deltoid_posterior": "agonist", "deltoid_anterior": "antagonist", "deltoid_middle": "synergist", "pecmaj_clavicular": "antagonist", "triceps_long": "synergist"},
        "sh-horizontal-adduction": {"deltoid_anterior": "agonist", "deltoid_posterior": "antagonist", "pecmaj_clavicular": "agonist", "pecmaj_sternocostal": "agonist", "infraspinatus": "antagonist"},
        "sh-horizontal-abduction": {"deltoid_posterior": "agonist", "deltoid_anterior": "antagonist", "infraspinatus": "agonist", "teres_minor": "agonist", "pecmaj_sternocostal": "antagonist", "pecmaj_clavicular": "antagonist"},
        "sh-internal-rotation": {"subscapularis": "agonist", "pecmaj_sternocostal": "agonist", "teres_major": "agonist", "deltoid_anterior": "synergist", "infraspinatus": "antagonist", "teres_minor": "antagonist", "deltoid_posterior": "antagonist"},
        "sh-external-rotation": {"infraspinatus": "agonist", "teres_minor": "agonist", "deltoid_posterior": "synergist", "subscapularis": "antagonist", "pecmaj_sternocostal": "antagonist", "teres_major": "antagonist", "deltoid_anterior": "antagonist"},
        "sh-adduction": {"pecmaj_sternocostal": "agonist", "pecmaj_abdominal": "agonist", "teres_major": "agonist", "deltoid_middle": "antagonist", "supraspinatus": "antagonist", "deltoid_anterior": "antagonist", "deltoid_posterior": "antagonist"},
        "hip-adduction": {"adductor_longus": "agonist", "adductor_magnus": "agonist", "gracilis": "agonist", "adductor_brevis": "agonist", "gluteus_medius": "antagonist", "gluteus_minimus": "antagonist", "tfl": "antagonist"},
        "hip-internal-rotation": {"gluteus_minimus": "agonist", "tfl": "agonist", "gluteus_medius": "synergist", "piriformis": "antagonist", "gluteus_maximus": "antagonist"},
        "hip-external-rotation": {"piriformis": "agonist", "gluteus_maximus": "agonist", "gluteus_minimus": "antagonist", "tfl": "antagonist"},
        "wr-radial-deviation": {"fcr": "agonist", "ecrl": "agonist", "ecrb": "agonist", "fcu": "antagonist", "ecu": "antagonist"},
        "wr-ulnar-deviation": {"fcu": "agonist", "ecu": "agonist", "fcr": "antagonist", "ecrl": "antagonist", "ecrb": "antagonist"},
    }
    for m in MOTIONS:
        m.setdefault("roles", {})
        if m["id"] in MESH_ROLES:
            m["meshRoles"] = MESH_ROLES[m["id"]]
    out = {"version": 1, "note": "3D 움직임 정의. tools/make_motions.py 로 생성.", "motions": _post(MOTIONS)}
    json.dump(out, open(os.path.join(ROOT, "data", "motions3d.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from collections import Counter
    print(len(MOTIONS), "motions", Counter(m["model"] for m in MOTIONS))


if __name__ == "__main__":
    main()
