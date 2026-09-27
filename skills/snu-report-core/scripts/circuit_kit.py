#!/usr/bin/env python3
"""보고서용 그림 도우미 — 회로도(schemdraw)와 흑백 막대그래프 스타일

회로도 규칙 (사용자 지정)
  - 게이트 이름(N1 …)은 게이트 몸체의 정중앙 (가로·세로 모두)
  - 노드 이름($Y_1$ …)은 그 노드의 점에 붙여서
  - 점은 분기점(T자)과 이름 붙인 노드에만. 게이트 출력 버블에 붙이지 않는다
  글자는 schemdraw 라벨 대신 matplotlib text로 정확한 좌표에 찍는다
  (schemdraw 라벨은 세로 가운데 정렬이 어긋난다).

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

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["mathtext.fontset"] = "dejavusans"
import schemdraw  # noqa: E402
import schemdraw.elements as elm  # noqa: E402
from schemdraw import logic  # noqa: E402

# 글자 글꼴: 본문(맑은 고딕)과 맞춘 고딕. 맑은 고딕이 없으면 Noto Sans CJK KR
from pathlib import Path as _Path  # noqa: E402
from matplotlib import font_manager as _fm  # noqa: E402

for _f in list(_Path.home().glob(".fonts/*.ttf")) + [_Path(x) for x in _fm.findSystemFonts() if "NotoSansCJK" in x or "malgun" in x.lower()]:
    try:
        _fm.fontManager.addfont(str(_f))
    except Exception:
        pass
_AVAILABLE = {f.name for f in _fm.fontManager.ttflist}
TEXT_FAMILY = [f for f in ("Malgun Gothic", "Noto Sans CJK KR", "Noto Sans CJK JP") if f in _AVAILABLE] + ["DejaVu Sans"]

# schemdraw logic 게이트 치수 (schemdraw/logic/logic.py)
_LEADIN, _LEADOUT, _GATEL, _GATEH = 0.35, 0.35, 0.65, 1.0

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


class Circuit:
    def __init__(self, fontsize=13, name_size=11, lw=1.3):
        schemdraw.config(fontsize=fontsize, lw=lw, font="sans-serif")
        self.d = schemdraw.Drawing(show=False)
        self.texts: list[tuple] = []
        self.fontsize, self.name_size = fontsize, name_size

    def add(self, element):
        self.d.add(element)
        return element

    def gate(self, kind: str, out_at, name: str | None = None, inputs: int = 2):
        cls = getattr(logic, kind)
        if kind.lower() in ("not", "buffer"):
            # 2단자 소자라 기본 길이(3)만큼 앞뒤로 선이 붙는다 → 몸체 길이로 줄여 선을 없앤다
            el = cls().length(_GATEL + (0.24 if kind.lower() == "not" else 0))
        else:
            el = cls(inputs=inputs)
        g = self.add(el.at(out_at).anchor("out"))
        if name:
            x, y = body_center(kind, out_at)
            size = self.name_size * (0.75 if kind.lower() in ("not", "buffer") else 1.0)  # 삼각형은 작아서 글자도 작게
            self.texts.append((x, y, name, "center", "center", size))
        return g

    def node(self, pt, name: str | None = None, where: str = "ne", dot: bool = True):
        if dot:
            self.add(elm.Dot().at(pt))
        if name:
            dx, dy, ha, va = _WHERE[where]
            self.texts.append((pt[0] + dx, pt[1] + dy, name, ha, va, self.fontsize))

    def text(self, pt, s, ha="center", va="center", size=None):
        self.texts.append((pt[0], pt[1], s, ha, va, size or self.fontsize))

    def save(self, path, dpi=220):
        fig = self.d.draw(show=False)
        for x, y, s, ha, va, size in self.texts:
            fig.ax.text(x, y, s, ha=ha, va=va, fontsize=size, family=TEXT_FAMILY, zorder=10)
        fig.save(str(path), dpi=dpi)
        return path
