"""
자체 제작 개념 도식(SVG) 생성기.

이 스크립트가 만드는 이미지는 모두 '개념 도식'입니다.
실제 해부학 일러스트(근육의 정확한 형태·결 방향·부착부)가 아니며,
관절 각도·자세·조직 층의 순서 같은 '개념'만 단순화해 표현합니다.

실행:  python3 tools/generate_media.py
결과:  media/ 폴더 아래에 SVG 파일 생성
"""
import math
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "media")

INK = "#1F2430"
MUTED = "#8A8F99"
ACCENT = "#2F6F6A"
WARM = "#B0563F"
FONT = "font-family=\"-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',sans-serif\""


def write(path, body, w=400, h=400):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
        f"{body}</svg>\n"
    )
    with open(full, "w", encoding="utf-8") as f:
        f.write(svg)


def text(x, y, s, size=13, fill=INK, anchor="start", weight=400):
    return (
        f'<text x="{x}" y="{y}" {FONT} font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}">{s}</text>'
    )


# ---------------------------------------------------------------- 어깨 벌림
def shoulder_abduction():
    angles = list(range(0, 181, 15))
    L = 118
    for i, a in enumerate(angles):
        parts = []
        # 바닥선
        parts.append(f'<line x1="60" y1="388" x2="340" y2="388" stroke="#D9D4C7" stroke-width="2"/>')
        # 머리·목·몸통·다리 (정면, 단순화)
        parts.append(f'<circle cx="200" cy="66" r="26" fill="none" stroke="{INK}" stroke-width="3"/>')
        parts.append(f'<line x1="200" y1="92" x2="200" y2="112" stroke="{INK}" stroke-width="3"/>')
        parts.append(
            f'<path d="M150 118 Q200 108 250 118 L242 262 Q200 272 158 262 Z" fill="#F1EEE6" stroke="{INK}" stroke-width="3"/>'
        )
        parts.append(f'<line x1="178" y1="266" x2="172" y2="384" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>')
        parts.append(f'<line x1="222" y1="266" x2="228" y2="384" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>')
        # 고정된 반대쪽 팔
        parts.append(f'<line x1="152" y1="126" x2="138" y2="250" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>')
        # 움직이는 팔: 90° 이후 어깨뼈 위쪽돌림을 단순화해 어깨점이 조금 올라가도록 표현
        lift = max(0, a - 90) / 90 * 10
        sx, sy = 248, 126 - lift
        rad = math.radians(a)
        ex, ey = sx + L * math.sin(rad), sy + L * math.cos(rad)
        # 시작 자세 기준선
        parts.append(
            f'<line x1="{sx}" y1="{sy}" x2="{sx}" y2="{sy + L}" stroke="{MUTED}" stroke-width="2" stroke-dasharray="5 5"/>'
        )
        # 각도 호
        if a > 0:
            r = 42
            x1, y1 = sx, sy + r
            x2, y2 = sx + r * math.sin(rad), sy + r * math.cos(rad)
            large = 1 if a > 180 else 0
            parts.append(
                f'<path d="M{x1:.1f} {y1:.1f} A{r} {r} 0 {large} 0 {x2:.1f} {y2:.1f}" fill="none" stroke="{ACCENT}" stroke-width="2"/>'
            )
        parts.append(
            f'<line x1="{sx}" y1="{sy:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{ACCENT}" stroke-width="13" stroke-linecap="round"/>'
        )
        parts.append(f'<circle cx="{sx}" cy="{sy:.1f}" r="7" fill="#fff" stroke="{ACCENT}" stroke-width="3"/>')
        # 주석
        # 제목·설명은 겹쳐 보기에서 글자가 겹치지 않도록 뷰어 캡션(media.json)으로 표시
        parts.append(text(380, 384, "자체 제작 개념 도식", 10, MUTED, "end"))
        write(f"movements/shoulder-abduction/f{i:02d}.svg", "".join(parts))
    return angles


# ---------------------------------------------------------------- 무릎 폄
def knee_extension():
    flex = list(range(90, -1, -10))
    for i, k in enumerate(flex):
        parts = []
        parts.append(f'<line x1="20" y1="388" x2="380" y2="388" stroke="#D9D4C7" stroke-width="2"/>')
        # 의자
        parts.append(f'<rect x="60" y="214" width="150" height="12" fill="#E4DFD3"/>')
        parts.append(f'<line x1="70" y1="226" x2="70" y2="388" stroke="#D2CCBE" stroke-width="6"/>')
        parts.append(f'<line x1="200" y1="226" x2="200" y2="388" stroke="#D2CCBE" stroke-width="6"/>')
        # 몸통(옆모습)·머리
        parts.append(f'<line x1="110" y1="200" x2="110" y2="80" stroke="{INK}" stroke-width="16" stroke-linecap="round"/>')
        parts.append(f'<circle cx="114" cy="52" r="24" fill="none" stroke="{INK}" stroke-width="3"/>')
        # 넙다리
        hx, hy, kx, ky = 110, 200, 236, 200
        parts.append(f'<line x1="{hx}" y1="{hy}" x2="{kx}" y2="{ky}" stroke="{INK}" stroke-width="16" stroke-linecap="round"/>')
        # 정강이: k=90 → 수직, k=0 → 수평
        L = 132
        a = math.radians(90 - k)
        ax, ay = kx + L * math.sin(a), ky + L * math.cos(a)
        parts.append(
            f'<line x1="{kx}" y1="{ky}" x2="{kx}" y2="{ky + L}" stroke="{MUTED}" stroke-width="2" stroke-dasharray="5 5"/>'
        )
        parts.append(
            f'<line x1="{kx}" y1="{ky}" x2="{ax:.1f}" y2="{ay:.1f}" stroke="{ACCENT}" stroke-width="14" stroke-linecap="round"/>'
        )
        # 발
        fx, fy = ax + 22 * math.cos(a), ay - 22 * math.sin(a)
        parts.append(
            f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{fx:.1f}" y2="{fy:.1f}" stroke="{ACCENT}" stroke-width="10" stroke-linecap="round"/>'
        )
        parts.append(f'<circle cx="{kx}" cy="{ky}" r="7" fill="#fff" stroke="{ACCENT}" stroke-width="3"/>')
        parts.append(text(380, 384, "자체 제작 개념 도식", 10, MUTED, "end"))
        write(f"movements/knee-extension/f{i:02d}.svg", "".join(parts))
    return flex


# ---------------------------------------------------------------- 해부학적 자세
def figure_front(back=False):
    p = []
    p.append(f'<circle cx="200" cy="58" r="26" fill="#F1EEE6" stroke="{INK}" stroke-width="3"/>')
    p.append(f'<path d="M152 104 Q200 92 248 104 L240 236 Q200 246 160 236 Z" fill="#F1EEE6" stroke="{INK}" stroke-width="3"/>')
    # 팔: 몸통 옆, 손바닥 앞쪽
    p.append(f'<line x1="154" y1="112" x2="130" y2="238" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>')
    p.append(f'<line x1="246" y1="112" x2="270" y2="238" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>')
    p.append(f'<ellipse cx="126" cy="252" rx="9" ry="14" fill="{"#F1EEE6" if back else "#D9ECE9"}" stroke="{INK}" stroke-width="2"/>')
    p.append(f'<ellipse cx="274" cy="252" rx="9" ry="14" fill="{"#F1EEE6" if back else "#D9ECE9"}" stroke="{INK}" stroke-width="2"/>')
    p.append(f'<line x1="180" y1="240" x2="176" y2="372" stroke="{INK}" stroke-width="13" stroke-linecap="round"/>')
    p.append(f'<line x1="220" y1="240" x2="224" y2="372" stroke="{INK}" stroke-width="13" stroke-linecap="round"/>')
    p.append(f'<line x1="176" y1="376" x2="164" y2="378" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>')
    p.append(f'<line x1="224" y1="376" x2="236" y2="378" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>')
    if back:
        p.append(f'<line x1="200" y1="100" x2="200" y2="236" stroke="{MUTED}" stroke-width="2" stroke-dasharray="4 4"/>')
    else:
        p.append(f'<circle cx="200" cy="190" r="3" fill="{MUTED}"/>')
    return p


def anatomical_position():
    p = figure_front()
    p.append(text(20, 396, "손바닥이 앞을 향함 (청록색)", 12, MUTED))
    p.append(text(60, 200, "몸의 오른쪽", 12, WARM, "middle"))
    p.append(text(340, 200, "몸의 왼쪽", 12, WARM, "middle"))
    p.append(text(380, 396, "자체 제작 개념 도식", 10, MUTED, "end"))
    write("basics/anatomical-position/front.svg", "".join(p))

    p = figure_front(back=True)
    p.append(text(20, 396, "점선: 몸의 정중선", 12, MUTED))
    p.append(text(60, 200, "몸의 왼쪽", 12, WARM, "middle"))
    p.append(text(340, 200, "몸의 오른쪽", 12, WARM, "middle"))
    p.append(text(380, 396, "자체 제작 개념 도식", 10, MUTED, "end"))
    write("basics/anatomical-position/back.svg", "".join(p))

    # 옆면(왼쪽에서 본 모습): 얼굴이 왼쪽을 향함
    p = []
    p.append(f'<circle cx="200" cy="58" r="26" fill="#F1EEE6" stroke="{INK}" stroke-width="3"/>')
    p.append(f'<path d="M180 60 L172 66 L180 70" fill="none" stroke="{INK}" stroke-width="2"/>')
    p.append(f'<path d="M184 100 Q206 96 220 104 L218 236 Q200 244 182 236 Z" fill="#F1EEE6" stroke="{INK}" stroke-width="3"/>')
    p.append(f'<line x1="200" y1="112" x2="200" y2="240" stroke="{INK}" stroke-width="12" stroke-linecap="round"/>')
    p.append(f'<ellipse cx="200" cy="254" rx="5" ry="14" fill="#D9ECE9" stroke="{INK}" stroke-width="2"/>')
    p.append(f'<line x1="200" y1="240" x2="200" y2="372" stroke="{INK}" stroke-width="14" stroke-linecap="round"/>')
    p.append(f'<line x1="200" y1="376" x2="176" y2="378" stroke="{INK}" stroke-width="8" stroke-linecap="round"/>')
    p.append(text(20, 396, "얼굴이 향한 쪽 = 앞쪽", 12, MUTED))
    p.append(text(110, 200, "앞쪽", 12, WARM, "middle"))
    p.append(text(290, 200, "뒤쪽", 12, WARM, "middle"))
    p.append(text(380, 396, "자체 제작 개념 도식", 10, MUTED, "end"))
    write("basics/anatomical-position/left.svg", "".join(p))


def planes():
    p = figure_front()
    # 시상면 (세로, 앞-뒤 방향) — 비스듬한 평행사변형
    p.append('<polygon points="200,10 230,30 230,395 200,375" fill="#2F6F6A" fill-opacity="0.18" stroke="#2F6F6A"/>')
    # 관상면 (세로, 좌-우 방향)
    p.append('<polygon points="96,20 316,20 316,384 96,384" fill="#B0563F" fill-opacity="0.08" stroke="#B0563F" stroke-dasharray="6 4"/>')
    # 수평면
    p.append('<polygon points="60,180 320,180 350,205 90,205" fill="#3B4F7A" fill-opacity="0.18" stroke="#3B4F7A"/>')
    p.append(text(240, 26, "시상면", 12, ACCENT, weight=700))
    p.append(text(104, 38, "관상면(이마면)", 12, WARM, weight=700))
    p.append(text(352, 200, "수평면", 12, "#3B4F7A", "end", 700))
    p.append(text(380, 396, "자체 제작 개념 도식", 10, MUTED, "end"))
    write("basics/planes.svg", "".join(p))


# ---------------------------------------------------------------- 조직 층 (분리된 투명 레이어)
def ring(r_out, r_in, fill):
    # even-odd 규칙으로 도넛 모양
    return (
        f'<path fill-rule="evenodd" fill="{fill}" d="'
        f"M{200 - r_out} 200 a{r_out} {r_out} 0 1 0 {2 * r_out} 0 a{r_out} {r_out} 0 1 0 {-2 * r_out} 0 Z "
        f'M{200 - r_in} 200 a{r_in} {r_in} 0 1 0 {2 * r_in} 0 a{r_in} {r_in} 0 1 0 {-2 * r_in} 0 Z"/>'
    )


def label(y, x_target, s, color):
    return (
        f'<line x1="{x_target}" y1="{y}" x2="350" y2="{y}" stroke="{color}" stroke-width="1.2"/>'
        f'<circle cx="{x_target}" cy="{y}" r="3" fill="{color}"/>'
        + text(352, y + 4, s, 11, color)
    )


def tissue_layers():
    write("basics/tissue-layers/skin.svg", ring(150, 140, "#D9A88A") + label(60, 200, "피부", "#9C5B3E"))
    write(
        "basics/tissue-layers/subcutaneous.svg",
        ring(140, 120, "#F2DDA4") + label(90, 200, "피하조직", "#9A7B22"),
    )
    muscle = ring(120, 52, "#C77B6E")
    # 근막 경계와 근육 사이 칸막이(단순화)
    muscle += '<circle cx="200" cy="200" r="120" fill="none" stroke="#7E3A31" stroke-width="2"/>'
    for ang in (20, 110, 200, 290):
        r = math.radians(ang)
        muscle += (
            f'<line x1="{200 + 52 * math.cos(r):.1f}" y1="{200 + 52 * math.sin(r):.1f}" '
            f'x2="{200 + 120 * math.cos(r):.1f}" y2="{200 + 120 * math.sin(r):.1f}" stroke="#7E3A31" stroke-width="2"/>'
        )
    muscle += label(130, 228, "근막 · 근육", "#7E3A31")
    write("basics/tissue-layers/muscle.svg", muscle)
    bone = ring(52, 30, "#EFEAE0") + '<circle cx="200" cy="200" r="30" fill="#E6C9A8"/>'
    bone += '<circle cx="200" cy="200" r="52" fill="none" stroke="#5E5A52" stroke-width="2"/>'
    bone += label(200, 248, "뼈 (치밀뼈·골수공간)", "#5E5A52")
    write("basics/tissue-layers/bone.svg", bone)


if __name__ == "__main__":
    shoulder_abduction()
    knee_extension()
    anatomical_position()
    planes()
    tissue_layers()
    print("media generated in", os.path.abspath(ROOT))
