# 3D 모델 검사 보고서 — shoulder-right

`python3 tools/inspect_model.py` 로 생성 (GLB를 직접 읽어 검사)

## 1. 파일
- GLB: `models/shoulder-right.glb` — 6,070,464 bytes (6.07 MB), glTF 2.0
- 노드(Mesh) 55개, 삼각형 294,932개
- 등록부 통계 일치: 예
- 저작권 표기: BodyParts3D, © The Database Center for Life Science licensed under CC Attribution 4.0 International (source OBJ headers: CC Attribution-Share Alike 2.1 Japan). Derived GLB: CC BY-SA 4.0

## 2. 매핑
- 매핑 항목 55개 / GLB 노드 55개
- GLB에 있으나 매핑 없음: 0개 
- 매핑에 있으나 GLB에 없음: 0개 
- 중복 meshId: 없음
- 원본 OBJ 누락: 없음 (sources/bodyparts3d/obj)
- FJ ↔ FMA 개념명 불일치: 없음
- 존재하지 않는 anatomyItemId: 없음
- 해부학 자료(items.json)와 연결: 21개 (같은 구조 10, 부분 11)
- 연결 자료 없음(이름만 표시): 34개

| meshId | 원본 FJ | FMA | 원본 개념명 | 한글 | 레이어 | 연결 항목 | 관계 | 삼각형 | 면 방향 |
|---|---|---|---|---|---|---|---|---|---|
| skin | FJ2810 | FMA7163 | skin | 피부 (어깨 주변 잘라냄) | skin | — | — | 41,484 | 바깥(정상) |
| deltoid_anterior | FJ1468 | FMA34680 | clavicular part of right deltoid | 어깨세모근 앞섬유 (빗장부분) | superficial | m-deltoid | part-of | 2,206 | 바깥(정상) |
| deltoid_middle | FJ1467 | FMA34682 | acromial part of right deltoid | 어깨세모근 중간섬유 (봉우리부분) | superficial | m-deltoid | part-of | 1,300 | 바깥(정상) |
| deltoid_posterior | FJ1513 | FMA34684 | spinal part of right deltoid | 어깨세모근 뒤섬유 (가시부분) | superficial | m-deltoid | part-of | 1,900 | 바깥(정상) |
| pecmaj_clavicular | FJ1447 | FMA34690 | clavicular part of right pectoralis major | 큰가슴근 빗장부분 | superficial | m-pectoralis-major | part-of | 1,846 | 바깥(정상) |
| pecmaj_sternocostal | FJ1464 | FMA79979 | sternocostal part of right pectoralis major | 큰가슴근 복장갈비부분 | superficial | m-pectoralis-major | part-of | 7,114 | 바깥(정상) |
| pecmaj_abdominal | FJ1446 | FMA45874 | abdominal part of right pectoralis major | 큰가슴근 배부분 | superficial | m-pectoralis-major | part-of | 1,536 | 바깥(정상) |
| trapezius_descending | FJ1521 | FMA33586 | descending part of right trapezius | 등세모근 내림부분 (위섬유) | superficial | m-trapezius | part-of | 7,108 | 바깥(정상) |
| trapezius_transverse | FJ1554 | FMA33584 | transverse part of right trapezius | 등세모근 가로부분 (중간섬유) | superficial | m-trapezius | part-of | 4,460 | 바깥(정상) |
| trapezius_ascending | FJ1520 | FMA33581 | ascending part of right trapezius | 등세모근 오름부분 (아래섬유) | superficial | m-trapezius | part-of | 10,530 | 바깥(정상) |
| infraspinatus | FJ1500 | FMA32547 | right infraspinatus muscle | 가시아래근 | intermediate | m-infraspinatus | same | 866 | 바깥(정상) |
| teres_minor | FJ1508 | FMA32553 | right teres minor | 작은원근 | intermediate | m-teres-minor | same | 506 | 바깥(정상) |
| teres_major | FJ1507 | FMA32551 | right teres major | 큰원근 | intermediate | m-teres-major | same | 1,042 | 바깥(정상) |
| serratus_anterior | FJ1459 | FMA13398 | right serratus anterior | 앞톱니근 | intermediate | m-serratus-anterior | same | 49,212 | 바깥(정상) |
| levator_scapulae | FJ1532 | FMA32540 | right levator scapulae | 어깨올림근 | intermediate | — | — | 4,718 | 바깥(정상) |
| rhomboid_major | FJ1536 | FMA13381 | right rhomboid major | 큰마름근 | intermediate | — | — | 7,202 | 바깥(정상) |
| rhomboid_minor | FJ1537 | FMA13383 | right rhomboid minor | 작은마름근 | intermediate | — | — | 2,206 | 바깥(정상) |
| biceps_long | FJ1478 | FMA37686 | long head of right biceps brachii | 위팔두갈래근 긴갈래 | intermediate | — | — | 1,426 | 바깥(정상) |
| biceps_short | FJ1512 | FMA37684 | short head of right biceps brachii | 위팔두갈래근 짧은갈래 | intermediate | — | — | 1,856 | 바깥(정상) |
| triceps_long | FJ1479 | FMA37699 | long head of right triceps brachii | 위팔세갈래근 긴갈래 | intermediate | — | — | 1,588 | 바깥(정상) |
| triceps_lateral | FJ1477 | FMA37697 | lateral head of right triceps brachii | 위팔세갈래근 가쪽갈래 | intermediate | — | — | 2,606 | 바깥(정상) |
| triceps_medial | FJ1480 | FMA37695 | medial head of right triceps brachii | 위팔세갈래근 안쪽갈래 | deep | — | — | 832 | 바깥(정상) |
| coracobrachialis | FJ1488 | FMA37665 | right coracobrachialis | 부리위팔근 | deep | — | — | 444 | 바깥(정상) |
| supraspinatus | FJ1506 | FMA32544 | right supraspinatus | 가시위근 | deep | m-supraspinatus | same | 878 | 바깥(정상) |
| subscapularis | FJ1504 | FMA13414 | right subscapularis | 어깨밑근 | deep | m-subscapularis | same | 2,092 | 바깥(정상) |
| pectoralis_minor | FJ1456 | FMA13375 | right pectoralis minor | 작은가슴근 | deep | m-pectoralis-minor | same | 9,468 | 바깥(정상) |
| humerus | FJ3368 | FMA23130 | right humerus | 위팔뼈 | bone | b-humerus | same | 3,784 | 바깥(정상) |
| scapula | FJ3384 | FMA13395 | right scapula | 어깨뼈 | bone | b-scapula | same | 26,172 | 바깥(정상) |
| clavicle | FJ3362 | FMA13322 | right clavicle | 빗장뼈 | bone | b-clavicle | same | 1,146 | 바깥(정상) |
| manubrium | FJ3290 | FMA7486 | manubrium | 복장뼈자루 | bone | b-sternum | part-of | 2,546 | 바깥(정상) |
| sternum_body | FJ3178 | FMA7487 | body of sternum | 복장뼈몸통 | bone | b-sternum | part-of | 4,646 | 바깥(정상) |
| rib_1 | FJ3334 | FMA7857 | right first rib | 오른쪽 1번 갈비뼈 | bone | — | — | 3,276 | 바깥(정상) |
| rib_2 | FJ3336 | FMA7882 | right second rib | 오른쪽 2번 갈비뼈 | bone | — | — | 5,594 | 바깥(정상) |
| rib_3 | FJ3338 | FMA7909 | right third rib | 오른쪽 3번 갈비뼈 | bone | — | — | 7,254 | 바깥(정상) |
| rib_4 | FJ3340 | FMA7957 | right fourth rib | 오른쪽 4번 갈비뼈 | bone | — | — | 8,832 | 바깥(정상) |
| rib_5 | FJ3342 | FMA8066 | right fifth rib | 오른쪽 5번 갈비뼈 | bone | — | — | 9,710 | 바깥(정상) |
| rib_6 | FJ3344 | FMA8175 | right sixth rib | 오른쪽 6번 갈비뼈 | bone | — | — | 10,246 | 바깥(정상) |
| rib_7 | FJ3346 | FMA8229 | right seventh rib | 오른쪽 7번 갈비뼈 | bone | — | — | 10,032 | 바깥(정상) |
| rib_8 | FJ3347 | FMA8283 | right eighth rib | 오른쪽 8번 갈비뼈 | bone | — | — | 8,336 | 바깥(정상) |
| vertebra_c7 | FJ3172 | FMA12525 | seventh cervical vertebra | 7번 목뼈 | bone | — | — | 1,820 | 바깥(정상) |
| vertebra_t1 | FJ3158 | FMA9165 | first thoracic vertebra | 1번 등뼈 | bone | — | — | 1,700 | 바깥(정상) |
| vertebra_t2 | FJ3160 | FMA9187 | second thoracic vertebra | 2번 등뼈 | bone | — | — | 1,938 | 바깥(정상) |
| vertebra_t3 | FJ3163 | FMA9209 | third thoracic vertebra | 3번 등뼈 | bone | — | — | 2,038 | 바깥(정상) |
| vertebra_t4 | FJ3166 | FMA9248 | fourth thoracic vertebra | 4번 등뼈 | bone | — | — | 2,066 | 바깥(정상) |
| vertebra_t5 | FJ3169 | FMA9922 | fifth thoracic vertebra | 5번 등뼈 | bone | — | — | 2,280 | 바깥(정상) |
| vertebra_t6 | FJ3171 | FMA9945 | sixth thoracic vertebra | 6번 등뼈 | bone | — | — | 2,248 | 바깥(정상) |
| vertebra_t7 | FJ3173 | FMA9968 | seventh thoracic vertebra | 7번 등뼈 | bone | — | — | 2,574 | 바깥(정상) |
| vertebra_t8 | FJ3174 | FMA9991 | eighth thoracic vertebra | 8번 등뼈 | bone | — | — | 2,424 | 바깥(정상) |
| costal_cartilage_1 | FJ3333 | FMA7875 | right first costal cartilage | 오른쪽 1번 갈비연골 | cartilage | — | — | 676 | 바깥(정상) |
| costal_cartilage_2 | FJ3335 | FMA7886 | right second costal cartilage | 오른쪽 2번 갈비연골 | cartilage | — | — | 658 | 바깥(정상) |
| costal_cartilage_3 | FJ3337 | FMA7913 | right third costal cartilage | 오른쪽 3번 갈비연골 | cartilage | — | — | 652 | 바깥(정상) |
| costal_cartilage_4 | FJ3339 | FMA7976 | right fourth costal cartilage | 오른쪽 4번 갈비연골 | cartilage | — | — | 694 | 바깥(정상) |
| costal_cartilage_5 | FJ3341 | FMA8070 | right fifth costal cartilage | 오른쪽 5번 갈비연골 | cartilage | — | — | 1,168 | 바깥(정상) |
| costal_cartilage_6 | FJ3343 | FMA8194 | right sixth costal cartilage | 오른쪽 6번 갈비연골 | cartilage | — | — | 1,546 | 바깥(정상) |
| costal_cartilage_7 | FJ3345 | FMA8248 | right seventh costal cartilage | 오른쪽 7번 갈비연골 | cartilage | — | — | 2,450 | 바깥(정상) |

## 3. 형상
- 면이 안쪽으로 뒤집힌 닫힌 메쉬: 없음
- 퇴화(넓이 0) 삼각형: 0개 
- 전체 경계 상자(cm): X -17.5~17.5, Y -28.6~28.6, Z -13.5~13.5
- 중심: (0.00, 0.00, 0.00) — 원점 근처면 정상

## 4. 비율 (대표 뼈 길이)
- humerus: 최대 길이 30.7 cm (참고 범위 28–38 cm) ✓
- clavicle: 최대 길이 13.6 cm (참고 범위 12–17 cm) ✓
- scapula: 최대 길이 16.6 cm (참고 범위 13–19 cm) ✓
- 방향: 위팔뼈 중심 X -9.5 < 복장뼈 중심 X 9.6 → 대상자의 오른쪽이 화면 왼쪽(-X) ✓
- 방향: 복장뼈 Z 9.9 > 등뼈 Z -5.5 → 앞쪽이 +Z ✓

## 5. 근육 ↔ 부착 뼈 접촉 (최소 거리, 0.5 cm 이내면 맞닿음)
| 근육 메쉬 | 뼈 메쉬 | 최소 거리 | 판정 |
|---|---|---|---|
| deltoid_anterior | clavicle | 0.00 cm | ✓ 맞닿음 |
| deltoid_anterior | humerus | 0.13 cm | ✓ 맞닿음 |
| deltoid_middle | scapula | 0.01 cm | ✓ 맞닿음 |
| deltoid_middle | humerus | 0.10 cm | ✓ 맞닿음 |
| deltoid_posterior | scapula | 0.03 cm | ✓ 맞닿음 |
| deltoid_posterior | humerus | 0.08 cm | ✓ 맞닿음 |
| supraspinatus | scapula | 0.04 cm | ✓ 맞닿음 |
| supraspinatus | humerus | 0.01 cm | ✓ 맞닿음 |
| infraspinatus | scapula | 0.03 cm | ✓ 맞닿음 |
| infraspinatus | humerus | 0.02 cm | ✓ 맞닿음 |
| teres_minor | scapula | 0.01 cm | ✓ 맞닿음 |
| teres_minor | humerus | 0.02 cm | ✓ 맞닿음 |
| subscapularis | scapula | 0.11 cm | ✓ 맞닿음 |
| subscapularis | humerus | 0.02 cm | ✓ 맞닿음 |
| teres_major | scapula | 0.04 cm | ✓ 맞닿음 |
| teres_major | humerus | 0.03 cm | ✓ 맞닿음 |
| pecmaj_clavicular | clavicle | 0.03 cm | ✓ 맞닿음 |
| pecmaj_clavicular | humerus | 0.18 cm | ✓ 맞닿음 |
| pecmaj_sternocostal | sternum_body | 0.03 cm | ✓ 맞닿음 |
| pecmaj_sternocostal | humerus | 0.17 cm | ✓ 맞닿음 |
| pecmaj_abdominal | humerus | 0.12 cm | ✓ 맞닿음 |
| pectoralis_minor | scapula | 0.01 cm | ✓ 맞닿음 |
| pectoralis_minor | rib_3 | 0.02 cm | ✓ 맞닿음 |
| pectoralis_minor | rib_4 | 0.03 cm | ✓ 맞닿음 |
| pectoralis_minor | rib_5 | 0.02 cm | ✓ 맞닿음 |
| serratus_anterior | scapula | 0.01 cm | ✓ 맞닿음 |
| serratus_anterior | rib_2 | 0.02 cm | ✓ 맞닿음 |
| serratus_anterior | rib_5 | 0.01 cm | ✓ 맞닿음 |
| serratus_anterior | rib_8 | 0.02 cm | ✓ 맞닿음 |
| trapezius_descending | clavicle | 0.07 cm | ✓ 맞닿음 |
| trapezius_transverse | scapula | 0.03 cm | ✓ 맞닿음 |
| trapezius_ascending | scapula | 0.03 cm | ✓ 맞닿음 |
| coracobrachialis | scapula | 0.02 cm | ✓ 맞닿음 |
| coracobrachialis | humerus | 0.07 cm | ✓ 맞닿음 |
| biceps_short | scapula | 0.02 cm | ✓ 맞닿음 |
| triceps_long | scapula | 0.02 cm | ✓ 맞닿음 |
| triceps_lateral | humerus | 0.04 cm | ✓ 맞닿음 |
| triceps_medial | humerus | 0.03 cm | ✓ 맞닿음 |
| levator_scapulae | scapula | 0.01 cm | ✓ 맞닿음 |
| rhomboid_major | scapula | 0.01 cm | ✓ 맞닿음 |
| rhomboid_minor | scapula | 0.01 cm | ✓ 맞닿음 |

### 어깨세모근 부착 위치
- 앞섬유 ↔ 빗장뼈 접촉 위치: 안쪽 끝에서 평균 82% 지점 (기대: 가쪽 1/3 = 67% 이상) ✓
- deltoid_anterior ↔ 위팔뼈 가장 아래 접촉: 위끝에서 43% 지점 (기대: 세모근거친면, 몸통 중간 위쪽 약 25–60%) ✓
- deltoid_middle ↔ 위팔뼈 가장 아래 접촉: 위끝에서 43% 지점 (기대: 세모근거친면, 몸통 중간 위쪽 약 25–60%) ✓
- deltoid_posterior ↔ 위팔뼈 가장 아래 접촉: 위끝에서 47% 지점 (기대: 세모근거친면, 몸통 중간 위쪽 약 25–60%) ✓

## 요약
- 문제 0건: 없음
