#!/usr/bin/env python3
"""prelab 예상값(expected.json) vs 실험 측정값(measured.json) 비교표

  python compare.py <lab_dir>                 # 마크다운 출력
  python compare.py <lab_dir> --md report/compare.md
  python compare.py <lab_dir> --part 74LS08   # 스코프 지연을 datasheet 값과 비교

measured.json 은 실험 후 '본인이 관찰한 값'만 넣는다. 비워 둔 칸은 "?" 로 두고 절대 채워 넣지 않는다.
  {
    "truth_table": {"inputs": ["A","B"], "outputs": {"F": [0, 0, 0, 1]}},
    "voltages":   {"F_high": 4.2, "F_low": 0.12},      # 선택
    "notes":      ["B=1 스위치 채터링 관찰"],             # 선택
    "scope":      {...}                                  # scope.py --json 이 채움
  }
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

REF = Path(__file__).resolve().parent.parent / "references" / "ic-pinouts.yaml"


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def truth_compare(exp, mea):
    et, mt = exp.get("truth_table"), mea.get("truth_table")
    if not et or not mt:
        return None, [], 0
    ins = et["inputs"]
    outs = list(et["outputs"])
    n = 2 ** len(ins)
    lines = ["| " + " | ".join(ins) + " | " + " | ".join(f"{o} 예상 | {o} 측정" for o in outs) + " | 일치 |",
             "|" + "|".join([":-:"] * (len(ins) + 2 * len(outs) + 1)) + "|"]
    mism, unknown = [], 0
    for i in range(n):
        bits = format(i, f"0{len(ins)}b")
        cells, ok = [], True
        for o in outs:
            e = et["outputs"][o][i]
            m = mt.get("outputs", {}).get(o, ["?"] * n)[i]
            cells += [str(e), f"**{m}**" if str(m) not in (str(e), "?") else str(m)]
            if str(m) == "?":
                unknown += 1
                ok = None if ok else ok
            elif str(m) != str(e):
                ok = False
                mism.append((bits, o, e, m))
        mark = "✓" if ok else ("?" if ok is None else "✗")
        lines.append("| " + " | ".join(bits) + " | " + " | ".join(cells) + f" | {mark} |")
    return "\n".join(lines), mism, unknown


def delay_compare(mea, part):
    if not mea.get("scope"):
        return None
    db = yaml.safe_load(REF.read_text(encoding="utf-8"))["timing_typ_ns"]
    ref = db.get(part, {}) if part else {}
    L = ["| 측정 | 신호 | 측정값 | datasheet typ | 차이 |", "|:-:|:-:|:-:|:-:|:-:|"]
    for key, sigs in mea["scope"].items():
        for sig, m in sigs.items():
            for dk, dv in m.items():
                if dk.startswith("delay_from_"):
                    for kind, val in dv.items():
                        typ = ref.get(kind, ref.get("tpd"))
                        ns = val * 1e9
                        diff = f"{(ns - typ) / typ * 100:+.0f}%" if typ else "-"
                        L.append(f"| {key} | {sig} {kind} | {ns:.1f} ns | {typ if typ else '-'} ns | {diff} |")
    return "\n".join(L) if len(L) > 2 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lab_dir", type=Path)
    ap.add_argument("--md")
    ap.add_argument("--part", help="예: 74LS08, 74HC08")
    a = ap.parse_args()
    exp = load(a.lab_dir / "prelab" / "expected.json")
    mea = load(a.lab_dir / "report" / "measured.json")

    out = []
    tt, mism, unknown = truth_compare(exp, mea) if exp.get("truth_table") and mea.get("truth_table") else (None, [], 0)
    if tt:
        out += ["Table: 예상 진리표와 측정 결과 비교 {#tbl:compare}", "", tt, ""]
        if unknown:
            out.append(f"[TODO: 측정값이 비어 있는 칸 {unknown}개 — measured.json 확인]")
        if mism:
            out.append("불일치 항목 (고찰에서 원인 분석 필요):")
            out += [f"- 입력 {b}: {o} 예상 {e}, 측정 {m}" for b, o, e, m in mism]
        elif not unknown:
            out.append("모든 입력 조합에서 측정값이 예상과 일치.")
        out.append("")
    dc = delay_compare(mea, a.part)
    if dc:
        out += ["Table: 전파 지연 측정값과 datasheet 비교 {#tbl:delay}", "", dc, ""]
    text = "\n".join(out) or "비교할 데이터가 없음 (expected.json / measured.json 확인)"
    if a.md:
        Path(a.md).write_text(text, encoding="utf-8")
        print("✓", a.md)
    print(text)


if __name__ == "__main__":
    main()
