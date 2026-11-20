"""
부위별 3D 모델 정의 → data/mappings/<id>.json 과 data/models3d.json 등록 + 원본 OBJ 추출

각 구조: (meshId, [BodyParts3D 개념명...], 한글명, 영어명, layer, anatomyItemId|None, 관계)
  - 개념명이 여러 개면 해당 OBJ들을 하나의 메쉬로 합칩니다 (예: 손가락뼈 14개).
  - anatomyItemId 는 같은 구조(same)이거나 그 항목의 한 부분(part-of)일 때만 지정합니다.

사용법:
  python3 tools/regions.py <isa_BP3D_4.0_obj_99.zip 경로>   → 매핑·등록부 갱신, 필요한 OBJ를 sources/bodyparts3d/obj 로 추출
그 다음 python3 tools/build_model_glb.py 로 GLB 생성.
"""
import collections
import json
import os
import sys
import zipfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ORD = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth"]
KO = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
FINGERS = ["thumb", "index finger", "middle finger", "ring finger", "little finger"]
TOES = ["big toe", "second toe", "third toe", "fourth toe", "little toe"]


def S(mesh, concepts, ko, en, layer, item=None, rel=None):
    return {"mesh": mesh, "concepts": concepts if isinstance(concepts, list) else [concepts], "ko": ko, "en": en,
            "layer": layer, "item": item, "rel": rel or ("same" if item else None)}


hand_phal = [f"{p} phalanx of right {f}" for f in FINGERS for p in ("proximal", "middle", "distal") if not (f == "thumb" and p == "middle")]
foot_phal = [f"{p} phalanx of right {t}" for t in TOES for p in ("proximal", "middle", "distal") if not (t == "big toe" and p == "middle")]

REGIONS = {
    "arm-right": {
        "title": "오른팔 · 위팔 · 아래팔 · 손", "region": "upper-limb", "camera": {"view": "front", "fov": 35, "fitPadding": 1.05},
        "related": ["j-elbow", "j-radioulnar", "j-wrist", "j-thumb-cmc", "mv-elbow-flexion", "mv-elbow-extension", "mv-pronation", "mv-supination",
                    "mv-wrist-flexion", "mv-wrist-extension", "mv-finger-flexion", "mv-finger-abduction", "mv-thumb-opposition", "c-carpal-tunnel", "c-hand-grips"],
        "structures": [
            S("scapula", "right scapula", "어깨뼈", "Scapula", "bone", "b-scapula"),
            S("clavicle", "right clavicle", "빗장뼈", "Clavicle", "bone", "b-clavicle"),
            S("humerus", "right humerus", "위팔뼈", "Humerus", "bone", "b-humerus"),
            S("radius", "right radius", "노뼈", "Radius", "bone", "b-radius"),
            S("ulna", "right ulna", "자뼈", "Ulna", "bone", "b-ulna"),
            *[S(f"carpal_{n}", f"right {n}", ko, n.title(), "bone", "b-carpals", "part-of") for n, ko in
              (("scaphoid", "손배뼈"), ("lunate", "반달뼈"), ("triquetral", "세모뼈"), ("pisiform", "콩알뼈"), ("trapezium", "큰마름뼈"),
               ("trapezoid", "작은마름뼈"), ("capitate", "알머리뼈"), ("hamate", "갈고리뼈"))],
            S("metacarpals", [f"right {o} metacarpal bone" for o in ORD[:5]], "손허리뼈 (1–5)", "Metacarpals", "bone", "b-metacarpals"),
            S("phalanges_hand", hand_phal, "손가락뼈 (14개)", "Phalanges of the hand", "bone", "b-phalanges-hand"),
            S("biceps_long", "long head of right biceps brachii", "위팔두갈래근 긴갈래", "Biceps brachii — long head", "superficial", "m-biceps-brachii", "part-of"),
            S("biceps_short", "short head of right biceps brachii", "위팔두갈래근 짧은갈래", "Biceps brachii — short head", "superficial", "m-biceps-brachii", "part-of"),
            S("brachialis", "right brachialis", "위팔근", "Brachialis", "deep", "m-brachialis"),
            S("triceps_long", "long head of right triceps brachii", "위팔세갈래근 긴갈래", "Triceps — long head", "superficial", "m-triceps-brachii", "part-of"),
            S("triceps_lateral", "lateral head of right triceps brachii", "위팔세갈래근 가쪽갈래", "Triceps — lateral head", "superficial", "m-triceps-brachii", "part-of"),
            S("triceps_medial", "medial head of right triceps brachii", "위팔세갈래근 안쪽갈래", "Triceps — medial head", "deep", "m-triceps-brachii", "part-of"),
            S("coracobrachialis", "right coracobrachialis", "부리위팔근", "Coracobrachialis", "deep", "m-coracobrachialis"),
            S("brachioradialis", "right brachioradialis", "위팔노근", "Brachioradialis", "superficial", "m-brachioradialis"),
            S("pronator_teres", ["humeral head of right pronator teres", "ulnar head of right pronator teres"], "원엎침근", "Pronator teres", "superficial", "m-pronator-teres"),
            S("pronator_quadratus", "right pronator quadratus", "네모엎침근", "Pronator quadratus", "deep", "m-pronator-quadratus"),
            S("supinator", "right supinator", "손뒤침근", "Supinator", "deep", "m-supinator"),
            S("fcr", "right flexor carpi radialis", "노쪽손목굽힘근", "Flexor carpi radialis", "superficial", "m-flexor-carpi-radialis"),
            S("fcu", ["humeral head of right flexor carpi ulnaris", "ulnar head of right flexor carpi ulnaris"], "자쪽손목굽힘근", "Flexor carpi ulnaris", "superficial", "m-flexor-carpi-ulnaris"),
            S("palmaris_longus", "right palmaris longus", "긴손바닥근", "Palmaris longus", "superficial", "m-palmaris-longus"),
            S("ecrl", "right extensor carpi radialis longus", "긴노쪽손목폄근", "Extensor carpi radialis longus", "superficial", "m-extensor-carpi-radialis-longus"),
            S("ecrb", "right extensor carpi radialis brevis", "짧은노쪽손목폄근", "Extensor carpi radialis brevis", "superficial", "m-extensor-carpi-radialis-brevis"),
            S("ecu", "right extensor carpi ulnaris", "자쪽손목폄근", "Extensor carpi ulnaris", "superficial", "m-extensor-carpi-ulnaris"),
            S("fds", "right flexor digitorum superficialis", "얕은손가락굽힘근", "Flexor digitorum superficialis", "intermediate", "m-flexor-digitorum-superficialis"),
            S("fdp", "right flexor digitorum profundus", "깊은손가락굽힘근", "Flexor digitorum profundus", "deep", "m-flexor-digitorum-profundus"),
            S("extensor_digitorum", "right extensor digitorum", "손가락폄근", "Extensor digitorum", "superficial", "m-extensor-digitorum"),
            S("apb", "right abductor pollicis brevis", "짧은엄지벌림근", "Abductor pollicis brevis", "superficial", "m-thenar", "part-of"),
            S("fpb", "superficial head of right flexor pollicis brevis", "짧은엄지굽힘근", "Flexor pollicis brevis", "superficial", "m-thenar", "part-of"),
            S("opponens_pollicis", "right opponens pollicis", "엄지맞섬근", "Opponens pollicis", "deep", "m-thenar", "part-of"),
            S("adductor_pollicis", ["oblique head of right adductor pollicis", "transverse head of right adductor pollicis"], "엄지모음근", "Adductor pollicis", "deep", "m-adductor-pollicis"),
            S("adm_hand", "abductor digiti minimi of right hand", "새끼벌림근", "Abductor digiti minimi", "superficial", "m-hypothenar", "part-of"),
            S("fdm_hand", "flexor digiti minimi brevis of right hand", "짧은새끼굽힘근", "Flexor digiti minimi brevis", "superficial", "m-hypothenar", "part-of"),
            S("odm_hand", "opponens digiti minimi of right hand", "새끼맞섬근", "Opponens digiti minimi", "deep", "m-hypothenar", "part-of"),
            S("lumbricals_hand", "set of lumbricals of right hand", "벌레근 (4개)", "Lumbricals of the hand", "intermediate", "m-lumbricals-hand"),
        ],
    },
    "leg-right": {
        "title": "오른다리 · 골반 · 허벅지 · 종아리 · 발", "region": "lower-limb", "camera": {"view": "front", "fov": 35, "fitPadding": 1.05},
        "related": ["j-hip", "j-knee", "j-ankle", "j-subtalar", "mv-hip-flexion", "mv-hip-extension", "mv-hip-abduction", "mv-knee-flexion", "mv-knee-extension",
                    "mv-ankle-dorsiflexion", "mv-ankle-plantarflexion", "mv-ankle-inversion", "mv-ankle-eversion", "mv-toe-flexion", "c-foot-arches",
                    "c-plantar-fascia", "c-gait", "c-pelvic-tilt", "c-quadriceps"],
        "structures": [
            S("hip_bone", "right hip bone", "볼기뼈", "Hip bone", "bone", "b-hip-bone"),
            S("sacrum", "sacrum", "엉치뼈", "Sacrum", "bone", "b-sacrum"),
            S("femur", "right femur", "넙다리뼈", "Femur", "bone", "b-femur"),
            S("patella", "right patella", "무릎뼈", "Patella", "bone", "b-patella"),
            S("tibia", "right tibia", "정강뼈", "Tibia", "bone", "b-tibia"),
            S("fibula", "right fibula", "종아리뼈", "Fibula", "bone", "b-fibula"),
            *[S(f"tarsal_{m}", c, ko, en, "bone", "b-tarsals", "part-of") for m, c, ko, en in
              (("talus", "right talus", "목말뼈", "Talus"), ("calcaneus", "right calcaneus", "발꿈치뼈", "Calcaneus"),
               ("navicular", "navicular bone of right foot", "발배뼈", "Navicular"), ("cuboid", "right cuboid bone", "입방뼈", "Cuboid"),
               ("medial_cuneiform", "right medial cuneiform bone", "안쪽쐐기뼈", "Medial cuneiform"),
               ("intermediate_cuneiform", "right intermediate cuneiform bone", "중간쐐기뼈", "Intermediate cuneiform"),
               ("lateral_cuneiform", "right lateral cuneiform bone", "가쪽쐐기뼈", "Lateral cuneiform"))],
            S("metatarsals", [f"right {o} metatarsal bone" for o in ORD[:5]], "발허리뼈 (1–5)", "Metatarsals", "bone", "b-metatarsals"),
            S("phalanges_foot", foot_phal, "발가락뼈 (14개)", "Phalanges of the foot", "bone", "b-phalanges-foot"),
            S("gluteus_maximus", "right gluteus maximus", "큰볼기근", "Gluteus maximus", "superficial", "m-gluteus-maximus"),
            S("gluteus_medius", "right gluteus medius", "중간볼기근", "Gluteus medius", "intermediate", "m-gluteus-medius"),
            S("gluteus_minimus", "right gluteus minimus", "작은볼기근", "Gluteus minimus", "deep", "m-gluteus-minimus"),
            S("piriformis", "right piriformis", "궁둥구멍근", "Piriformis", "deep", "m-piriformis"),
            S("tfl", "right tensor fasciae latae", "넙다리근막긴장근", "Tensor fasciae latae", "superficial", "m-tensor-fasciae-latae"),
            S("psoas_major", "right psoas major", "큰허리근", "Psoas major", "deep", "m-iliopsoas", "part-of"),
            S("iliacus", "right iliacus", "엉덩근", "Iliacus", "deep", "m-iliopsoas", "part-of"),
            S("rectus_femoris", "right rectus femoris", "넙다리곧은근", "Rectus femoris", "superficial", "m-rectus-femoris"),
            S("vastus_lateralis", "right vastus lateralis", "가쪽넓은근", "Vastus lateralis", "superficial", "m-vastus-lateralis"),
            S("vastus_medialis", "right vastus medialis", "안쪽넓은근", "Vastus medialis", "superficial", "m-vastus-medialis"),
            S("vastus_intermedius", "right vastus intermedius", "중간넓은근", "Vastus intermedius", "deep", "m-vastus-intermedius"),
            S("sartorius", "right sartorius", "넙다리빗근", "Sartorius", "superficial", "m-sartorius"),
            S("adductor_longus", "right adductor longus", "긴모음근", "Adductor longus", "superficial", "m-adductor-longus"),
            S("adductor_brevis", "right adductor brevis", "짧은모음근", "Adductor brevis", "intermediate"),
            S("adductor_magnus", "right adductor magnus", "큰모음근", "Adductor magnus", "deep", "m-adductor-magnus"),
            S("gracilis", "right gracilis", "두덩정강근", "Gracilis", "superficial", "m-gracilis"),
            S("biceps_femoris_long", "long head of right biceps femoris", "넙다리두갈래근 긴갈래", "Biceps femoris — long head", "superficial", "m-biceps-femoris", "part-of"),
            S("biceps_femoris_short", "short head of right biceps femoris", "넙다리두갈래근 짧은갈래", "Biceps femoris — short head", "deep", "m-biceps-femoris", "part-of"),
            S("semitendinosus", "right semitendinosus", "반힘줄근", "Semitendinosus", "superficial", "m-semitendinosus"),
            S("semimembranosus", "right semimembranosus", "반막근", "Semimembranosus", "deep", "m-semimembranosus"),
            S("tibialis_anterior", "right tibialis anterior", "앞정강근", "Tibialis anterior", "superficial", "m-tibialis-anterior"),
            S("tibialis_posterior", "right tibialis posterior", "뒤정강근", "Tibialis posterior", "deep", "m-tibialis-posterior"),
            S("fibularis_longus", "right fibularis longus", "긴종아리근", "Fibularis longus", "superficial", "m-fibularis-longus"),
            S("fibularis_brevis", "right fibularis brevis", "짧은종아리근", "Fibularis brevis", "deep", "m-fibularis-brevis"),
            S("gastrocnemius_medial", "medial head of right gastrocnemius", "장딴지근 안쪽갈래", "Gastrocnemius — medial head", "superficial", "m-gastrocnemius", "part-of"),
            S("gastrocnemius_lateral", "lateral head of right gastrocnemius", "장딴지근 가쪽갈래", "Gastrocnemius — lateral head", "superficial", "m-gastrocnemius", "part-of"),
            S("soleus", "right soleus", "가자미근", "Soleus", "intermediate", "m-soleus"),
            S("abductor_hallucis", "right abductor hallucis", "엄지벌림근", "Abductor hallucis", "superficial", "m-plantar-intrinsics", "part-of"),
            S("fdb_foot", "right flexor digitorum brevis", "짧은발가락굽힘근", "Flexor digitorum brevis", "superficial", "m-plantar-intrinsics", "part-of"),
            S("adm_foot", "abductor digiti minimi of right foot", "새끼벌림근 (발)", "Abductor digiti minimi of foot", "superficial", "m-plantar-intrinsics", "part-of"),
            S("lumbricals_foot", [f"{o} lumbrical of right foot" for o in ORD[:4]], "벌레근 (발)", "Lumbricals of foot", "intermediate", "m-plantar-intrinsics", "part-of"),
            S("fhb_foot", ["lateral head of right flexor hallucis brevis", "medial head of right flexor hallucis brevis"], "짧은엄지굽힘근 (발)", "Flexor hallucis brevis", "deep", "m-plantar-intrinsics", "part-of"),
            S("adductor_hallucis", ["oblique head of right adductor hallucis", "transverse head of right adductor hallucis"], "엄지모음근 (발)", "Adductor hallucis", "deep", "m-plantar-intrinsics", "part-of"),
            S("fdm_foot", "flexor digiti minimi brevis of right foot", "짧은새끼굽힘근 (발)", "Flexor digiti minimi brevis of foot", "deep", "m-plantar-intrinsics", "part-of"),
            S("plantar_interossei", [f"{o} plantar interosseous of right foot" for o in ORD[:3]], "바닥쪽뼈사이근 (발)", "Plantar interossei", "deep", "m-plantar-intrinsics", "part-of"),
        ],
    },
    "trunk": {
        "title": "몸통 · 척추 · 가슴우리 · 목", "region": "trunk", "camera": {"view": "oblique", "fov": 35, "fitPadding": 1.0},
        "related": ["j-intervertebral-disc", "j-costovertebral", "j-atlanto-joints", "c-spinal-ligaments", "c-breathing-mechanics", "mv-breathing", "mv-trunk-flexion",
                    "mv-trunk-extension", "mv-trunk-rotation", "mv-trunk-lateral-flexion", "mv-neck-flexion", "mv-neck-extension", "mv-neck-rotation",
                    "mv-neck-lateral-flexion", "c-core-stability", "m-rectus-abdominis", "m-internal-oblique", "m-transversus-abdominis", "m-quadratus-lumborum",
                    "m-multifidus", "m-longus-colli", "c-rectus-sheath"],
        "structures": [
            S("vertebra_c1", "atlas", "고리뼈 (C1)", "Atlas", "bone", "b-cervical-vertebrae", "part-of"),
            S("vertebra_c2", "axis", "중쇠뼈 (C2)", "Axis", "bone", "b-cervical-vertebrae", "part-of"),
            *[S(f"vertebra_c{i + 1}", f"{ORD[i]} cervical vertebra", f"{i + 1}번 목뼈", f"C{i + 1}", "bone", "b-cervical-vertebrae", "part-of") for i in range(2, 7)],
            *[S(f"vertebra_t{i + 1}", f"{ORD[i]} thoracic vertebra", f"{i + 1}번 등뼈", f"T{i + 1}", "bone", "b-thoracic-vertebrae", "part-of") for i in range(12)],
            *[S(f"vertebra_l{i + 1}", f"{ORD[i]} lumbar vertebra", f"{i + 1}번 허리뼈", f"L{i + 1}", "bone", "b-lumbar-vertebrae", "part-of") for i in range(5)],
            S("sacrum", "sacrum", "엉치뼈", "Sacrum", "bone", "b-sacrum"),
            S("hip_bone_r", "right hip bone", "오른쪽 볼기뼈", "Right hip bone", "bone", "b-hip-bone"),
            S("hip_bone_l", "left hip bone", "왼쪽 볼기뼈", "Left hip bone", "bone", "b-hip-bone"),
            S("manubrium", "manubrium", "복장뼈자루", "Manubrium", "bone", "b-sternum", "part-of"),
            S("sternum_body", "body of sternum", "복장뼈몸통", "Body of sternum", "bone", "b-sternum", "part-of"),
            S("ribs_r", [f"right {o} rib" for o in ORD], "오른쪽 갈비뼈 (12)", "Right ribs", "bone", "b-ribs"),
            S("ribs_l", [f"left {o} rib" for o in ORD], "왼쪽 갈비뼈 (12)", "Left ribs", "bone", "b-ribs"),
            S("costal_cartilage_r", [f"right {o} costal cartilage" for o in ORD[:7]], "오른쪽 갈비연골", "Right costal cartilages", "cartilage"),
            S("costal_cartilage_l", [f"left {o} costal cartilage" for o in ORD[:7]], "왼쪽 갈비연골", "Left costal cartilages", "cartilage"),
            S("hyoid", "hyoid bone", "목뿔뼈", "Hyoid bone", "bone", "b-hyoid"),
            S("diaphragm", "diaphragm", "가로막", "Diaphragm", "deep", "m-diaphragm"),
            S("external_intercostals", "external intercostal muscle", "바깥갈비사이근", "External intercostals", "superficial", "m-external-intercostals"),
            S("internal_intercostals", "internal intercostal muscle", "속갈비사이근", "Internal intercostals", "intermediate", "m-internal-intercostals"),
            S("sternocleidomastoid", "right sternocleidomastoid", "목빗근 (오른쪽)", "Sternocleidomastoid", "superficial", "m-sternocleidomastoid"),
            S("scalenus_anterior", "right scalenus anterior", "앞목갈비근", "Scalenus anterior", "deep", "m-scalenes", "part-of"),
            S("scalenus_medius", "right scalenus medius", "중간목갈비근", "Scalenus medius", "deep", "m-scalenes", "part-of"),
            S("scalenus_posterior", "right scalenus posterior", "뒤목갈비근", "Scalenus posterior", "deep", "m-scalenes", "part-of"),
            S("longus_capitis", "right longus capitis", "머리긴근", "Longus capitis", "deep", "m-longus-capitis"),
            S("levator_scapulae", "right levator scapulae", "어깨올림근", "Levator scapulae", "intermediate", "m-levator-scapulae"),
            S("suprahyoid", ["right digastric", "right mylohyoid", "right geniohyoid", "right stylohyoid"], "목뿔위근육", "Suprahyoid muscles", "superficial", "m-suprahyoid"),
            S("infrahyoid", ["right sternohyoid", "right omohyoid", "right sternothyroid", "right thyrohyoid"], "목뿔아래근육", "Infrahyoid muscles", "superficial", "m-infrahyoid"),
            S("iliocostalis", ["right iliocostalis lumborum", "right iliocostalis thoracis", "right iliocostalis cervicis"], "엉덩갈비근", "Iliocostalis", "intermediate", "m-erector-spinae", "part-of"),
            S("longissimus", ["right longissimus thoracis", "right longissimus cervicis", "right longissimus capitis"], "가장긴근", "Longissimus", "intermediate", "m-erector-spinae", "part-of"),
            S("spinalis", "right spinalis thoracis", "가시근", "Spinalis", "intermediate", "m-erector-spinae", "part-of"),
            S("splenius", ["right splenius capitis", "right splenius cervicis"], "머리·목널판근", "Splenius", "intermediate"),
            S("semispinalis", ["right semispinalis capitis", "right semispinalis cervicis", "right semispinalis thoracis"], "반가시근", "Semispinalis", "deep"),
            S("external_oblique", "right external oblique", "배바깥빗근", "External oblique", "superficial", "m-external-oblique"),
            S("psoas_major", "right psoas major", "큰허리근", "Psoas major", "deep", "m-iliopsoas", "part-of"),
            S("iliacus", "right iliacus", "엉덩근", "Iliacus", "deep", "m-iliopsoas", "part-of"),
        ],
    },
    "head": {
        "title": "머리뼈 · 아래턱 · 목뿔", "region": "head", "camera": {"view": "oblique", "fov": 35, "fitPadding": 1.05},
        "related": ["j-tmj", "mv-mouth-opening", "mv-mouth-closing", "mv-jaw-protrusion", "mv-jaw-lateral", "m-masseter", "m-temporalis", "m-medial-pterygoid",
                    "m-lateral-pterygoid", "b-facial-skeleton", "c-facial-nerve", "c-facial-expressions", "mv-facial-expression"],
        "notes": ["BodyParts3D 4.0에는 씹기근육(깨물근·관자근·날개근)과 얼굴 표정근 메쉬가 없습니다. 이 모델의 뼈는 실제 메쉬이며, 근육은 움직임 모드에서 이는곳·닿는곳 기준점 사이의 작용선(교육용 표시)으로만 나타냅니다."],
        "structures": [
            S("mandible", "mandible", "아래턱뼈", "Mandible", "bone", "b-mandible"),
            S("frontal", "frontal bone", "이마뼈", "Frontal bone", "bone", "b-facial-skeleton", "part-of"),
            S("parietal_r", "right parietal bone", "오른쪽 마루뼈", "Right parietal bone", "bone"),
            S("parietal_l", "left parietal bone", "왼쪽 마루뼈", "Left parietal bone", "bone"),
            S("occipital", "occipital bone", "뒤통수뼈", "Occipital bone", "bone"),
            S("temporal_r", "right temporal bone", "오른쪽 관자뼈", "Right temporal bone", "bone"),
            S("temporal_l", "left temporal bone", "왼쪽 관자뼈", "Left temporal bone", "bone"),
            S("sphenoid", "sphenoid bone", "나비뼈", "Sphenoid bone", "bone"),
            S("maxilla_r", "right maxilla", "오른쪽 위턱뼈", "Right maxilla", "bone", "b-facial-skeleton", "part-of"),
            S("maxilla_l", "left maxilla", "왼쪽 위턱뼈", "Left maxilla", "bone", "b-facial-skeleton", "part-of"),
            S("zygomatic_r", "right zygomatic bone", "오른쪽 광대뼈", "Right zygomatic bone", "bone", "b-facial-skeleton", "part-of"),
            S("zygomatic_l", "left zygomatic bone", "왼쪽 광대뼈", "Left zygomatic bone", "bone", "b-facial-skeleton", "part-of"),
            S("nasal_r", "right nasal bone", "오른쪽 코뼈", "Right nasal bone", "bone", "b-facial-skeleton", "part-of"),
            S("nasal_l", "left nasal bone", "왼쪽 코뼈", "Left nasal bone", "bone", "b-facial-skeleton", "part-of"),
            S("hyoid", "hyoid bone", "목뿔뼈", "Hyoid bone", "bone", "b-hyoid"),
            S("vertebra_c1", "atlas", "고리뼈 (C1)", "Atlas", "bone", "b-cervical-vertebrae", "part-of"),
            S("vertebra_c2", "axis", "중쇠뼈 (C2)", "Axis", "bone", "b-cervical-vertebrae", "part-of"),
            S("suprahyoid", ["right digastric", "right mylohyoid", "right geniohyoid", "right stylohyoid", "left digastric", "left mylohyoid", "left geniohyoid", "left stylohyoid"],
              "목뿔위근육 (양쪽)", "Suprahyoid muscles", "superficial", "m-suprahyoid"),
        ],
    },
    # 등 부위 층별 해부용 (V5 LAYER-001/002): 오른쪽 등 근육을 표층→심층까지 한 모델에
    "back": {
        "title": "등 · 층별 해부 (오른쪽)", "region": "back", "camera": {"view": "back", "fov": 35, "fitPadding": 1.0},
        "related": ["m-trapezius", "m-rhomboids", "m-levator-scapulae", "m-erector-spinae", "m-multifidus", "m-latissimus-dorsi",
                    "m-supraspinatus", "m-infraspinatus", "m-teres-minor", "m-teres-major", "j-scapulothoracic", "mv-scapular-upward-rotation",
                    "mv-trunk-extension", "c-core-stability"],
        "notes": ["넓은등근·뭇갈래근(다열근)·돌림근은 BodyParts3D 4.0에 메쉬가 없어 이 모델에 없습니다 (3D 모델 확보 필요).",
                  "오른쪽 등 근육만 포함합니다. 척추뼈는 가운데 전체, 갈비뼈는 오른쪽만."],
        "structures": [
            S("occipital", "occipital bone", "뒤통수뼈", "Occipital bone", "bone"),
            S("vertebra_c1", "atlas", "고리뼈 (C1)", "Atlas", "bone", "b-cervical-vertebrae", "part-of"),
            S("vertebra_c2", "axis", "중쇠뼈 (C2)", "Axis", "bone", "b-cervical-vertebrae", "part-of"),
            *[S(f"vertebra_c{i + 1}", f"{ORD[i]} cervical vertebra", f"{i + 1}번 목뼈", f"C{i + 1}", "bone", "b-cervical-vertebrae", "part-of") for i in range(2, 7)],
            *[S(f"vertebra_t{i + 1}", f"{ORD[i]} thoracic vertebra", f"{i + 1}번 등뼈", f"T{i + 1}", "bone", "b-thoracic-vertebrae", "part-of") for i in range(12)],
            *[S(f"vertebra_l{i + 1}", f"{ORD[i]} lumbar vertebra", f"{i + 1}번 허리뼈", f"L{i + 1}", "bone", "b-lumbar-vertebrae", "part-of") for i in range(5)],
            S("sacrum", "sacrum", "엉치뼈", "Sacrum", "bone", "b-sacrum"),
            S("hip_bone_r", "right hip bone", "오른쪽 볼기뼈", "Right hip bone", "bone", "b-hip-bone"),
            S("ribs_r", [f"right {o} rib" for o in ORD], "오른쪽 갈비뼈 (12)", "Right ribs", "bone", "b-ribs"),
            S("scapula", "right scapula", "어깨뼈", "Scapula", "bone", "b-scapula"),
            S("clavicle", "right clavicle", "빗장뼈", "Clavicle", "bone", "b-clavicle"),
            S("humerus", "right humerus", "위팔뼈", "Humerus", "bone", "b-humerus"),
            S("trapezius_descending", "descending part of right trapezius", "등세모근 내림부분", "Trapezius — descending part", "superficial", "m-trapezius", "part-of"),
            S("trapezius_transverse", "transverse part of right trapezius", "등세모근 가로부분", "Trapezius — transverse part", "superficial", "m-trapezius", "part-of"),
            S("trapezius_ascending", "ascending part of right trapezius", "등세모근 오름부분", "Trapezius — ascending part", "superficial", "m-trapezius", "part-of"),
            S("deltoid_posterior", "spinal part of right deltoid", "어깨세모근 뒤섬유", "Deltoid — spinal part", "superficial", "m-deltoid", "part-of"),
            S("rhomboid_minor", "right rhomboid minor", "작은마름근", "Rhomboid minor", "intermediate", "m-rhomboids", "part-of"),
            S("rhomboid_major", "right rhomboid major", "큰마름근", "Rhomboid major", "intermediate", "m-rhomboids", "part-of"),
            S("levator_scapulae", "right levator scapulae", "어깨올림근", "Levator scapulae", "intermediate", "m-levator-scapulae"),
            S("serratus_posterior_superior", "right serratus posterior superior", "위뒤톱니근", "Serratus posterior superior", "intermediate"),
            S("serratus_posterior_inferior", "right serratus posterior inferior", "아래뒤톱니근", "Serratus posterior inferior", "intermediate"),
            S("supraspinatus", "right supraspinatus", "가시위근", "Supraspinatus", "deep", "m-supraspinatus"),
            S("infraspinatus", "right infraspinatus muscle", "가시아래근", "Infraspinatus", "intermediate", "m-infraspinatus"),
            S("teres_minor", "right teres minor", "작은원근", "Teres minor", "intermediate", "m-teres-minor"),
            S("teres_major", "right teres major", "큰원근", "Teres major", "intermediate", "m-teres-major"),
            S("splenius", ["right splenius capitis", "right splenius cervicis"], "머리·목널판근", "Splenius capitis et cervicis", "intermediate"),
            S("iliocostalis", ["right iliocostalis lumborum", "right iliocostalis thoracis", "right iliocostalis cervicis"], "엉덩갈비근", "Iliocostalis", "deep", "m-erector-spinae", "part-of"),
            S("longissimus", ["right longissimus thoracis", "right longissimus cervicis", "right longissimus capitis"], "가장긴근", "Longissimus", "deep", "m-erector-spinae", "part-of"),
            S("spinalis", "right spinalis thoracis", "가시근", "Spinalis", "deep", "m-erector-spinae", "part-of"),
            S("semispinalis", ["right semispinalis capitis", "right semispinalis cervicis", "right semispinalis thoracis"], "반가시근", "Semispinalis", "deep"),
            S("interspinales", ["right interspinalis thoracis", "set of interspinales lumborum", "set of interspinales cervicis"], "가시사이근", "Interspinales", "deep"),
            S("intertransversarii", ["lateral lumbar intertransversarius", "medial lumbar intertransversarius"], "가로돌기사이근 (허리)", "Lumbar intertransversarii", "deep"),
        ],
    },
}


def main():
    zpath = sys.argv[1]
    rows = collections.defaultdict(list)
    fma = {}
    for line in open(os.path.join(ROOT, "sources", "bodyparts3d", "isa_element_parts.txt"), encoding="utf-8"):
        p = line.rstrip("\n").split("\t")
        if len(p) == 3 and p[2].startswith("FJ"):
            rows[p[1]].append(p[2])
            fma[p[1]] = p[0]
    items = {i["id"]: i for i in json.load(open(os.path.join(ROOT, "data", "items.json"), encoding="utf-8"))}
    z = zipfile.ZipFile(zpath)
    names = set(z.namelist())
    reg_path = os.path.join(ROOT, "data", "models3d.json")
    reg = json.load(open(reg_path, encoding="utf-8"))
    missing = []
    for rid, R in REGIONS.items():
        meshes = []
        for s in R["structures"]:
            fjs, fmas, srcn = [], [], []
            for c in s["concepts"]:
                if c not in rows:
                    missing.append(f"{rid}:{s['mesh']}:{c}")
                    continue
                fjs += rows[c]
                fmas.append(fma[c])
                srcn.append(c)
            if not fjs:
                continue
            for fj in fjs:
                n = f"isa_BP3D_4.0_obj_99/{fj}.obj"
                if n in names:
                    out = os.path.join(ROOT, "sources", "bodyparts3d", "obj", f"{fj}.obj")
                    if not os.path.exists(out):
                        open(out, "wb").write(z.read(n))
                else:
                    missing.append(f"{rid}:{s['mesh']}:{fj}.obj")
            it = items.get(s["item"]) if s["item"] else None
            cat = {"bone": "bone", "cartilage": "cartilage"}.get(s["layer"], "muscle")
            meshes.append({
                "meshId": s["mesh"], "sourceId": fjs if len(fjs) > 1 else fjs[0], "fmaId": fmas if len(fmas) > 1 else fmas[0],
                "sourceName": srcn if len(srcn) > 1 else srcn[0], "anatomyItemId": s["item"],
                "mappingStatus": "linked" if s["item"] else "unlinked", "mappingRelation": s["rel"],
                "koreanName": s["ko"], "englishName": s["en"], "latinName": (it or {}).get("latinName", "") if s["rel"] == "same" else "",
                "category": cat, "layer": s["layer"], "reviewStatus": "needs-review",
            })
        mp = f"data/mappings/{rid}.json"
        json.dump({"modelId": rid, "source": "BodyParts3D 4.0 isa_BP3D_4.0_obj_99", "meshes": meshes},
                  open(os.path.join(ROOT, mp), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        base = next(m for m in reg["models"] if m["id"] == "shoulder-right")
        entry = next((m for m in reg["models"] if m["id"] == rid), None)
        if not entry:
            entry = {"id": rid}
            reg["models"].append(entry)
        entry.update({"title": R["title"], "url": f"models/{rid}.glb", "region": R["region"], "side": "right",
                      "reviewStatus": "needs-review", "relatedItems": R["related"], "source": base["source"],
                      "notes": R.get("notes", []), "mapping": mp, "camera": R["camera"]})
        print(rid, len(meshes), "meshes", sum(1 for m in meshes if m["anatomyItemId"]), "linked")
    json.dump(reg, open(reg_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("missing:", missing)


if __name__ == "__main__":
    main()
