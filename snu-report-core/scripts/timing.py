#!/usr/bin/env python3
"""타이밍도(예상 파형) 그리기 — prelab의 '예상 결과' 그림용

  python timing.py spec.yaml -o figs/timing.png [--json expected.json]

spec.yaml 예:
  unit: "μs"          # x축 단위 표시 (선택)
  step: 1             # 한 칸의 시간
  signals:            # 문자 하나 = 한 칸.  0/1, x(모름), 공백은 무시
    A: "0011 0011"
    B: "0101 0101"
    CLK: clk          # clk = 01 반복 (길이는 다른 신호에 맞춤)
  derive:             # 다른 신호로부터 계산 (logic.py 식 문법)
    F: "A^B"
  delay:              # 칸 단위 전파 지연 표시 (선택, 소수 가능)
    F: 0.15
  marks: [2, 4]       # 세로 점선 (선택)
  clock: CLK          # 이 신호의 에지마다 세로 점선 (선택, edge: rise | fall — 기본 rise)

순차 회로는 circuit_kit의 c.verify_seq(...) 결과를 c.timing(trace, [...], "figs/x.png")로 그리면
그림의 회로에서 계산한 파형이 그대로 들어간다 (figures.md "블록과 순차 회로").

--json 을 주면 expected.json 의 "waveforms" 에 계산된 파형을 저장 → compare.py 가 사용.
"""
from __future__ import annotations

import _console  # noqa: F401  (Windows에서 한글·기호 출력)
import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sympy as sp
import yaml
from sympy.parsing.sympy_parser import parse_expr

ACCENT = "#1F3A5F"
HI = "#C0392B"


def expand(signals: dict) -> dict[str, list]:
    raw = {k: str(v).replace(" ", "") for k, v in signals.items()}
    n = max((len(v) for v in raw.values() if v != "clk"), default=8)
    out = {}
    for k, v in raw.items():
        if v == "clk":
            v = ("01" * n)[:n]
        out[k] = [c if c in "x" else int(c) for c in v.ljust(n, v[-1])]
    return out


def derive(sig: dict, eqs: dict) -> dict:
    for name, e in (eqs or {}).items():
        syms = {k: sp.Symbol(k) for k in sig}
        expr = parse_expr(e, local_dict=syms)
        n = len(next(iter(sig.values())))
        vals = []
        for i in range(n):
            env = {syms[k]: bool(v[i]) for k, v in sig.items() if v[i] != "x"}
            r = expr.subs(env)
            vals.append(int(bool(r)) if r in (sp.true, sp.false) else "x")
        sig[name] = vals
    return sig


def draw(sig, spec, out):
    names = list(sig)
    n = len(sig[names[0]])
    step = spec.get("step", 1)
    delay = spec.get("delay", {}) or {}
    fig, ax = plt.subplots(figsize=(max(5, 0.55 * n + 1.5), 0.62 * len(names) + 0.7), dpi=200)
    for row, name in enumerate(names):
        y0 = -row * 1.5
        vals = sig[name]
        d = delay.get(name, 0) * step
        xs, ys = [0], [vals[0] if vals[0] != "x" else 0.5]
        for i, v in enumerate(vals):
            t0 = i * step + (d if i > 0 else 0)
            yv = 0.5 if v == "x" else v
            xs += [t0, t0]
            ys += [ys[-1], yv]
            if v == "x":
                ax.add_patch(plt.Rectangle((t0, y0), step, 0.8, fc="#DDDDDD", ec="none"))
        xs.append(n * step)
        ys.append(ys[-1])
        color = HI if name in (spec.get("derive") or {}) else ACCENT
        ax.plot(xs, [y0 + 0.8 * y for y in ys], color=color, lw=1.6, solid_joinstyle="miter")
        ax.text(-0.25 * step, y0 + 0.4, name, ha="right", va="center", fontsize=10, family="monospace")
    for i in range(n + 1):
        ax.axvline(i * step, color="#EEEEEE", lw=0.6, zorder=0)
    marks = list(spec.get("marks", []) or [])
    ck = spec.get("clock")
    if ck in sig:   # clock 에지마다 점선
        want = (1, 0) if spec.get("edge") == "fall" else (0, 1)
        v = sig[ck]
        marks += [i for i in range(1, len(v)) if (v[i - 1], v[i]) == want]
    for m in marks:
        ax.axvline(m * step, color="#888", lw=0.8, ls="--")
    unit = spec.get("unit", "")
    ax.set_xticks([i * step for i in range(n + 1)])
    ax.set_xticklabels([f"{i * step:g}" for i in range(n + 1)], fontsize=7, color="#666")
    if unit:
        ax.set_xlabel(f"t [{unit}]", fontsize=8, color="#666")
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.set_xlim(-0.05 * step, n * step)
    ax.set_ylim(-(len(names) - 1) * 1.5 - 0.3, 1.1)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    print("✓", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", default="timing.png")
    ap.add_argument("--json")
    a = ap.parse_args()
    spec = yaml.safe_load(Path(a.spec).read_text(encoding="utf-8"))
    sig = derive(expand(spec["signals"]), spec.get("derive"))
    draw(sig, spec, a.out)
    if a.json:
        p = Path(a.json)
        data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        data.setdefault("waveforms", {}).update({k: v for k, v in sig.items()})
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print("✓", p)


if __name__ == "__main__":
    main()
