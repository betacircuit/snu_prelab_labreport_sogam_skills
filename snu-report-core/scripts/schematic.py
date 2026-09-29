#!/usr/bin/env python3
"""논리식 → 게이트 회로도 그림 (schemdraw)

  python schematic.py "F = (~A & B) | (A & ~C)" -o figs/circuit_F.png
  python schematic.py "F = ~(A & B)" -o figs/nand.png --gateH 1.2

식 문법: ~ & | ^  (logic.py와 동일). 괄호로 구조를 명시하면 그대로 그려진다.
복잡한 회로(플립플롭, 카운터 등)는 자동 배치가 어색하므로
schemdraw 코드를 직접 쓰거나 손 그림/Logisim 캡처를 쓰는 편이 낫다.
"""
from __future__ import annotations

import _console  # noqa: F401  (Windows에서 한글·기호 출력)
import argparse
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import schemdraw
from schemdraw.parsing import logicparse


def to_schemdraw_syntax(expr: str) -> str:
    e = expr.replace("&", " and ").replace("|", " or ").replace("^", " xor ")
    e = re.sub(r"~\s*", " not ", e)
    return re.sub(r"\s+", " ", e).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("eq")
    ap.add_argument("-o", "--out", default="circuit.png")
    ap.add_argument("--gateH", type=float, default=1.0)
    ap.add_argument("--gateW", type=float, default=1.8)
    a = ap.parse_args()
    name, rhs = (s.strip() for s in a.eq.split("=", 1)) if "=" in a.eq else ("F", a.eq)
    schemdraw.config(fontsize=11)
    d = logicparse(to_schemdraw_syntax(rhs), outlabel=f"${name}$", gateH=a.gateH, gateW=a.gateW)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    d.save(a.out, dpi=200)
    print("✓", a.out)


if __name__ == "__main__":
    main()
