#!/usr/bin/env python3
"""보고서용 그림 도우미 — 회로도(schemdraw)와 흑백 막대그래프 스타일

회로도 규칙 (사용자 지정)
  - 게이트 이름(N1 …)은 게이트 몸체의 정중앙 (가로·세로 모두)
  - 노드 이름($Y_1$ …)은 그 노드의 점에 붙여서
  - 점은 분기점(T자)과 이름 붙인 노드에만. 게이트 출력 버블에 붙이지 않는다
  글자는 schemdraw 라벨 대신 matplotlib text로 정확한 좌표에 찍는다
  (schemdraw 라벨은 세로 가운데 정렬이 어긋난다).

그림 검사 (save()가 자동으로 한다. 오류가 있으면 그림은 저장하되 CircuitError를 낸다)
  - 선 겹침: 같은 줄 위에서 두 선이 포개짐
  - 선 간격: 나란한 두 선이 0.3보다 가까움 (눈으로는 한 줄처럼 보인다)
  - 게이트·소자 관통: 선이 게이트 몸체나 소자를 지나가거나, 핀이 아닌 곳에서 끝남
  - 대각선·곡선 배선
  - T자 분기에 점이 없음 / 꺾임에 점이 있음 / 교차점에 점이 있음(네 갈래)
  - 글자가 선·게이트와 겹침
  - 끝이 떠 있는 선 (경고)

회로 검증 (verify): 그린 그림에서 넷리스트를 뽑아 기대 식과 진리표를 비교한다.
  NOR/XOR, NAND/AND처럼 모양이 비슷한 게이트를 잘못 그리거나, 핀을 잘못 이은 것을 잡는다.
    c.pin((0, ya), "A")                    # 입력 이름 (선 왼쪽 끝) — 검증의 입력 변수
    c.pin((12, 0), "Y", side="out")        # 출력 이름 (선 오른쪽 끝)
    c.verify({"Y": "A ^ B"}, kinds={"N1": "NAND"})

막대그래프 규칙
  - 계열 순서대로: 빈 막대(흰색 + 검은 테두리) → 검은 막대 → 빗금 막대

사용 예:
    from circuit_kit import Circuit, BAR_STYLES
    c = Circuit()
    n1 = c.gate("Nand", out_at=(4, 0), name="N1")
    c.node((4.6, 0), "$Y_1$", where="ne")
    c.save("figs/circuit.png")
"""
from __future__ import annotations

import itertools
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["mathtext.fontset"] = "dejavusans"
import schemdraw  # noqa: E402
import schemdraw.elements as elm  # noqa: E402
from schemdraw import logic  # noqa: E402

# 글자 글꼴: 본문(맑은 고딕)과 맞춘 고딕. 맑은 고딕이 없으면 Noto Sans CJK KR
from pathlib import Path as _Path  # noqa: E402
from matplotlib import font_manager as _fm  # noqa: E402

_KO_HINTS = ("notosanscjk", "notosanskr", "malgun", "nanum", "applesdgothic", "applegothic", "wqy", "sourcehansans", "gulim", "dotum")
for _f in list(_Path.home().glob(".fonts/*.tt[fc]")) + [_Path(x) for x in _fm.findSystemFonts()
                                                        if any(h in x.lower().replace(" ", "").replace("-", "") for h in _KO_HINTS)]:
    try:
        _fm.fontManager.addfont(str(_f))
    except Exception:
        pass
_AVAILABLE = {f.name for f in _fm.fontManager.ttflist}
# 한글이 되는 고딕을 앞에 (Windows 맑은 고딕, macOS Apple SD 산돌고딕 Neo, Linux Noto·나눔·문천역), 없으면 DejaVu Sans
TEXT_FAMILY = [f for f in ("Malgun Gothic", "Apple SD Gothic Neo", "AppleGothic", "Noto Sans CJK KR", "Noto Sans KR",
                           "NanumGothic", "Noto Sans CJK JP", "WenQuanYi Zen Hei") if f in _AVAILABLE] + ["DejaVu Sans"]

# schemdraw logic 게이트 치수 (schemdraw/logic/logic.py)
_LEADIN, _LEADOUT, _GATEL, _GATEH = 0.35, 0.35, 0.65, 1.0
_NOT_LEAD = 0.35   # NOT·BUFFER 삼각형 앞뒤의 짧은 입출력 선 (다른 게이트의 핀 선과 같은 길이)

BAR_STYLES = [
    {"color": "white", "edgecolor": "black", "linewidth": 0.9},                    # 1번째 계열: 빈 막대
    {"color": "black", "edgecolor": "black", "linewidth": 0.9},                    # 2번째: 검은 막대
    {"color": "white", "edgecolor": "black", "linewidth": 0.9, "hatch": "////"},   # 3번째: 빗금
]

_WHERE = {  # 점에서 글자까지 (dx, dy, ha, va)
    "ne": (0.07, 0.07, "left", "bottom"), "nw": (-0.07, 0.07, "right", "bottom"),
    "se": (0.07, -0.07, "left", "top"), "sw": (-0.07, -0.07, "right", "top"),
    "n": (0, 0.10, "center", "bottom"), "s": (0, -0.10, "center", "top"),
    "e": (0.12, 0, "left", "center"), "w": (-0.12, 0, "right", "center"),
}


def body_center(kind: str, out_at) -> tuple[float, float]:
    """출력 anchor 위치 → 게이트 몸체 중심 (뒷면 ~ 앞 곡선 끝의 가운데)."""
    k = kind.lower()
    if k in ("not", "buffer"):
        # 삼각형 (0 ~ gatel), 출력 anchor = gatel + 버블
        tri_len = _GATEL
        out_local = tri_len + (0.24 if k == "not" else 0)
        return (out_at[0] - out_local + tri_len * 0.4, out_at[1])
    out_local = _GATEL + _GATEH / 2 + _LEADIN + _LEADOUT      # 1.85
    body_mid = _LEADIN + (_GATEL + _GATEH / 2) / 2             # 0.925
    return (out_at[0] - out_local + body_mid, out_at[1])


# ───────────────────────── 게이트 종류 ─────────────────────────
# 모양이 비슷해 헷갈리는 게이트를 이름 하나로만 받는다 (Nor ↔ Xor, Nand ↔ And, Xnor ↔ Nor)
GATE_KINDS = {"and": "And", "or": "Or", "nand": "Nand", "nor": "Nor", "xor": "Xor", "xnor": "Xnor",
              "not": "Not", "buffer": "Buffer"}
GATE_INFO = {   # 종류: (74xx 2입력 칩, 모양, 진리)
    "AND": ("7408", "D자 몸체, 버블 없음", "모두 1일 때만 1"),
    "NAND": ("7400", "D자 몸체 + 출력 버블", "모두 1일 때만 0"),
    "OR": ("7432", "방패 몸체(입력 쪽 곡선 한 줄), 버블 없음", "하나라도 1이면 1"),
    "NOR": ("7402", "방패 몸체(입력 쪽 곡선 한 줄) + 출력 버블", "모두 0일 때만 1"),
    "XOR": ("7486", "방패 몸체 + 입력 쪽 곡선 두 줄, 버블 없음", "1의 개수가 홀수면 1"),
    "XNOR": ("74266", "방패 몸체 + 입력 쪽 곡선 두 줄 + 출력 버블", "1의 개수가 짝수면 1"),
    "NOT": ("7404", "삼각형 + 출력 버블", "반전"),
    "BUFFER": ("", "삼각형, 버블 없음", "그대로"),
}


def canon_kind(kind: str) -> str:
    k = str(kind).strip().lower()
    if k not in GATE_KINDS:
        raise ValueError(f"게이트 종류 '{kind}'를 모름 — {', '.join(v.upper() for v in GATE_KINDS)} 중 하나")
    return k.upper()


def _eval_gate(kind: str, xs: list[int]) -> int:
    if kind == "NOT":
        return 1 - xs[0]
    if kind == "BUFFER":
        return xs[0]
    base = {"AND": all(xs), "NAND": all(xs), "OR": any(xs), "NOR": any(xs),
            "XOR": sum(xs) % 2 == 1, "XNOR": sum(xs) % 2 == 1}[kind]
    return int(base) ^ (kind in ("NAND", "NOR", "XNOR"))


class CircuitError(Exception):
    pass


EPS = 1e-3
MIN_GAP = 0.3          # 나란한 선 사이 최소 간격 (3입력 게이트 핀 간격 0.33은 통과)
_WIRE_TYPES = ("Line", "Wire")
_SKIP_TYPES = ("Dot", "Label", "Gap")


def _norm_name(s: str) -> str:
    """'$Y_1$' → 'Y1', '$\\overline{Q}$' → 'overlineQ' (비교용)"""
    return re.sub(r"[\s${}_\\]", "", str(s))


class _Bit:
    """기대 식 계산용: ~ & | ^ 를 0/1로"""
    def __init__(self, v):
        self.v = int(v) & 1

    def __and__(self, o):
        return _Bit(self.v & _b(o))

    __rand__ = __and__

    def __or__(self, o):
        return _Bit(self.v | _b(o))

    __ror__ = __or__

    def __xor__(self, o):
        return _Bit(self.v ^ _b(o))

    __rxor__ = __xor__

    def __invert__(self):
        return _Bit(1 - self.v)


def _b(o):
    return o.v if isinstance(o, _Bit) else int(o) & 1


def _eval_expr(expr: str, env: dict[str, int]) -> int:
    e = expr.replace("!", "~")
    names = {k: _Bit(v) for k, v in env.items()}
    try:
        return _b(eval(e, {"__builtins__": {}}, names))   # noqa: S307 (식은 원고 작성자가 쓴 것)
    except NameError as err:
        raise CircuitError(f"기대 식 '{expr}'에 입력에 없는 이름이 있음: {err} — c.pin(..., side='in')으로 입력을 표시했는지") from None


def _segments(el) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    out = []
    for s in getattr(el, "segments", []):
        path = getattr(s, "path", None)
        if path is None or len(path) < 2:
            continue
        pts = [tuple(float(c) for c in el.transform.transform(p)) for p in path]
        for a, b in zip(pts, pts[1:]):
            if abs(a[0] - b[0]) > EPS or abs(a[1] - b[1]) > EPS:
                out.append((a, b))
    # 같은 방향으로 이어진 조각은 하나로 (Line의 경로는 점 세 개)
    merged = []
    for a, b in out:
        if merged:
            pa, pb = merged[-1]
            same_dir = (abs(pa[0] - pb[0]) < EPS and abs(a[0] - b[0]) < EPS and abs(pa[0] - a[0]) < EPS) or \
                       (abs(pa[1] - pb[1]) < EPS and abs(a[1] - b[1]) < EPS and abs(pa[1] - a[1]) < EPS)
            if same_dir and _close(pb, a):
                merged[-1] = (pa, b)
                continue
        merged.append((a, b))
    return merged


def _close(p, q, tol=EPS * 5):
    return abs(p[0] - q[0]) <= tol and abs(p[1] - q[1]) <= tol


def _horiz(s):
    return abs(s[0][1] - s[1][1]) < EPS


def _vert(s):
    return abs(s[0][0] - s[1][0]) < EPS


def _on_interior(p, s, tol=EPS * 5):
    """점 p가 선분 s의 양 끝이 아닌 안쪽에 있는가"""
    (x1, y1), (x2, y2) = s
    if _horiz(s):
        return abs(p[1] - y1) <= tol and min(x1, x2) + tol < p[0] < max(x1, x2) - tol
    if _vert(s):
        return abs(p[0] - x1) <= tol and min(y1, y2) + tol < p[1] < max(y1, y2) - tol
    return False


def _inside_len(s, box, pad=0.02) -> float:
    """선분이 상자 안(가장자리에서 pad 안쪽)을 지나는 길이"""
    x0, y0, x1, y1 = box[0] + pad, box[1] + pad, box[2] - pad, box[3] - pad
    if x0 >= x1 or y0 >= y1:
        return 0.0
    (ax, ay), (bx, by) = s
    if _horiz(s):
        if not (y0 < ay < y1):
            return 0.0
        return max(0.0, min(max(ax, bx), x1) - max(min(ax, bx), x0))
    if _vert(s):
        if not (x0 < ax < x1):
            return 0.0
        return max(0.0, min(max(ay, by), y1) - max(min(ay, by), y0))
    return 0.0


def _in_box(p, box, pad=0.02):
    return box[0] + pad < p[0] < box[2] - pad and box[1] + pad < p[1] < box[3] - pad


def _fmt(p):
    return f"({p[0]:.2f}, {p[1]:.2f})"


class Circuit:
    def __init__(self, fontsize=13, name_size=11, lw=1.3):
        schemdraw.config(fontsize=fontsize, lw=lw, font="sans-serif")
        self.d = schemdraw.Drawing(show=False)
        self.texts: list[tuple] = []
        self.fontsize, self.name_size = fontsize, name_size
        self.elements: list = []
        self.gates: list[dict] = []      # {kind, name, el, pins{in1.., out}}
        self.ports: list[tuple] = []     # (pt, name, side)
        self.named: list[tuple] = []     # (pt, name) — node()로 이름 붙인 점

    def add(self, element):
        self.d.add(element)
        self.elements.append(element)
        return element

    def gate(self, kind: str, out_at, name: str | None = None, inputs: int = 2):
        k = canon_kind(kind)
        cls = getattr(logic, GATE_KINDS[k.lower()])
        if k in ("NOT", "BUFFER"):
            # 2단자 소자라 기본 길이(3)면 앞뒤 선이 길다 → 몸체 + 짧은 입출력 선(_NOT_LEAD)으로 줄인다.
            # 입력선이 있어야 선이 삼각형 뒷면 가운데(입력)에 들어가는 것이 보인다. 연결은 n.start(입력), n.end(출력)
            body = _GATEL + (0.24 if k == "NOT" else 0)
            g = self.add(cls().length(body + 2 * _NOT_LEAD).right().at(out_at).anchor("end"))
            pins = {"in1": tuple(float(c) for c in g.absanchors["start"]),
                    "out": tuple(float(c) for c in g.absanchors["end"])}
            back = tuple(float(c) for c in g.absanchors["in1"])          # 삼각형 뒷면 가운데
            center = (back[0] + _GATEL * 0.4, back[1])
        else:
            g = self.add(cls(inputs=inputs).right().at(out_at).anchor("out"))   # 앞에서 down() 등을 썼어도 게이트는 항상 오른쪽을 본다
            pins = {f"in{i}": tuple(float(c) for c in g.absanchors[f"in{i}"]) for i in range(1, inputs + 1)}
            pins["out"] = tuple(float(c) for c in g.absanchors["out"])
            center = body_center(k, out_at)
        self.gates.append({"kind": k, "name": name or f"{k}{len(self.gates) + 1}", "el": g, "pins": pins, "center": center})
        if name:
            size = self.name_size * (0.75 if k in ("NOT", "BUFFER") else 1.0)  # 삼각형은 작아서 글자도 작게
            self.texts.append((center[0], center[1], name, "center", "center", size))
        return g

    def node(self, pt, name: str | None = None, where: str = "ne", dot: bool = True, port: str | None = None):
        """이름 붙인 노드. port="in"이면 검증의 입력 변수, "out"이면 출력으로도 쓴다."""
        if dot:
            self.add(elm.Dot().at(pt))
        if name:
            dx, dy, ha, va = _WHERE[where]
            self.texts.append((pt[0] + dx, pt[1] + dy, name, ha, va, self.fontsize))
            self.named.append((tuple(pt), name))
            if port:
                self.ports.append((tuple(pt), name, port))

    def pin(self, pt, name: str, side: str = "in", gap: float = 0.15):
        """입력(선 왼쪽 끝)·출력(선 오른쪽 끝) 이름. 검증에서 입력 변수·출력 이름이 된다."""
        if side not in ("in", "out"):
            raise ValueError("side는 'in' 또는 'out'")
        x = pt[0] - gap if side == "in" else pt[0] + gap
        self.texts.append((x, pt[1], name, "right" if side == "in" else "left", "center", self.fontsize))
        self.ports.append((tuple(pt), name, side))

    def text(self, pt, s, ha="center", va="center", size=None):
        self.texts.append((pt[0], pt[1], s, ha, va, size or self.fontsize))

    # ───────────────────────── 기하 정보 ─────────────────────────
    def _collect(self):
        wires, dots, parts, gate_boxes = [], [], [], []
        for el in self.elements:
            t = type(el).__name__
            if t in _WIRE_TYPES:
                for s in _segments(el):
                    wires.append((s, el))
            elif t == "Dot":
                dots.append(tuple(float(c) for c in el.absanchors["start"]))
            elif t in _SKIP_TYPES:
                continue
            else:
                bb = el.get_bbox(transform=True)
                box = (bb.xmin, bb.ymin, bb.xmax, bb.ymax)
                g = next((g for g in self.gates if g["el"] is el), None)
                if g:
                    gate_boxes.append((box, g))
                else:
                    terms = [tuple(float(c) for c in v) for k, v in el.absanchors.items()
                             if k in ("start", "end") or k.startswith(("in", "out"))]
                    parts.append((box, el, terms))
        return wires, dots, parts, gate_boxes

    def check(self, ax=None, renderer=None) -> tuple[list[str], list[str]]:
        """그림 검사 → (오류, 경고)"""
        wires, dots, parts, gate_boxes = self._collect()
        errs, warns = [], []
        segs = [s for s, _ in wires]

        # 1. 대각선·곡선
        for s in segs:
            if not (_horiz(s) or _vert(s)):
                errs.append(f"대각선 배선 {_fmt(s[0])}→{_fmt(s[1])} — Wire('-|') / Wire('|-')로 직각으로")

        # 2. 겹침과 간격
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                a, b = segs[i], segs[j]
                for is_h in (True, False):
                    if not ((_horiz(a) and _horiz(b)) if is_h else (_vert(a) and _vert(b))):
                        continue
                    ax_i = 0 if is_h else 1           # 선 방향 좌표
                    off = abs(a[0][1 - ax_i] - b[0][1 - ax_i])
                    lo = max(min(a[0][ax_i], a[1][ax_i]), min(b[0][ax_i], b[1][ax_i]))
                    hi = min(max(a[0][ax_i], a[1][ax_i]), max(b[0][ax_i], b[1][ax_i]))
                    run = hi - lo
                    where = f"{'y' if is_h else 'x'} = {a[0][1 - ax_i]:.2f}"
                    if off < EPS and run > EPS * 5:
                        errs.append(f"선 겹침: {where}에서 두 선이 {run:.2f} 길이만큼 포개짐 ({_fmt(a[0])}–{_fmt(a[1])} / {_fmt(b[0])}–{_fmt(b[1])})")
                    elif EPS <= off < MIN_GAP and run > MIN_GAP:
                        errs.append(f"선 간격 좁음: {'가로' if is_h else '세로'} 선 두 개가 {off:.2f} 간격으로 {run:.2f} 나란히 감 "
                                    f"({_fmt(a[0])}–{_fmt(a[1])} / {_fmt(b[0])}–{_fmt(b[1])}) — {MIN_GAP} 이상 띄우거나 다른 길로")

        # 3. 게이트·소자 관통, 핀 아닌 곳에서 끝남
        for box, g in gate_boxes:
            pins = list(g["pins"].values())
            for s in segs:
                if _inside_len(s, box) > EPS * 5:
                    errs.append(f"선이 게이트 {g['name']}({g['kind']}) 몸체를 지나감: {_fmt(s[0])}–{_fmt(s[1])} — 게이트 위·아래로 돌아가게")
                for p in s:
                    on_edge = box[0] - EPS <= p[0] <= box[2] + EPS and box[1] - EPS <= p[1] <= box[3] + EPS
                    if on_edge and not any(_close(p, q) for q in pins):
                        hint = " (NOT은 n.start가 입력, n.end가 출력)" if g["kind"] in ("NOT", "BUFFER") else ""
                        errs.append(f"선 끝 {_fmt(p)}이 게이트 {g['name']}({g['kind']})의 핀이 아닌 곳에 닿음 — 핀: "
                                    + ", ".join(f"{k}{_fmt(v)}" for k, v in g["pins"].items()) + hint)
            # 핀은 핀 선(lead) 끝이다. 선은 가로로 바깥쪽에서 오거나(입력은 왼쪽, 출력은 오른쪽), 세로로 와서 핀 선 끝에서 꺾인다.
            # 몸체 쪽에서 들어오거나, 선이 다른 핀을 지나가면 안 된다.
            for pk, q in g["pins"].items():
                for s in segs:
                    if _on_interior(q, s):
                        errs.append(f"선이 게이트 {g['name']}({g['kind']})의 {pk}{_fmt(q)}를 지나감: {_fmt(s[0])}–{_fmt(s[1])} — 핀마다 따로 끌어온다")
                        continue
                    if not any(_close(e, q) for e in s):
                        continue
                    other = s[1] if _close(s[0], q) else s[0]
                    wrong = _horiz(s) and (other[0] > q[0] if pk.startswith("in") else other[0] < q[0])
                    if wrong:
                        errs.append(f"게이트 {g['name']}({g['kind']}) {pk}{_fmt(q)}에 선이 몸체 쪽에서 닿음 — "
                                    f"{'입력은 왼쪽에서' if pk.startswith('in') else '출력은 오른쪽으로'} 연결")
        for box, el, terms in parts:
            for s in segs:
                if _inside_len(s, box) > EPS * 5:
                    errs.append(f"선이 {type(el).__name__} 소자를 지나감: {_fmt(s[0])}–{_fmt(s[1])}")

        # 4. 이음점: 선 끝이 다른 선 안쪽에 닿는 T자, 세 갈래 이상 모임
        ends = [p for s in segs for p in s]
        junctions = []
        for p in {(round(x, 3), round(y, 3)) for x, y in ends}:
            n_end = sum(1 for q in ends if _close(p, q))
            n_mid = sum(1 for s in segs if _on_interior(p, s))
            if n_mid or n_end >= 3:
                junctions.append(p)
        for p in junctions:
            if not any(_close(p, d) for d in dots):
                errs.append(f"T자 분기 {_fmt(p)}에 점이 없음 — c.node(pt)")
        for d in dots:
            n_end = sum(1 for q in ends if _close(d, q))
            n_mid = sum(1 for s in segs if _on_interior(d, s))
            named = any(_close(d, q) for q, _ in self.named)
            if n_mid >= 2:
                errs.append(f"교차점 {_fmt(d)}에 점 — 네 갈래 연결은 T자 두 개로 나눈다 (점 없는 교차는 연결 아님)")
            elif not named and n_mid == 0 and n_end <= 2 and not any(_close(d, q) for q in junctions):
                warns.append(f"꺾임·끝 {_fmt(d)}에 점 — 점은 분기점과 이름 붙인 노드에만")

        # 5. 떠 있는 선 끝
        anchors = [q for _, g in gate_boxes for q in g["pins"].values()] + [q for *_, ts in parts for q in ts]
        labels = [(x, y) for x, y, *_ in self.texts] + [q for q, *_ in self.ports]
        for p in ends:
            touched = (sum(1 for q in ends if _close(p, q)) >= 2 or any(_on_interior(p, s) for s in segs)
                       or any(_close(p, q) for q in anchors) or any(_close(p, d) for d in dots))
            near_label = any(abs(p[0] - q[0]) < 0.4 and abs(p[1] - q[1]) < 0.4 for q in labels)
            if not touched and not near_label:
                warns.append(f"끝이 떠 있는 선 {_fmt(p)} — 연결할 곳이 빠졌거나 이름이 없음")

        # 6. 글자와 선·게이트 겹침 (그린 뒤 글자 크기로)
        if ax is not None and renderer is not None:
            inv = ax.transData.inverted()
            for t in ax.texts:
                if not t.get_text().strip() or getattr(t, "_ck_gate_name", False):
                    continue
                bb = t.get_window_extent(renderer).transformed(inv)
                box = (bb.x0, bb.y0, bb.x1, bb.y1)
                for s in segs:
                    if _inside_len(s, box, pad=0.03) > EPS * 5:
                        errs.append(f"글자 '{t.get_text()}'가 선과 겹침 ({_fmt(s[0])}–{_fmt(s[1])}) — 글자 위치(where) 바꾸기")
                        break
                for gbox, g in gate_boxes:
                    ov = min(box[2], gbox[2]) - max(box[0], gbox[0]), min(box[3], gbox[3]) - max(box[1], gbox[1])
                    if ov[0] > 0.05 and ov[1] > 0.05:
                        errs.append(f"글자 '{t.get_text()}'가 게이트 {g['name']}와 겹침")
                        break
        return sorted(set(errs)), sorted(set(warns))

    # ───────────────────────── 넷리스트와 검증 ─────────────────────────
    def netlist(self) -> dict:
        """그림의 연결 → {inputs, outputs, gates:[{id, type, in, out}]} (pinmap.py 형식)"""
        wires, dots, parts, gate_boxes = self._collect()
        segs = [s for s, _ in wires]
        parent = list(range(len(segs)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i, j):
            parent[find(i)] = find(j)

        owner = [el for _, el in wires]
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                a, b = segs[i], segs[j]
                if owner[i] is owner[j]:
                    union(i, j)                                   # 한 선(Wire)의 조각은 한 넷
                elif any(_close(p, q) for p in a for q in b):     # 끝끼리
                    union(i, j)
                elif any(_on_interior(p, b) for p in a) or any(_on_interior(q, a) for q in b):   # T자
                    union(i, j)
                # 안쪽끼리 교차는 연결이 아니다

        def net_at(p):
            for i, s in enumerate(segs):
                if any(_close(p, q) for q in s) or _on_interior(p, s):
                    return f"n{find(i)}"
            return None

        names: dict[str, str] = {}
        for p, nm in self.named:
            n = net_at(p)
            if n:
                names.setdefault(n, _norm_name(nm))
        inputs, outputs = [], []
        for p, nm, side in self.ports:
            n = net_at(p)
            if n is None:
                raise CircuitError(f"'{nm}' 이름이 선에 닿지 않음 {_fmt(p)} — pin/node 좌표를 선 끝에")
            names[n] = _norm_name(nm)
            (inputs if side == "in" else outputs).append(_norm_name(nm))
        gates, float_pins = [], []
        for g in self.gates:
            ins = []
            for k in sorted(k for k in g["pins"] if k.startswith("in")):
                n = net_at(g["pins"][k])
                if n is None:
                    float_pins.append(f"{g['name']}.{k}")
                    n = f"?{g['name']}.{k}"
                ins.append(names.get(n, n))
            n = net_at(g["pins"]["out"]) or f"{g['name']}.out"
            names.setdefault(n, _norm_name(g["name"]) + "_out" if n.startswith("n") else n)
            gates.append({"id": g["name"], "type": g["kind"], "in": ins, "out": names.get(n, n)})
        if float_pins:
            raise CircuitError("선이 닿지 않은 게이트 입력: " + ", ".join(float_pins))
        drivers = {}
        for g in gates:
            if g["out"] in drivers:
                raise CircuitError(f"게이트 출력끼리 연결됨: {drivers[g['out']]}, {g['id']} → {g['out']}")
            drivers[g["out"]] = g["id"]
        return {"inputs": inputs, "outputs": outputs, "gates": gates}

    def simulate(self, env: dict[str, int]) -> dict[str, int] | None:
        """입력값 → 모든 넷 값. 되먹임(래치)이 있어 값이 정해지지 않으면 None"""
        nl = self.netlist()
        val = {k: int(v) for k, v in env.items()}
        for _ in range(len(nl["gates"]) + 2):
            changed = False
            for g in nl["gates"]:
                if all(x in val for x in g["in"]):
                    v = _eval_gate(g["type"], [val[x] for x in g["in"]])
                    if val.get(g["out"]) != v:
                        val[g["out"]] = v
                        changed = True
            if not changed:
                break
        else:
            return None
        return val

    def verify(self, expected: dict[str, str], kinds: dict[str, str] | None = None, quiet: bool = False) -> bool:
        """그림에서 뽑은 회로가 기대 식과 같은지 진리표 전체로 비교한다.
        expected: {"Y": "~(A & B)"}  (이름은 pin/node 이름, 식 문법은 logic.py와 같음: ~ & | ^)
        kinds:    {"N1": "NOR"}      본문에 쓴 게이트 종류와 그림이 같은지 (NOR ↔ XOR 혼동 방지)"""
        nl = self.netlist()
        errs = []
        by_id = {g["id"]: g for g in nl["gates"]}
        for gid, k in (kinds or {}).items():
            want = canon_kind(k)
            got = by_id.get(gid, {}).get("type")
            if got != want:
                errs.append(f"게이트 {gid}: 본문은 {want}({GATE_INFO[want][1]}) — 그림은 {got}")
        ins = nl["inputs"]
        if not ins:
            raise CircuitError("입력이 없음 — c.pin(pt, 'A') 또는 c.node(pt, 'A', port='in')으로 입력을 표시")
        want = {_norm_name(k): v for k, v in expected.items()}
        rows = []
        seq = False
        for bits in itertools.product([0, 1], repeat=len(ins)):
            env = dict(zip(ins, bits))
            val = self.simulate(env)
            if val is None:
                seq = True
                break
            missing = [o for o in want if o not in val]
            if missing:
                errs.append(f"{', '.join(missing)}가 그림에 없음 — 있는 이름: {', '.join(sorted(k for k in val if not k.startswith('n')))}")
                break
            for out, ex in want.items():
                exp = _eval_expr(ex, env)
                if val[out] != exp:
                    rows.append(f"{' '.join(f'{k}={v}' for k, v in env.items())}: {out} 그림 {val[out]} / 기대 {exp}")
        if seq:
            errs.append("되먹임이 있어 입력만으로 값이 정해지지 않음 — 순차 회로는 timing.py로 따로 확인")
        if rows:
            errs.append(f"진리표 불일치 {len(rows)}행:\n    " + "\n    ".join(rows[:8]))
        if not quiet:
            print("  회로 검증 — 게이트:", ", ".join(f"{g['id']} {g['type']}({len(g['in'])}입력, {GATE_INFO[g['type']][0] or '-'})" for g in nl["gates"]))
            print("               입력:", ", ".join(ins), "/ 확인한 출력:", ", ".join(want))
        if errs:
            raise CircuitError("회로 검증 실패\n  - " + "\n  - ".join(errs))
        if not quiet:
            print(f"  ✓ 회로 검증 통과 ({2 ** len(ins)}행 전부 일치)")
        return True

    def save(self, path, dpi=220, check=True):
        fig = self.d.draw(show=False)
        for x, y, s, ha, va, size in self.texts:
            t = fig.ax.text(x, y, s, ha=ha, va=va, fontsize=size, family=TEXT_FAMILY, zorder=10)
            t._ck_gate_name = any(abs(x - g["center"][0]) < EPS and s == g["name"] for g in self.gates)
        fig.save(str(path), dpi=dpi)
        if check:
            renderer = fig.fig.canvas.get_renderer()
            errs, warns = self.check(fig.ax, renderer)
            for w in warns:
                print(f"  ⚠ 회로도 {Path(str(path)).name}: {w}")
            if errs:
                raise CircuitError(f"회로도 {path} 검사 실패 (그림은 저장됨 — 열어 보고 고칠 것)\n  - " + "\n  - ".join(errs))
        return path
