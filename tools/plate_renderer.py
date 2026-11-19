"""
해부학 도판 렌더러 — Python 표준 라이브러리만 사용 (numpy·PIL 없이 동작)

BodyParts3D 메쉬(GLB)를 정사영(orthographic)으로 직접 래스터화해 교재 스타일 도판을 만듭니다.
  - Z-버퍼 + 정점 법선 보간(Gouraud) 음영, 구조별 단색
  - ID 버퍼로 외곽선(실루엣·구조 경계) 그리기
  - 2배 슈퍼샘플링 후 축소(안티에일리어싱)
  - 명칭 설명선 위치는 'ID 버퍼에서 그 구조가 실제로 보이는 픽셀'로 계산
  - 결과: PNG(그림) + SVG(그림을 내장하고 설명선·명칭·방향 표시를 벡터로 얹음)

형상은 원본 모델 그대로이며, 색·외곽선·설명선·부착 영역 표시는 이 도구가 덧붙인 것입니다.
"""
import base64
import json
import math
import os
import struct
import zlib

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


# ------------------------------------------------------------------ GLB 읽기
def read_glb(path):
    data = open(path, "rb").read()
    jlen = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + jlen])
    binary = data[20 + jlen + 8:]

    def acc(i):
        a = gltf["accessors"][i]
        bv = gltf["bufferViews"][a["bufferView"]]
        start = bv.get("byteOffset", 0)
        n = a["count"]
        if a["type"] == "VEC3":
            return list(struct.iter_unpack("<3f", binary[start:start + 12 * n]))
        if a["componentType"] == 5125:
            return list(struct.unpack_from(f"<{n}I", binary, start))
        return list(struct.unpack_from(f"<{n}H", binary, start))

    meshes = {}
    for node in gltf["nodes"]:
        prim = gltf["meshes"][node["mesh"]]["primitives"][0]
        pos = acc(prim["attributes"]["POSITION"])
        nor = acc(prim["attributes"]["NORMAL"])
        idx = acc(prim["indices"])
        meshes[node["name"]] = {"v": pos, "n": nor, "f": [tuple(idx[i:i + 3]) for i in range(0, len(idx), 3)]}
    return meshes


# ------------------------------------------------------------------ 벡터
def norm(v):
    l = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / l for c in v)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rotate_point(p, center, axis, deg):
    """Rodrigues 회전"""
    a = math.radians(deg)
    k = norm(axis)
    v = (p[0] - center[0], p[1] - center[1], p[2] - center[2])
    c, s = math.cos(a), math.sin(a)
    kv = cross(k, v)
    kd = dot(k, v)
    r = tuple(v[i] * c + kv[i] * s + k[i] * kd * (1 - c) for i in range(3))
    return (r[0] + center[0], r[1] + center[1], r[2] + center[2])


def rotate_vec(v, axis, deg):
    return rotate_point(v, (0, 0, 0), axis, deg)


# ------------------------------------------------------------------ 카메라
class View:
    """dir: 모델 → 카메라 방향, up: 화면 위쪽"""

    def __init__(self, direction, up=(0, 1, 0)):
        self.d = norm(direction)
        r = cross(up, self.d)
        if abs(sum(c * c for c in r)) < 1e-9:
            r = cross((0, 0, -1), self.d)
        self.r = norm(r)
        self.u = norm(cross(self.d, self.r))

    def project(self, p):
        return dot(p, self.r), dot(p, self.u), dot(p, self.d)

    def to_view(self, n):
        return dot(n, self.r), dot(n, self.u), dot(n, self.d)


# ------------------------------------------------------------------ 래스터화
class Canvas:
    def __init__(self, w, h, bg=(253, 252, 249)):
        self.w, self.h = w, h
        self.z = [-1e30] * (w * h)
        self.id = [0] * (w * h)
        self.r = bytearray([bg[0]]) * (w * h)
        self.g = bytearray([bg[1]]) * (w * h)
        self.b = bytearray([bg[2]]) * (w * h)
        self.bg = bg

    def tri(self, p0, p1, p2, c0, c1, c2, mid):
        """p = (x, y, depth) 화면 좌표, c = (r, g, b) 정점 색"""
        x0, y0, z0 = p0
        x1, y1, z1 = p1
        x2, y2, z2 = p2
        area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
        if area <= 1e-9:  # 뒷면(화면 기준 시계 방향)과 퇴화 삼각형 제외
            return
        w, h = self.w, self.h
        minx = max(int(min(x0, x1, x2)), 0)
        maxx = min(int(max(x0, x1, x2)) + 1, w - 1)
        miny = max(int(min(y0, y1, y2)), 0)
        maxy = min(int(max(y0, y1, y2)) + 1, h - 1)
        if minx > maxx or miny > maxy:
            return
        inv = 1.0 / area
        zb, ib, rb, gb, bb = self.z, self.id, self.r, self.g, self.b
        for y in range(miny, maxy + 1):
            py = y + 0.5
            row = y * w
            for x in range(minx, maxx + 1):
                px = x + 0.5
                w0 = ((x1 - px) * (y2 - py) - (x2 - px) * (y1 - py)) * inv
                if w0 < 0:
                    continue
                w1 = ((x2 - px) * (y0 - py) - (x0 - px) * (y2 - py)) * inv
                if w1 < 0:
                    continue
                w2 = 1.0 - w0 - w1
                if w2 < 0:
                    continue
                z = w0 * z0 + w1 * z1 + w2 * z2
                k = row + x
                if z > zb[k]:
                    zb[k] = z
                    ib[k] = mid
                    rb[k] = int(w0 * c0[0] + w1 * c1[0] + w2 * c2[0])
                    gb[k] = int(w0 * c0[1] + w1 * c1[1] + w2 * c2[1])
                    bb[k] = int(w0 * c0[2] + w1 * c1[2] + w2 * c2[2])

    def outline(self, thick=2, sil=0.30, inner=0.62):
        """ID 경계 픽셀을 어둡게: 배경과의 경계(실루엣)는 진하게, 구조 사이 경계는 옅게"""
        w, h, ib = self.w, self.h, self.id
        mark = {}
        for y in range(h - 1):
            row = y * w
            for x in range(w - 1):
                k = row + x
                a = ib[k]
                for nb in (k + 1, k + w):
                    b = ib[nb]
                    if a != b:
                        f = sil if (a == 0 or b == 0) else inner
                        for t in range(thick):
                            for kk in (k, nb):
                                tgt = kk if t == 0 else (kk + t if kk == k else kk - t)
                                if 0 <= tgt < w * h and ib[tgt] != 0:
                                    if mark.get(tgt, 1) > f:
                                        mark[tgt] = f
                        if a == 0 or b == 0:
                            for kk in (k, nb):
                                if ib[kk] == 0:
                                    mark[kk] = min(mark.get(kk, 1), 0.55)
        rb, gb, bb, bg = self.r, self.g, self.b, self.bg
        for k, f in mark.items():
            if ib[k] == 0:
                rb[k] = int(bg[0] * f + 60 * (1 - f))
                gb[k] = int(bg[1] * f + 55 * (1 - f))
                bb[k] = int(bg[2] * f + 50 * (1 - f))
            else:
                rb[k] = int(rb[k] * f)
                gb[k] = int(gb[k] * f)
                bb[k] = int(bb[k] * f)

    def downsample(self, s=2):
        w2, h2 = self.w // s, self.h // s
        out = bytearray(w2 * h2 * 3)
        W = self.w
        rb, gb, bb = self.r, self.g, self.b
        n = s * s
        for y in range(h2):
            for x in range(w2):
                sr = sg = sb = 0
                for dy in range(s):
                    k = (y * s + dy) * W + x * s
                    for dx in range(s):
                        sr += rb[k + dx]
                        sg += gb[k + dx]
                        sb += bb[k + dx]
                o = (y * w2 + x) * 3
                out[o] = sr // n
                out[o + 1] = sg // n
                out[o + 2] = sb // n
        return w2, h2, out


def png_bytes(w, h, rgb):
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]

    def chunk(t, d):
        c = struct.pack(">I", len(d)) + t + d
        return c + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


# ------------------------------------------------------------------ 장면 렌더
LIGHT = norm((-0.45, 0.6, 0.75))  # 화면 기준: 왼쪽 위 앞에서 오는 빛


def render(meshes, items, view, size=(1200, 1000), area=(260, 40, 940, 960), ss=2, bg=(253, 252, 249),
           vertex_colors=None, transforms=None, fit_names=None, fit_points=None):
    """
    items: [(meshName, '#rrggbb')] 그릴 구조와 색 (순서 무관)
    area: 그림이 들어갈 영역 (x0, y0, x1, y1) — 나머지는 명칭 자리
    vertex_colors: {meshName: [rgb or None per vertex]} 부착 영역 등 정점별 색 덧칠
    transforms: {meshName: fn(p)->p} 위치 변환(움직임 도판), 법선도 같은 회전 적용
    fit_names: 화면 맞춤 기준 구조 (없으면 그리는 전체)
    """
    W, H = size[0] * ss, size[1] * ss
    cv = Canvas(W, H, bg)
    proj = {}
    for name, _ in items:
        m = meshes[name]
        tf = (transforms or {}).get(name)
        pts = [tf[0](p) for p in m["v"]] if tf else m["v"]
        nrm = [tf[1](n) for n in m["n"]] if tf else m["n"]
        proj[name] = ([view.project(p) for p in pts], [view.to_view(n) for n in nrm], pts)
    if fit_points:  # 여러 프레임이 같은 배율·위치를 쓰도록 고정된 점 집합으로 맞춤
        fp = [view.project(p) for p in fit_points]
        xs = [p[0] for p in fp]
        ys = [p[1] for p in fp]
    else:
        fit = fit_names or [n for n, _ in items]
        xs = [p[0] for n in fit for p in proj[n][0]]
        ys = [p[1] for n in fit for p in proj[n][0]]
    ax0, ay0, ax1, ay1 = area
    scale = min((ax1 - ax0) / (max(xs) - min(xs)), (ay1 - ay0) / (max(ys) - min(ys)))
    cx = (ax0 + ax1) / 2 - (max(xs) + min(xs)) / 2 * scale
    cy = (ay0 + ay1) / 2 + (max(ys) + min(ys)) / 2 * scale

    def to_px(p):
        return ((cx + p[0] * scale) * ss, (cy - p[1] * scale) * ss, p[2])

    ids = {}
    for i, (name, color) in enumerate(items, start=1):
        ids[i] = name
        base = hex_rgb(color)
        sp, vn, _ = proj[name]
        px = [to_px(p) for p in sp]
        vc = (vertex_colors or {}).get(name)
        cols = []
        for k, n in enumerate(vn):
            lam = max(0.0, dot(n, LIGHT))
            rim = max(0.0, n[2]) ** 0.5
            inten = 0.50 + 0.40 * lam + 0.12 * rim
            c = vc[k] if vc and vc[k] else base
            cols.append(tuple(min(255, int(ch * inten)) for ch in c))
        for a, b, c in meshes[name]["f"]:
            # 화면 y가 아래로 커지므로 정점 순서를 바꿔 앞면을 양의 넓이로
            cv.tri(px[a], px[c], px[b], cols[a], cols[c], cols[b], i)
    cv.outline(thick=2)

    def screen(p3):
        """3D 점 → 최종(축소 후) 화면 좌표"""
        q = view.project(p3)
        return cx + q[0] * scale, cy - q[1] * scale

    return cv, ids, screen, scale


def visible_anchor(cv, ids, name, ss=2, step=3):
    """그 구조가 실제로 보이는 픽셀 중, 보이는 영역의 중심에 가장 가까운 픽셀(최종 좌표)"""
    target = [k for k, v in ids.items() if v == name]
    if not target:
        return None
    t = target[0]
    w = cv.w
    pts = [(k % w, k // w) for k in range(0, len(cv.id), step) if cv.id[k] == t]
    if len(pts) < 8:
        return None
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    best = min(pts, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)
    # 경계선 위가 아니라 안쪽으로: 이웃도 같은 ID인 점 우선
    inner = [p for p in pts if all(0 <= p[0] + dx < w and cv.id[(p[1] + dy) * w + p[0] + dx] == t
                                   for dx, dy in ((6, 0), (-6, 0), (0, 6), (0, -6)) if 0 <= p[1] + dy < cv.h)]
    if inner:
        best = min(inner, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)
    return best[0] / ss, best[1] / ss, len(pts)


def anchors(cv, ids, names, ss=2, step=2):
    """여러 구조의 '보이는 픽셀' 기준 설명선 위치를 한 번에 계산 → {name: (x, y, 보이는 픽셀 수)}"""
    want = {k: v for k, v in ids.items() if v in names}
    pts = {k: [] for k in want}
    w = cv.w
    idb = cv.id
    for y in range(0, cv.h, step):
        row = y * w
        for x in range(0, w, step):
            k = idb[row + x]
            if k in pts:
                pts[k].append((x, y))
    out = {}
    for k, ps in pts.items():
        if len(ps) < 30:
            continue
        mx = sum(p[0] for p in ps) / len(ps)
        my = sum(p[1] for p in ps) / len(ps)

        def inner(p, r=10):
            return all(0 <= p[0] + dx < w and 0 <= p[1] + dy < cv.h and idb[(p[1] + dy) * w + p[0] + dx] == k
                       for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r)))
        cand = [p for p in ps if inner(p)] or ps
        best = min(cand, key=lambda p: (p[0] - mx) ** 2 + (p[1] - my) ** 2)
        out[want[k]] = (best[0] / ss, best[1] / ss, len(ps))
    return out


# ------------------------------------------------------------------ SVG 조립
FONT = "-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Noto Sans KR',sans-serif"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def layout_labels(labels, size, area, gap=40, bottom=860):
    """labels: [{x,y,text,sub,color}] → 좌우 열에 겹치지 않게 배치"""
    W, H = size
    cxm = (area[0] + area[2]) / 2
    left = sorted([l for l in labels if l["x"] < cxm], key=lambda l: l["y"])
    right = sorted([l for l in labels if l["x"] >= cxm], key=lambda l: l["y"])
    out = []
    for col, side in ((left, "L"), (right, "R")):
        ys = []
        prev = -1e9
        for l in col:
            y = max(l["y"], prev + gap)
            ys.append(y)
            prev = y
        # 아래로 넘치면 위로 밀어 올림
        over = (ys[-1] - bottom) if ys else 0  # 아래쪽 제목·방향 표시 영역은 비워 둠
        if over > 0:
            ys = [y - over for y in ys]
            for i in range(1, len(ys)):
                ys[i] = max(ys[i], ys[i - 1] + gap)
        for l, y in zip(col, ys):
            out.append({**l, "ty": max(40, y), "side": side})
    return out


def svg(path_png_bytes, size, labels, title, subtitle, credit, orient=None, extra=""):
    W, H = size
    b64 = base64.b64encode(path_png_bytes).decode()
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{FONT}">',
             f'<rect width="{W}" height="{H}" fill="#FDFCF9"/>',
             f'<image href="data:image/png;base64,{b64}" x="0" y="0" width="{W}" height="{H}"/>']
    for l in labels:
        tx = 24 if l["side"] == "L" else W - 24
        anchor = "start" if l["side"] == "L" else "end"
        lx = 230 if l["side"] == "L" else W - 230
        col = l.get("color", "#2B2F38")
        parts.append(f'<polyline points="{lx:.1f},{l["ty"]:.1f} {l["x"]:.1f},{l["y"]:.1f}" fill="none" stroke="#2B2F38" stroke-width="1.3"/>')
        parts.append(f'<circle cx="{l["x"]:.1f}" cy="{l["y"]:.1f}" r="4.5" fill="{col}" stroke="#fff" stroke-width="1.6"/>')
        sw = f'<rect x="{(tx if anchor == "start" else tx - 14)}" y="{l["ty"] - 15}" width="14" height="14" rx="3" fill="{col}"/>' if l.get("swatch") else ""
        off = 20 if l.get("swatch") else 0
        parts.append(sw)
        parts.append(f'<text x="{tx + off if anchor == "start" else tx - off}" y="{l["ty"] - 3:.1f}" font-size="19" font-weight="700" fill="#1E2A44" text-anchor="{anchor}">{esc(l["text"])}</text>')
        if l.get("sub"):
            parts.append(f'<text x="{tx + off if anchor == "start" else tx - off}" y="{l["ty"] + 17:.1f}" font-size="13" fill="#5B6170" text-anchor="{anchor}">{esc(l["sub"])}</text>')
        # 명칭 끝에서 설명선 시작점까지 가로선
        parts.append(f'<line x1="{lx:.1f}" y1="{l["ty"]:.1f}" x2="{(tx + 200) if anchor == "start" else (tx - 200):.1f}" y2="{l["ty"]:.1f}" stroke="#2B2F38" stroke-width="0.8" stroke-dasharray="2 3" opacity=".5"/>')
    if orient:
        parts.append(orient)
    parts.append(extra)
    parts.append(f'<text x="{W / 2}" y="{H - 44}" font-size="22" font-weight="700" fill="#1E2A44" text-anchor="middle">{esc(title)}</text>')
    if subtitle:
        parts.append(f'<text x="{W / 2}" y="{H - 20}" font-size="14" fill="#5B6170" text-anchor="middle">{esc(subtitle)}</text>')
    parts.append(f'<text x="{W - 12}" y="{18}" font-size="11" fill="#8A8F99" text-anchor="end">{esc(credit)}</text>')
    parts.append("</svg>")
    return "\n".join(p for p in parts if p)


def compass(view, x, y, labels):
    """방향 표시: 3D 기준축(위·앞·대상자의 왼쪽)의 화면 방향 화살표"""
    axes = [((0, 1, 0), labels.get("up", "위")), ((0, 0, 1), labels.get("front", "앞")), ((1, 0, 0), labels.get("left", "안쪽"))]
    out = [f'<g transform="translate({x},{y})" font-size="12" fill="#5B6170">',
           '<circle r="36" fill="#fff" stroke="#D2CCBE"/>']
    for v, lab in axes:
        sx, sy = dot(v, view.r), -dot(v, view.u)
        l = math.hypot(sx, sy)
        if l < 0.25:
            continue
        ex, ey = sx / l * 26, sy / l * 26
        out.append(f'<line x1="0" y1="0" x2="{ex:.1f}" y2="{ey:.1f}" stroke="#2F6F6A" stroke-width="2"/>')
        out.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="2.5" fill="#2F6F6A"/>')
        out.append(f'<text x="{ex * 1.75:.1f}" y="{ey * 1.75 + 4:.1f}" text-anchor="middle" font-weight="600">{esc(lab)}</text>')
    out.append("</g>")
    return "".join(out)
