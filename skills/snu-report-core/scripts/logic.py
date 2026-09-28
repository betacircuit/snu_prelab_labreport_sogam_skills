#!/usr/bin/env python3
"""불 대수 도구 — 진리표, 간소화, K-map 그림, 게이트 넷리스트

식 문법: ~ (NOT)  & (AND)  | (OR)  ^ (XOR),  예) "F = ~A&B | A&~C"
변수 순서는 --vars 로 고정 (진리표 행 순서 = 이진수 순서, 첫 변수가 MSB)

  python logic.py truth   --vars A B C --eq "F=~A&B|A&~C" --eq "G=A^B^C" [--json expected.json] [--md]
  python logic.py minimize --vars A B C D --minterms 0 2 5 7 8 10 13 15 [--dc 1 9] [--name F]
  python logic.py kmap    --vars A B C D --eq "F=..." -o figs/kmap_F.png
  python logic.py kmap    --vars A B C --minterms 1 3 6 --dc 7 -o figs/kmap.png
  python logic.py netlist --vars A B C --eq "F=~A&B|A&~C" -o netlist.yaml   (→ pinmap.py 입력)

출력 식은 보고서용 LaTeX(오버라인)와 식 문자열 둘 다 출력한다.
"""
from __future__ import annotations

import _console  # noqa: F401  (Windows에서 한글·기호 출력)
import argparse
import itertools
import json
import sys
from pathlib import Path

import sympy as sp
from sympy.logic.boolalg import And, Not, Or, Xor
from sympy.parsing.sympy_parser import parse_expr


# ───────────────────────── parsing ─────────────────────────
def parse_eq(eq: str, vars_: list[str]):
    name, rhs = (s.strip() for s in eq.split("=", 1)) if "=" in eq else ("F", eq.strip())
    syms = {v: sp.Symbol(v) for v in vars_}
    expr = parse_expr(rhs.replace("'", ""), local_dict=syms)
    extra = {str(s) for s in expr.free_symbols} - set(vars_)
    if extra:
        sys.exit(f"--vars 에 없는 변수: {extra}")
    return name, expr


def rows(n):
    return list(itertools.product([0, 1], repeat=n))


def evaluate(expr, vars_):
    syms = [sp.Symbol(v) for v in vars_]
    return [int(bool(expr.subs(dict(zip(syms, map(bool, r)))))) for r in rows(len(vars_))]


# ───────────────────────── formatting ─────────────────────────
def to_latex(expr) -> str:
    """보고서용: \\overline{A}B + A\\overline{C}"""
    if isinstance(expr, sp.Symbol):
        return str(expr)
    if isinstance(expr, Not):
        return r"\overline{" + to_latex(expr.args[0]) + "}"
    if isinstance(expr, And):
        parts = []
        for a in sorted(expr.args, key=str):
            s = to_latex(a)
            parts.append(f"({s})" if isinstance(a, (Or, Xor)) else s)
        return "".join(parts)
    if isinstance(expr, Or):
        return " + ".join(to_latex(a) for a in sorted(expr.args, key=str))
    if isinstance(expr, Xor):
        return r" \oplus ".join(
            f"({to_latex(a)})" if isinstance(a, (Or, And)) else to_latex(a) for a in expr.args
        )
    if expr is sp.true:
        return "1"
    if expr is sp.false:
        return "0"
    return sp.latex(expr)


def to_text(expr) -> str:
    return str(expr).replace(" ", "")


def md_truth_table(vars_, outs: dict[str, list[int]]) -> str:
    head = "| " + " | ".join(vars_ + list(outs)) + " |"
    sep = "|" + "|".join([":-:"] * (len(vars_) + len(outs))) + "|"
    body = []
    for i, r in enumerate(rows(len(vars_))):
        body.append("| " + " | ".join([str(x) for x in r] + [str(outs[k][i]) for k in outs]) + " |")
    return "\n".join([head, sep, *body])


# ───────────────────────── K-map ─────────────────────────
GRAY = {1: ["0", "1"], 2: ["00", "01", "11", "10"]}


def kmap_png(vars_, values, out, title=None, groups=None):
    """values: 길이 2^n 리스트, 원소는 0/1/'X'. 흑백.
    groups: [{"cells": [6, 7], "label": r"$\\overline{A}BC$"}, ...] — 묶음을 둥근 사각형으로 표시
    (행·열이 연속인 묶음만 한 상자로, 가장자리를 넘는 묶음은 칸마다 상자)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    plt.rcParams["mathtext.fontset"] = "dejavusans"
    from circuit_kit import TEXT_FAMILY
    n = len(vars_)
    if n not in (2, 3, 4):
        sys.exit("K-map은 2~4변수만 지원")
    rv, cv = vars_[: n // 2], vars_[n // 2 :]
    rg, cg = GRAY[len(rv)], GRAY[len(cv)]
    fig, ax = plt.subplots(figsize=(0.9 * len(cg) + 1.2, 0.9 * len(rg) + 1.0), dpi=200)
    pos = {}
    for i, rbits in enumerate(rg):
        for j, cbits in enumerate(cg):
            idx = int(rbits + cbits, 2)
            pos[idx] = (i, j)
            val = values[idx]
            ax.add_patch(plt.Rectangle((j, -i), 1, -1, fill=False, ec="black", lw=0.9))
            ax.text(j + 0.5, -i - 0.5, str(val), ha="center", va="center", fontsize=13, family=TEXT_FAMILY)
            ax.text(j + 0.93, -i - 0.9, str(idx), ha="right", va="bottom", fontsize=6, color="#777777", family=TEXT_FAMILY)
    for j, c in enumerate(cg):
        ax.text(j + 0.5, 0.2, c, ha="center", va="bottom", fontsize=10, family=TEXT_FAMILY)
    for i, r in enumerate(rg):
        ax.text(-0.15, -i - 0.5, r, ha="right", va="center", fontsize=10, family=TEXT_FAMILY)
    ax.text(-0.15, 0.2, f"{''.join(rv)}\\{''.join(cv)}", ha="right", va="bottom", fontsize=10, family=TEXT_FAMILY)
    styles = ["-", "--", ":", "-."]
    for k, g in enumerate(groups or []):
        cells = [pos[c] for c in g["cells"]]
        rows, cols = sorted({r for r, _ in cells}), sorted({c for _, c in cells})
        contiguous = rows == list(range(rows[0], rows[-1] + 1)) and cols == list(range(cols[0], cols[-1] + 1))
        boxes = [(rows[0], rows[-1], cols[0], cols[-1])] if contiguous else [(r, r, c, c) for r, c in cells]
        pad = 0.12 + 0.05 * k
        for r0, r1, c0, c1 in boxes:
            ax.add_patch(FancyBboxPatch((c0 + pad, -r1 - 1 + pad), c1 - c0 + 1 - 2 * pad, r1 - r0 + 1 - 2 * pad,
                                        boxstyle="round,pad=0,rounding_size=0.25", fill=False, ec="black",
                                        lw=1.4, ls=styles[k % len(styles)]))
        if g.get("label"):
            r0, r1, c0, c1 = boxes[0]
            ax.text(c1 + 1 + 0.08, -r0 - 0.5 if c1 == len(cg) - 1 else -r0 - 0.5, g["label"],
                    ha="left", va="center", fontsize=11, family=TEXT_FAMILY)
    if title:
        ax.set_title(title, fontsize=11, pad=6, family=TEXT_FAMILY)
    ax.set_xlim(-1, len(cg) + (1.2 if groups else 0.1))
    ax.set_ylim(-len(rg) - 0.1, 0.55)
    ax.set_aspect("equal")
    ax.axis("off")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    print("✓", out)


# ───────────────────────── netlist ─────────────────────────
def to_netlist(name, expr, gates, counter, cache):
    """sympy 식 → 게이트 목록. 반환값: 이 식의 출력 넷 이름."""
    key = sp.srepr(expr)
    if key in cache:
        return cache[key]
    if isinstance(expr, sp.Symbol):
        return str(expr)
    if isinstance(expr, Not):
        a = to_netlist(name, expr.args[0], gates, counter, cache)
        net = f"{a}'" if isinstance(expr.args[0], sp.Symbol) else f"n{next(counter)}"
        gates.append({"type": "NOT", "in": [a], "out": net})
    else:
        typ = {And: "AND", Or: "OR", Xor: "XOR"}[type(expr)]
        ins = [to_netlist(name, a, gates, counter, cache) for a in sorted(expr.args, key=str)]
        net = f"n{next(counter)}"
        gates.append({"type": typ, "in": ins, "out": net})
    cache[key] = net
    return net


# ───────────────────────── CLI ─────────────────────────
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for c in ("truth", "minimize", "kmap", "netlist"):
        p = sub.add_parser(c)
        p.add_argument("--vars", nargs="+", required=True)
        p.add_argument("--eq", action="append", default=[])
        p.add_argument("--minterms", nargs="*", type=int)
        p.add_argument("--dc", nargs="*", type=int, default=[])
        p.add_argument("--name", default="F")
        p.add_argument("--json", help="expected.json 에 truth_table 병합 저장")
        p.add_argument("-o", "--out")
    a = ap.parse_args()
    V = a.vars
    N = 2 ** len(V)

    if a.cmd == "truth":
        outs = {}
        for eq in a.eq:
            n, e = parse_eq(eq, V)
            outs[n] = evaluate(e, V)
        print(md_truth_table(V, outs))
        for n, vals in outs.items():
            print(f"\n{n}: minterms Σm({', '.join(str(i) for i, x in enumerate(vals) if x)})")
        if a.json:
            p = Path(a.json)
            data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
            data["truth_table"] = {"inputs": V, "outputs": outs}
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print("✓", p)

    elif a.cmd == "minimize":
        if a.minterms is None and a.eq:
            n, e = parse_eq(a.eq[0], V)
            vals = evaluate(e, V)
            mins, name = [i for i, x in enumerate(vals) if x], n
        else:
            mins, name = a.minterms or [], a.name
        syms = [sp.Symbol(v) for v in V]
        sop = sp.SOPform(syms, [list(r) for i, r in enumerate(rows(len(V))) if i in mins],
                         [list(r) for i, r in enumerate(rows(len(V))) if i in a.dc])
        pos = sp.POSform(syms, [list(r) for i, r in enumerate(rows(len(V))) if i in mins],
                         [list(r) for i, r in enumerate(rows(len(V))) if i in a.dc])
        maxs = [i for i in range(N) if i not in mins and i not in a.dc]
        print(f"{name} = Σm({', '.join(map(str, mins))})" + (f" + d({', '.join(map(str, a.dc))})" if a.dc else ""))
        print(f"   = ΠM({', '.join(map(str, maxs))})")
        print(f"최소 SOP : {to_text(sop)}")
        print(f"   LaTeX : ${name} = {to_latex(sop)}$")
        print(f"최소 POS : {to_text(pos)}")
        print(f"   LaTeX : ${name} = {to_latex(pos)}$")

    elif a.cmd == "kmap":
        if a.eq:
            name, e = parse_eq(a.eq[0], V)
            vals = evaluate(e, V)
        else:
            name, vals = a.name, [1 if i in (a.minterms or []) else 0 for i in range(N)]
        vals = ["X" if i in a.dc else v for i, v in enumerate(vals)]
        kmap_png(V, vals, a.out or f"kmap_{name}.png", title=f"K-map: {name}")

    elif a.cmd == "netlist":
        import yaml

        gates, cache = [], {}
        counter = itertools.count(1)
        outputs = {}
        for eq in a.eq:
            n, e = parse_eq(eq, V)
            net = to_netlist(n, e, gates, counter, cache)
            outputs[n] = net
        # 출력 넷 이름을 출력 변수명으로 교체
        ren = {v: k for k, v in outputs.items()}
        for g in gates:
            g["out"] = ren.get(g["out"], g["out"])
            g["in"] = [ren.get(x, x) for x in g["in"]]
        for i, g in enumerate(gates, 1):
            g["id"] = f"U{i}"
        doc = {"inputs": V, "outputs": list(outputs), "gates": gates}
        text = yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, default_flow_style=None)
        if a.out:
            Path(a.out).write_text(text, encoding="utf-8")
            print("✓", a.out)
        else:
            print(text)


if __name__ == "__main__":
    main()
