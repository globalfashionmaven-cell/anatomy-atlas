# 해부 아틀라스 — 디지털 해부학 자료집

뼈·관절·근육·동작·개념을 하나의 검색·열람 시스템으로 관리하는 인터랙티브 해부학 학습 웹앱입니다.
빌드 도구 없이 동작하는 정적 웹앱(HTML + CSS + ES Module JavaScript)이며, 콘텐츠는 `data/*.json`에 분리되어 있습니다.

## 실행

```bash
cd 프로젝트폴더
python3 -m http.server 8000
```

브라우저에서 http://localhost:8000 을 엽니다. (`index.html`을 더블클릭해 `file://`로 열면 JSON을 불러올 수 없습니다.)
어떤 정적 호스팅(Netlify, GitHub Pages, S3 등)에도 폴더 그대로 올리면 됩니다.

## 폴더 구조

```
index.html                 레이아웃 뼈대 (사이드바 · 상단 검색 · 부위 스트립 · 하단 탭바)
assets/css/app.css         디자인 시스템 + 반응형 (PC / 태블릿 레일 / 모바일 탭바)
assets/js/main.js          해시 라우터, 상단 검색 자동 제안
assets/js/data.js          데이터 로딩, 인덱스, 양방향 연결 파생, 추천
assets/js/search.js        통합 검색 (신용어·구용어·영어·라틴어·초성·부위·기능·용어집 동의어)
assets/js/store.js         즐겨찾기·최근 본 자료·학습 완료·메모 (localStorage)
assets/js/views/           화면: dashboard, chapters, item, visual, search, library, glossary(+about)
assets/js/viewers/         뷰어: frames, overlay, layers, angles, video
data/chapters.json         15개 신체 부위
data/items.json            모든 해부학 자료 (category: bone | joint | muscle | movement | concept)
data/media.json            이미지·레이어·프레임·영상 매니페스트
data/glossary.json         용어집 (신용어 ↔ 구용어 ↔ 영어 ↔ 라틴어)
data/sources.json          출처 목록 (항목에서 id로 참조)
media/                     미디어 파일
tools/generate_media.py    자체 제작 개념 도식(SVG) 생성기
tools/make_media_manifest.py  위 도식의 media.json 생성기
```

## 콘텐츠 추가

`data/items.json`에 객체를 하나 추가하면 목차·검색·추천·이전/다음에 자동 반영됩니다.

```json
{
  "id": "m-biceps-brachii", "chapterId": "upper-arm", "category": "muscle", "order": 2,
  "koreanName": "위팔두갈래근", "oldKoreanName": ["상완이두근"],
  "englishName": "Biceps brachii", "latinName": "Musculus biceps brachii",
  "summary": "초보자용 한두 문장 설명",
  "anatomicalPosition": "", "layer": "superficial",
  "origin": [], "insertion": [], "innervation": "", "action": [], "actionKeywords": [],
  "contraction": "", "roleInMovement": "",
  "synergists": [{ "ref": "다른 항목 id 또는 이름", "note": "어떤 움직임에서" }],
  "antagonists": [], "relatedBones": [], "relatedJoints": [], "relatedMovements": [], "relatedItems": [],
  "tags": [], "sources": [{ "id": "os-11-5", "note": "쪽수 등" }],
  "reviewStatus": "needs-review"
}
```

- `category`별로 쓰는 필드가 다릅니다. 뼈: `features`, 관절: `jointType`·`articulatingBones`·`movementsAllowed`·`stabilizers`, 동작: `movementType`·`targetMuscles`·`assistingMuscles`·`antagonistMuscles`·`steps`·`overlayPresets`, 개념: `description`·`keyPoints`. 비어 있는 필드는 화면에 나타나지 않습니다.
- `synergists`·`relatedBones` 등에 아직 없는 항목의 이름을 적으면 ‘준비 중’ 칩으로 표시되고, 나중에 그 id로 항목을 만들면 자동으로 링크됩니다.
- 근육의 `relatedBones`/`relatedJoints`/`relatedMovements`만 적으면 뼈·관절·동작 쪽의 “붙는 근육 / 움직이는 근육 / 주동근” 목록은 자동으로 채워집니다.
- `actionKeywords`는 챕터의 ‘근육의 기능’ 탭에서 근육을 움직임별로 묶는 데 쓰입니다.
- `reviewStatus`: `draft`(초안) · `needs-review`(검토 필요) · `reviewed`(검토됨). 실제 전문가 검수를 마친 경우에만 `reviewed`로 바꾸고, 검토자·날짜를 `sources`의 `note`에 기록하세요.
- 새 출처는 `data/sources.json`에 추가한 뒤 항목에서 `id`로 참조합니다. 새 용어는 `data/glossary.json`에 추가하면 동의어 검색(예: 외전 → 벌림)에 바로 쓰입니다.

## 이미지·영상 교체와 등록

미디어는 항목과 분리되어 `data/media.json`에서 `anatomyItemId`로 연결됩니다. 등록된 `type`에 따라 상세 페이지에 필요한 뷰어 탭만 자동으로 나타납니다.

| type | 뷰어 | 필수 필드 |
|---|---|---|
| `image` | 2장 이상이고 `viewAngle`이 서로 다르면 다각도 갤러리, 1장이면 단일 이미지 | `url`, `viewAngle` (`front`, `oblique-left`, `left`, `back`, `right`, `oblique-right`) |
| `layer` | 레이어 ON/OFF · 단독 · 투명도 | `url`, `layer`, `layerLabel`, `layerOrder` (0이 가장 아래). **같은 크기의 투명 PNG/SVG**여야 정확히 겹칩니다 |
| `frame` | 프레임 뷰어 + 오버레이 비교 | `url`, `frameOrder`, `frameLabel` (예: "45°") |
| `video` | HTML5 비디오 (배속·역방향·프레임 이동·반복) | `url`, 선택: `poster`, `mime` |

공통 권장 필드: `id`, `title`, `description`, `altText`, `license`, `schematic`(자체 개념 도식이면 true → 화면에 ‘개념 도식’ 안내 표시).

교체만 할 때는 같은 경로에 파일을 덮어쓰면 됩니다. 브라우저 캐시 때문에 바로 안 바뀌면 강력 새로고침(Cmd+Shift+R)하세요.

## 2D 해부학 도판 (3차 — 기본 화면)

상세 페이지의 기본 탭은 **해부학 도판**입니다. 3D 뷰어는 ‘3D 관찰’ 탭에서 선택해서 보는 보조 기능이며,
도판에서 **이 시점을 3D로 보기**를 누르면 같은 시점으로 3D 뷰어가 열립니다.
탭 순서: 해부학 도판 → 움직임 분석 → 근육 구조 → 3D 관찰 → 해부학 설명. 도판이 없는 항목은 3D 또는 내용이 있는 탭이 기본입니다.

### 어깨세모근 도판 (`media/plates/deltoid/`, 31장)

| 종류 | 파일 | 내용 |
|---|---|---|
| 대표 도판 | `hero.svg` | 앞가쪽 사선. 앞섬유(빨강)·중간섬유(주황)·뒤섬유(파랑) 색 구분 + 주변 구조 명칭·설명선 |
| 다각도 7장 | `view-front/back/right/left/oblique-front/oblique-back/top.svg` | 앞면·뒷면·오른쪽 측면(가쪽)·왼쪽 측면(안쪽)·앞 사선·뒤 사선·위 |
| 섬유 구분 | `parts.svg` | 가쪽면, 주변 근육은 흐리게, 부분별 이는곳·기능 범례 |
| 이는곳 | `origin.svg` | 위에서 본 빗장뼈·어깨뼈·위팔뼈, 부분별 이는곳 영역 색칠 |
| 닿는곳 | `insertion.svg` | 가쪽에서 본 위팔뼈, 세모근거친면 영역 색칠 |
| 벌림 | `abduction/f00–f06.svg` | 0–90° (15° 간격), 앞면 |
| 굽힘 | `flexion/f00–f06.svg` | 0–90° (15° 간격), 가쪽면 |
| 폄 | `extension/f00–f05.svg` | 0–50° (10° 간격), 가쪽면 — 새 항목 `mv-shoulder-extension` |

**만드는 방법**: `python3 tools/make_deltoid_plates.py` (약 3분, Python 표준 라이브러리만 사용)
- `tools/plate_renderer.py`가 `models/shoulder-right.glb`의 메쉬를 정사영으로 직접 래스터화합니다 (Z-버퍼, 정점 법선 음영, ID 버퍼 외곽선, 2배 슈퍼샘플링).
- 설명선은 렌더링한 ID 버퍼에서 **그 구조가 실제로 보이는 픽셀**을 찾아 가리킵니다. 보이는 면적이 작은 구조에는 명칭을 달지 않습니다.
- 이는곳·닿는곳은 모델에서 근육 메쉬가 뼈 표면에 0.3cm 이내로 맞닿은 정점을 칠한 **근사 영역**입니다 (닿는곳은 위팔뼈머리를 덮는 부분을 빼려고 위끝에서 22% 아래만).
- 움직임 도판: 위팔뼈머리에 구를 맞춰(반지름 2.21cm) 회전 중심을 구하고, **위팔뼈만** 강체 회전합니다. 어깨뼈·빗장뼈는 고정이고(실제로는 어깨위팔리듬으로 함께 움직임), 근육은 변형하지 않고 이는곳→닿는곳 **작용선**과 길이 변화(%)로 표시합니다. 이 단순화는 각 도판에 적혀 있습니다.
- 결과는 `data/media.json`에 출처·라이선스·검증 상태·도판 속 명칭 목록과 함께 자동 등록됩니다 (`provenance: "model-render"`, `generator`).

**자료 구분**: 화면과 데이터에서 **모델 추출 도판**(BodyParts3D 형상을 렌더링, 색·설명선은 자체 추가)과
**자체 제작 개념 도식**(기존 SVG 도식)을 배지로 구분합니다. AI 생성 이미지는 사용하지 않았습니다.
도판 라이선스는 CC BY-SA 4.0(BodyParts3D 파생), 모두 ‘검토 필요’입니다.

**검산(도판이 해부학 서술과 맞는지)**: 벌림 60°에서 작용선이 짧아지는 것은 중간섬유(−13%)·가시위근(−15%),
굽힘 60°에서는 앞섬유(−11%)·큰가슴근 빗장부분(−14%)이고 뒤섬유는 늘어남(+20%) — 교과서의 주동근·길항근 서술과 일치합니다.

## 3D 해부학 뷰어 (2차)

상세 페이지는 5개 탭으로 구성됩니다: **3D 관찰 · 근육 구조 · 다각도 이미지 · 움직임 분석 · 해부학 설명**.
자료가 있는 탭만 나타나며, 현재 탭은 공유 링크에 `?view=3d|structure|angles|motion|info`로 남습니다
(예: `#/item/m-deltoid?view=motion`). 기존 경로 `#/item/<id>`는 그대로 동작합니다.

### 3D 모델 출처와 라이선스

| 항목 | 내용 |
|---|---|
| 자료명 | BodyParts3D 4.0 — `isa_BP3D_4.0_obj_99.zip` (99% 폴리곤 감소판, IS-A 트리) |
| 원작자 | The Database Center for Life Science (DBCLS) |
| 다운로드 출처 | https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html |
| 라이선스 | 현재 공식 페이지: CC BY 4.0 — https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html<br>⚠ 단, 2011년 배포 OBJ 파일 머리말에는 이전 라이선스 **CC BY-SA 2.1 Japan** 표기가 남아 있음 |
| 상업적 이용 | 가능 — 두 라이선스 모두 상업적 이용 허용 (출처 표기 필수). 상업 배포 전 DBCLS에 현재 조건 확인 권장 |
| 파생물 라이선스 | 보수적으로 `models/*.glb`는 CC BY-SA 4.0으로 표기·배포 권장 (BY-SA 2.1 JP의 동일조건 충족) |
| 출처 표기 | `BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International` (이전 표기: `… licensed under CC Attribution-Share Alike 2.1 Japan`) |
| 수정 여부 | 수정함 — 필요한 부위 OBJ만 골라 GLB로 변환, Y-up 좌표로 회전, cm 단위·원점 이동, 법선 재계산, 전신 피부는 어깨 주변만 잘라냄. 형상은 편집하지 않음 |

출처 표기는 3D 뷰어 하단과 `#/about` 페이지에 자동으로 표시됩니다. GLB 파일 안의 `asset.copyright`에도 기록됩니다.

Z-Anatomy(CC BY-SA 4.0)는 검토했지만 사용하지 않았습니다. 원본이 Blender(.blend) 파일이라 이 환경에서는 변환할 수 없고,
동일조건변경허락(SA) 조건 때문에 파생 모델을 같은 라이선스로 공개해야 하는 부담이 있습니다.

Three.js는 r170(MIT)을 `vendor/three/`에 고정해 두었고 `index.html`의 import map으로 불러옵니다. 외부 CDN 없이 동작합니다.

### 3D 모델 시스템 구조 (부위별 확장용)

```
data/models3d.json              모델 등록부: 레이어 그룹, 모델별 GLB 경로·매핑 파일·카메라 초기값·라이선스·통계
data/mappings/<모델id>.json      메쉬 매핑: meshId ↔ anatomyItemId (모델마다 1개)
models/<모델id>.glb              웹용 모델 (메쉬마다 개별 노드)
sources/bodyparts3d/obj/        변환에 사용한 BodyParts3D 원본 OBJ 55개 (추적·재현용)
sources/bodyparts3d/*.txt       원본 FJ ↔ FMA 개념 목록
tools/build_model_glb.py        매핑 파일을 읽어 OBJ → GLB 변환, 통계를 등록부에 기록
tools/inspect_model.py          GLB 품질 검사 → docs/3d-model-qa-<모델id>.md
```

등록부(`models3d.json`)의 모델 항목: `id`, `title`, `url`(GLB), `mapping`(매핑 파일), `camera`(`view`·`fov`·`fitPadding`),
`layers`(선택: 모델별 레이어 그룹, 없으면 공통 `layers`), `relatedItems`, `source`(자료명·원작자·출처·라이선스·상업 이용·출처 표기·수정 내역),
`fileSize`·`meshCount`·`triangles`(변환기가 자동 기록).

매핑 파일(`mappings/*.json`)의 메쉬 항목:

| 필드 | 의미 |
|---|---|
| `meshId` | GLB 노드 이름 = 뷰어 고유 ID |
| `sourceId` | BodyParts3D 원본 파일(FJxxxx.obj) |
| `fmaId`, `sourceName` | 이 FJ를 가리키는 가장 구체적인 FMA 개념 (원본 목록에서 자동 확인) |
| `anatomyItemId` | `data/items.json` 항목. 없으면 `null` (이름만 표시, ‘자료 준비 중’) |
| `mappingStatus` | `linked` / `unlinked` |
| `mappingRelation` | `same`(같은 구조) / `part-of`(항목의 한 부분 — 예: 어깨세모근 빗장부분 → m-deltoid) |
| `koreanName`, `englishName`, `latinName` | 표시 명칭 (라틴어는 TA 표기) |
| `category`, `layer` | `muscle`·`bone`·`cartilage`·`skin` / 레이어 그룹 |
| `part`, `partInfo` | 근육의 부분과 부분별 이는곳·닿는곳·기능 |
| `reviewStatus` | 모두 `needs-review` |

새 부위 추가 순서:
1. `sources/bodyparts3d/isa_parts_list_e.txt`에서 구조를 찾고 `isa_element_parts.txt`로 FJ 번호 확인
2. `data/mappings/<새id>.json` 작성 (명칭이 비슷하다고 연결하지 말고, FMA 개념이 항목과 같은 구조이거나 그 부분일 때만 `anatomyItemId` 지정)
3. `data/models3d.json`에 모델 등록 (url·mapping·camera·source)
4. 원본 OBJ를 `sources/bodyparts3d/obj/`에 두고 `python3 tools/build_model_glb.py`
5. `python3 tools/inspect_model.py <새id>`로 매핑 누락·면 방향·뼈 비율·근육-뼈 접촉 확인 (부위에 맞게 `ATTACH`·`BONE_RANGES` 추가)

```bash
python3 tools/build_model_glb.py            # 원본 OBJ → GLB, 통계 기록
python3 tools/inspect_model.py              # 검사 보고서 docs/3d-model-qa-*.md
```

### 구현된 3D 기능
- 회전(드래그·한 손가락), 확대·축소(휠·두 손가락), 이동(우클릭 드래그·두 손가락), 초기 위치, 자동 회전과 속도 조절
- 시점 7개(정면·후면·좌측·우측·상단·하단·사선) 부드러운 카메라 이동, 모델별 카메라 초기값
- Raycaster 클릭 선택, 마우스 hover 이름, 선택 강조·주변 흐리게·선택 확대·선택만 보기·전체 복구·선택 해제
- 레이어 그룹(피부·표층·중간층·심부·뼈·연골) ON/OFF·단독·투명도, 전체 표시·숨기기 — `Mesh.visible`·`material.opacity` 직접 제어
- 구조 목록: 메쉬별 ON/OFF, 이름 필터, 클릭 시 선택·확대
- 선택 정보 카드: items.json의 이는곳·닿는곳·신경·기능·협력근·길항근·관련 관절, 부분별(앞·중간·뒤섬유) 정보, ‘움직임 분석 보기’
- 지연 로딩, 탭 전환·페이지 이동 시 메모리 정리, 화면 밖 렌더링 중지, 저사양 모드, 로딩 진행률, 모델·Three.js 로딩 실패와 WebGL 미지원 안내
- GLB에 애니메이션 클립이 있으면 AnimationMixer 컨트롤 자동 표시 (현재 모델엔 클립이 없어 미시험)

### 최종 검수 결과 (2026-11-19, 브라우저에서 직접 조작)

**모델·매핑** (`docs/3d-model-qa-shoulder-right.md`)
- 원본: 공식 아카이브 OBJ 2,234개 중 55개 사용, 프로젝트에 사본 보관 · GLB 1개 `models/shoulder-right.glb` 6,070,464 bytes
- 메쉬 55개 = 매핑 55개 (누락 0, 중복 0) · 원본 FJ ↔ FMA 개념명 불일치 0
- 해부학 자료와 연결 21개 (같은 구조 10 + 부분 11), 연결 자료 없음 34개 (뼈 세부·갈비뼈·척추·연골·위팔 근육 등 — 이름만 표시)
- 메쉬 구성: 근육 25개 (그중 자료 연결 16개) + 뼈 22개 + 갈비연골 7개 + 피부 1개 = 55개, 모두 개별 선택 가능
- 면 방향 뒤집힘 0, 퇴화 삼각형 0 · 위팔뼈 30.7cm / 빗장뼈 13.6cm / 어깨뼈 16.6cm (성인 범위)
- 근육-부착 뼈 41쌍 모두 0.2cm 이내 접촉 · 어깨세모근 앞섬유는 빗장뼈 가쪽 82% 지점, 세 섬유 닿는곳은 위팔뼈 위끝에서 43–47% (세모근거친면)

**조작 (실제 마우스 입력)**: 로딩 성공, 드래그 회전, 휠 확대·축소(페이지 스크롤 안 됨), 앞·중간·뒤섬유 개별 클릭 선택과 부분별 정보 표시,
선택 강조(불투명도 1 + 발광)·나머지 흐리게(0.25), 개별 구조 숨김, 뼈 단독 보기(22개), 전체 복구(55개), 카메라 초기화 (0, 0, 126.3)로 복귀

**클릭 정확도**: Raycaster 결과와 GPU에 실제로 그려진 메쉬(ID 렌더링)를 시점별 900점씩 비교 — 정면 97.5%, 우측 100%, 후면 98.7%, 사선 100%, 어깨세모근 근접 99.2%. 불일치는 모두 메쉬 가장자리 픽셀

**해상도** (320 / 375 / 430 / 768 / 1440px): 모두 모델 로딩, 메쉬 55개 중심이 캔버스 안, 가로 넘침 없음, 캔버스가 화면 높이 안, 레이어 메뉴 열림, 탭 전환 정상.
선택 카드는 1440px에서 오른쪽 패널, 그 이하에서 3D 뷰 아래. 이 Mac에서 자동 회전 61fps, 드로우콜 56

**터치**: 합성 포인터 이벤트(pointerType: touch)로 한 손가락 회전·두 손가락 핀치 확대가 동작함을 확인. **실제 휴대폰에서는 시험하지 못했음**

**기존 기능**: 58개 경로, 통합·초성·구용어·영어·라틴어 검색, 즐겨찾기, 최근 열람, 메모, 프레임 재생, 오버레이, 다각도, 2D 레이어 — 모두 정상, 새 오류 0

**검수 중 수정한 문제**
- PC 1440×900에서 3D 캔버스가 화면보다 커서 스크롤해야 했음 → 화면 높이에 맞춤
- 회전이 너무 민감함(드래그 120px ≈ 150°) → 회전 속도 0.55, 확대 속도 0.8
- 반투명 피부가 클릭을 가로채 피부가 선택됨 → 피부는 투명도 50% 이상일 때만 선택 대상
- 아이보리 뼈가 아이보리 배경과 구분되지 않음 → 3D 배경을 회청색으로
- 320px에서 시점 버튼이 두 줄로 넘어가 모델을 가림 → 한 줄 가로 스크롤
- 매핑을 등록부에서 분리하고 원본 FMA ID·개념명·라틴어·관계를 기록 (변환 결과 GLB는 이전과 바이트 단위로 동일함을 확인)

### 3D 미구현·한계
- **근육 메쉬 변형 없음**: 동작 시뮬레이션(아래 4차)은 뼈를 강체 회전하고, 관절을 가로지르는 근육은 이는곳→닿는곳 **작용선**으로 바꿔 길이 변화를 보여 줍니다. 근육이 굵어지거나 미끄러지는 모습은 구현하지 않았습니다.
- **관절면 운동학(roll·glide 접촉 이동) 계산 없음**: 단계별 텍스트 설명으로만 제공합니다.
- **메쉬 없는 근육**: 넓은등근·배곧은근·배속빗근·배가로근·허리네모근·뭇갈래근·긴목근·손 뼈사이근, 씹기근육 4개, 얼굴근육 11개. 3D에서 선택할 수 없고 도판은 '뼈대만' 부위 도판입니다. 씹기근육은 동작 중 **가상 작용선**으로만 표시합니다.
- **관절낭·인대·관절원반 없음, 힘줄은 근육에 포함**.
- 손가락뼈·갈비뼈는 합쳐진 메쉬라 손가락 개별 동작·갈비뼈 개별 동작이 없습니다.
- 피부는 전신 메쉬를 사각 범위로 잘라내 가장자리가 들쭉날쭉합니다.
- 실제 휴대폰 터치 조작, WebGL 미지원 브라우저의 대체 화면은 실기기에서 시험하지 못했습니다.
- 모델은 한 사람의 MRI 기반 데이터입니다. 개인차가 있고, 해부학적 정확성은 ‘검토 필요’ 상태입니다.

## 4차 — 전 부위 보완 (2026-11-19)

- **모델 5개**: 어깨(`shoulder-right`) · 오른팔(`arm-right`) · 오른다리(`leg-right`) · 몸통(`trunk`, 메쉬 감량) · 머리(`head`). 빌드: `python3 tools/build_model_glb.py sources/bodyparts3d/obj <id>` (부위 정의: `tools/regions.py`).
- **관절 동작 42종**: `data/motions3d.json` (생성: `python3 tools/make_motions.py`). 3D 관찰 탭의 '동작' 패널 — 재생·속도·프레임·역재생, 역할 색(주동 빨강·협력 주황·길항 파랑·안정 초록), 수축 상태, 단계 설명. 자세한 내용: `3D_MOTION_REPORT.md`.
- **전 부위 도판**: `python3 tools/make_region_plates.py` (병렬, 8코어 기준 약 7분). 근육마다 대표 도판(시점 자동 선택) + 부착 영역 도판, 뼈마다 대표 도판, 메쉬 없는 근육은 '근육 형상 없음' 부위 뼈대 도판. 자세한 내용: `IMAGE_ASSET_REPORT.md`.
- **자동 검사**: `python3 tools/audit.py` (챕터 상태) · `python3 tools/qa.py` (데이터·이미지·모델·동작 무결성) · `tools/qa_browser.js` (브라우저 경로·탭·기능·동작 회귀). 결과: `AUDIT_REPORT.md`, `QA_REPORT.md`.

## 현재 콘텐츠 상태

- 항목 190개 (근육 89 · 뼈 26 · 관절 14 · 움직임 37 · 개념 24), 15개 챕터 모두 작성. 자세한 내용: `CONTENT_COMPLETION_REPORT.md`.
- 모든 항목·도판은 `needs-review` 상태입니다. OpenStax 등 교과서의 일반적 서술을 바탕으로 정리했지만 전문가 검수를 받지 않았습니다. 혈액 공급은 대부분 미작성('자료 확인 중').
- AI 생성 이미지는 사용하지 않았습니다. 참고 사이트(AnatoBase)의 이미지·영상·문구는 사용하지 않았습니다.

## 공개 공유용 배포 (Claude 아티팩트)

공개 공유는 이미지로 JPEG·PNG·GIF·WebP만 허용하고 `.glb`도 받지 않으므로, 원본(SVG·GLB)은 그대로 두고 배포용 사본을 만듭니다.

```bash
python3 tools/export_png_server.py        # 1) 로컬 변환 서버 (localhost:8124)
```
2) 브라우저에서 http://localhost:8124/tools/export_png.html → ‘내보내기 시작’ → `build/png/`에 PNG 62장
   (도판은 원래 크기, 400px 도식은 2배, 레이어·궤적 도식은 투명 배경 유지)

```bash
python3 tools/build_artifact.py           # 3) build/artifact/: PNG 경로로 바꾼 media.json·chapters.json, base64 모델, 업로드 목록 files.json
```
4) 공개판(2D 전용): `python3 tools/build_public.py` → `artifact-public.html` + `build/public/files.json` (모델 도판은 JPEG, 투명 도식은 PNG)
5) `artifact.html`(문서 머리 없이 본문만 있는 페이지)과 `build/artifact/files.json`의 파일을 아티팩트로 게시.
   3D 뷰어는 `.b64.json`을 받으면 GLB로 되돌려 읽습니다.
