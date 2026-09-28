#!/usr/bin/env python3
"""게이트 넷리스트 → 74 시리즈 칩 할당 + 핀 배선표 (브레드보드 배선용)

  python pinmap.py netlist.yaml                    # 마크다운 표 출력
  python pinmap.py netlist.yaml --md wiring.md     # 파일로 저장
  python pinmap.py netlist.yaml --nand-only        # 모든 게이트를 NAND로 치환 (NAND-only 과제용)

netlist.yaml 형식 (logic.py netlist 가 생성):
  inputs: [A, B, C]
  outputs: [F]
  gates:
    - {id: U1, type: NOT, in: [A], out: "A'"}
    - {id: U2, type: AND, in: [A', B], out: n1}
"""
from __future__ import annotations

import _console  # noqa: F401  (Windows에서 한글·기호 출력)
import argparse
import itertools
from collections import defaultdict
from pathlib import Path

import yaml

REF = Path(__file__).resolve().parent.parent / "references" / "ic-pinouts.yaml"


def decompose(gates, prefer):
    """선호 칩이 없는 입력 수의 게이트를 2입력 체인으로 분해."""
    out, cnt = [], itertools.count(1)
    for g in gates:
        t, ins = g["type"], list(g["in"])
        avail = prefer.get(t, {})
        if len(ins) in avail:
            out.append(g)
            continue
        if t in ("NAND", "NOR"):
            raise SystemExit(f"{g['id']}: {len(ins)}입력 {t} 칩이 없음 — 식을 먼저 변형하세요.")
        cur = ins[0]
        for k, nxt in enumerate(ins[1:]):
            last = k == len(ins) - 2
            net = g["out"] if last else f"{g['out']}_c{next(cnt)}"
            out.append({"id": f"{g['id']}{'' if last else chr(97 + k)}", "type": t, "in": [cur, nxt], "out": net})
            cur = net
    return out


def to_nand(gates):
    """AND/OR/NOT → NAND 전용 변환 (2입력 기준)."""
    # 1) AND-OR(SOP) 구조는 NAND-NAND로 직접 치환 (이중 반전 제거)
    driver = {g["out"]: g for g in gates}
    fanout = defaultdict(int)
    for g in gates:
        for x in g["in"]:
            fanout[x] += 1
    for g in gates:
        if g["type"] == "OR" and all(
            x in driver and driver[x]["type"] in ("AND", "NOT") and fanout[x] == 1 for x in g["in"]
        ):
            for x in g["in"]:
                d = driver[x]
                if d["type"] == "AND":
                    d["type"] = "NAND"
                else:  # NOT 리터럴이 OR에 바로 들어가는 경우: x' 대신 원 신호를 NAND에
                    d["type"] = "BUF_SKIP"
            g["in"] = [driver[x]["in"][0] if driver[x]["type"] == "BUF_SKIP" else x for x in g["in"]]
            g["type"] = "NAND"
    gates = [g for g in gates if g["type"] != "BUF_SKIP"]

    res, c = [], itertools.count(1)
    for g in gates:
        t, i, o = g["type"], g["in"], g["out"]
        if t == "NOT":
            res.append({"id": g["id"], "type": "NAND", "in": [i[0], i[0]], "out": o})
        elif t == "AND":
            m = f"{o}_n{next(c)}"
            res += [{"id": g["id"] + "a", "type": "NAND", "in": i, "out": m},
                    {"id": g["id"] + "b", "type": "NAND", "in": [m, m], "out": o}]
        elif t == "OR":
            invs = []
            for x in i:
                m = f"{x}_inv{next(c)}"
                res.append({"id": f"{g['id']}i{len(invs)}", "type": "NAND", "in": [x, x], "out": m})
                invs.append(m)
            res.append({"id": g["id"], "type": "NAND", "in": invs, "out": o})
        else:
            res.append(g)
    return res


def allocate(gates, db):
    chips, prefer = db["chips"], db["prefer"]
    pool = defaultdict(list)  # part -> [(chip_label, free_gate_indices)]
    ncnt = itertools.count(1)
    assign = []
    for g in gates:
        part = prefer[g["type"]][len(g["in"])]
        slot = next((p for p in pool[part] if p[1]), None)
        if slot is None:
            slot = (f"IC{next(ncnt)}", list(range(len(chips[part]["gates"]))))
            pool[part].append(slot)
        gi = slot[1].pop(0)
        pins = chips[part]["gates"][gi]
        assign.append({**g, "chip": slot[0], "part": part, "unit": gi + 1,
                       "in_pins": pins[:-1], "out_pin": pins[-1]})
    return assign, pool, chips


def render(net, assign, pool, chips) -> str:
    L = ["Table: 사용 칩 {#tbl:chips}", "", "| 칩 | 부품 | 기능 | 사용 게이트 | 전원 |", "|:-:|:-:|:-:|:-:|:-:|"]
    for part, lst in pool.items():
        for label, free in lst:
            used = len(chips[part]["gates"]) - len(free)
            L.append(f"| {label} | 74xx{part[2:]} | {chips[part]['inputs']}-in {chips[part]['func']} | "
                     f"{used}/{len(chips[part]['gates'])} | VCC=14, GND=7 |")
    L += ["", "Table: 게이트별 칩/핀 할당 {#tbl:gates}", "", "| 게이트 | 종류 | 칩 | 입력 (신호→핀) | 출력 (핀→신호) |", "|:-:|:-:|:-:|:--|:--|"]
    for a in assign:
        ins = ", ".join(f"{s}→{p}" for s, p in zip(a["in"], a["in_pins"]))
        L.append(f"| {a['id']} | {a['type']} | {a['chip']} | {ins} | {a['out_pin']}→{a['out']} |")

    wires = defaultdict(list)
    for a in assign:
        wires[a["out"]].append(f"{a['chip']}.{a['out_pin']}(출력)")
        for s, p in zip(a["in"], a["in_pins"]):
            wires[s].append(f"{a['chip']}.{p}")
    L += ["", "Table: 넷별 배선 (같은 행 = 한 노드) {#tbl:nets}", "", "| 신호 | 연결 핀 |", "|:-:|:--|"]
    order = list(net.get("inputs", [])) + [k for k in wires if k not in net.get("inputs", []) and k not in net.get("outputs", [])] + list(net.get("outputs", []))
    for s in order:
        if s in wires:
            tag = " (입력 스위치)" if s in net.get("inputs", []) else (" (LED/프로브)" if s in net.get("outputs", []) else "")
            L.append(f"| {s}{tag} | {', '.join(wires[s])} |")

    unused = []
    for part, lst in pool.items():
        for label, free in lst:
            for gi in free:
                unused.append(f"{label}: " + ", ".join(map(str, chips[part]["gates"][gi][:-1])))
    if unused:
        L += ["", "> 사용하지 않는 게이트 입력은 GND나 VCC에 고정 (특히 HC 계열은 플로팅 금지): " + "; ".join(unused)]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("netlist")
    ap.add_argument("--md")
    ap.add_argument("--nand-only", action="store_true")
    a = ap.parse_args()
    db = yaml.safe_load(REF.read_text(encoding="utf-8"))
    net = yaml.safe_load(Path(a.netlist).read_text(encoding="utf-8"))
    gates = net["gates"]
    if a.nand_only:
        gates = to_nand(decompose(gates, {"AND": {2: 1}, "OR": {2: 1}, "NOT": {1: 1}}))
    gates = decompose(gates, db["prefer"])
    assign, pool, chips = allocate(gates, db)
    text = render(net, assign, pool, chips)
    if a.md:
        Path(a.md).write_text(text + "\n", encoding="utf-8")
        print("✓", a.md)
    else:
        print(text)


if __name__ == "__main__":
    main()
