#!/usr/bin/env python3
"""오실로스코프 CSV → 파형 그림 + 자동 측정 (전파 지연, 상승/하강 시간, 전압 레벨)

  python scope.py report/scope/and_gate.csv -o report/figs/and_scope.png \
      --names CH1=A CH2=F --ref A [--json report/measured.json --key and_gate]

지원 형식 (자동 감지):
  - 일반:        time, CH1, CH2, ...
  - Rigol:       X,CH1,CH2,Start,Increment  (두 번째 줄에 Start/Increment 값)
  - Keysight:    x-axis,1,2 / second,Volt,Volt
  - Tektronix:   메타데이터 열 + (time, value) 열
⚠ 실습실 스코프 모델을 확인하고 샘플 CSV 하나로 먼저 테스트할 것.

측정은 참고용. 보고서에는 스코프 화면에서 커서로 직접 잰 값과 함께 쓰고,
두 값이 다르면 그 이유(샘플링 간격, 프로브 보정, 임계값 정의)를 고찰에 적는다.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path

import numpy as np

NUM = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?$")


def _isnum(s):
    return bool(NUM.match(s.strip())) if s else False


def load_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    rows = list(csv.reader(path.read_text(encoding="utf-8", errors="ignore").splitlines()))
    start = next(i for i, r in enumerate(rows)
                 if sum(_isnum(c) for c in r) >= 2 and all(_isnum(c) or not c.strip() for c in r))
    pre = rows[:start]
    header = next((r for r in pre if any(c.strip().lower() == "increment" for c in r)), None) or next(
        (r for r in reversed(pre) if r and not _isnum(r[0]) and r[0].strip().lower() not in ("sequence", "second")),
        None,
    )
    data_rows = [r for r in rows[start:] if sum(_isnum(c) for c in r) >= 2]

    # Rigol: X,CH1,CH2,Start,Increment
    if header and any(h.strip().lower() == "increment" for h in header):
        hl = [h.strip().lower() for h in header]
        meta = rows[rows.index(header) + 1]
        t0 = float(meta[hl.index("start")]) if "start" in hl else float(rows[start][hl.index("start")])
        dt = float(meta[hl.index("increment")]) if "increment" in hl else float(rows[start][hl.index("increment")])
        ch_idx = [i for i, h in enumerate(hl) if h.startswith("ch")]
        arr = np.array([[float(r[i]) for i in ch_idx] for r in data_rows if all(_isnum(r[i]) for i in ch_idx)])
        t = t0 + dt * np.arange(len(arr))
        return t, {header[i].strip().upper(): arr[:, k] for k, i in enumerate(ch_idx)}

    ncol = max(len(r) for r in data_rows)
    numeric_cols = [j for j in range(ncol) if all(j < len(r) and _isnum(r[j]) for r in data_rows[:50])]
    # 첫 숫자 열 = 시간, 나머지 = 채널 (Tektronix처럼 앞에 메타데이터 열이 있어도 숫자 열만 사용)
    tcol, vcols = numeric_cols[0], numeric_cols[1:]
    arr = np.array([[float(r[j]) for j in [tcol, *vcols]] for r in data_rows if all(_isnum(r[j]) for j in [tcol, *vcols])])
    names = []
    for k, j in enumerate(vcols):
        h = header[j].strip() if header and j < len(header) else ""
        h = h if h and (h.isdigit() or not _isnum(h)) else f"CH{k + 1}"
        names.append(f"CH{h}" if h.isdigit() else h.upper())
    return arr[:, 0], {n: arr[:, k + 1] for k, n in enumerate(names)}


def levels(v):
    lo, hi = np.percentile(v, 2), np.percentile(v, 98)
    return float(lo), float(hi)


def crossings(t, v, thr, direction):
    s = v > thr
    idx = np.where((~s[:-1] & s[1:]) if direction == "rise" else (s[:-1] & ~s[1:]))[0]
    out = []
    for i in idx:  # 선형 보간
        v0, v1 = v[i], v[i + 1]
        out.append(float(t[i] + (thr - v0) * (t[i + 1] - t[i]) / (v1 - v0)) if v1 != v0 else float(t[i]))
    return out


def edge_times(t, v, frac_lo=0.1, frac_hi=0.9):
    lo, hi = levels(v)
    sw = hi - lo
    res = {"V_low": lo, "V_high": hi, "swing": sw}
    if sw < 0.5:  # 변화 없음
        return res
    r10, r90 = crossings(t, v, lo + frac_lo * sw, "rise"), crossings(t, v, lo + frac_hi * sw, "rise")
    f90, f10 = crossings(t, v, lo + frac_hi * sw, "fall"), crossings(t, v, lo + frac_lo * sw, "fall")
    def pair(starts, ends):
        out = []
        for i, a in enumerate(starts):
            nxt = starts[i + 1] if i + 1 < len(starts) else float("inf")
            b = next((x for x in ends if a < x < nxt), None)
            if b is not None:
                out.append(b - a)
        return out

    rises, falls = pair(r10, r90), pair(f90, f10)
    if rises:
        res["t_rise"] = float(np.median(rises))
    if falls:
        res["t_fall"] = float(np.median(falls))
    mid = lo + 0.5 * sw
    res["edges_rise"] = crossings(t, v, mid, "rise")
    res["edges_fall"] = crossings(t, v, mid, "fall")
    return res


def prop_delay(ref, out, window=1e-6):
    """ref 에지 직후 가장 가까운 out 에지까지의 시간. out 방향으로 tPLH/tPHL 구분."""
    ref_edges = sorted(ref.get("edges_rise", []) + ref.get("edges_fall", []))
    d = {"tPLH": [], "tPHL": []}
    for key, lst in (("tPLH", out.get("edges_rise", [])), ("tPHL", out.get("edges_fall", []))):
        for te in lst:
            prev = [r for r in ref_edges if 0 <= te - r < window]
            if prev:
                d[key].append(te - max(prev))
    return {k: float(np.median(v)) for k, v in d.items() if v}


def fmt_t(s):
    for unit, f in (("s", 1), ("ms", 1e3), ("μs", 1e6), ("ns", 1e9)):
        if abs(s) * f >= 1 or unit == "ns":
            if unit != "s" or abs(s) >= 1:
                return f"{s * f:.3g} {unit}"
    return f"{s:.3g} s"


def plot(t, chans, out, title=None):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = ["#E0A800", "#17A2B8", "#C2185B", "#1F3A5F"]  # 스코프 채널색 느낌
    n = len(chans)
    fig, axes = plt.subplots(n, 1, sharex=True, figsize=(7, 1.35 * n + 0.6), dpi=200)
    axes = np.atleast_1d(axes)
    scale, unit = 1, "s"
    span = t[-1] - t[0]
    for u, f in (("ns", 1e9), ("μs", 1e6), ("ms", 1e3)):
        if span * f < 5000:
            scale, unit = f, u
            break
    for ax, (name, v), c in zip(axes, chans.items(), colors * 2):
        ax.plot((t - t[0]) * scale, v, color=c, lw=1.1)
        ax.set_ylabel(name, rotation=0, ha="right", va="center", fontsize=9)
        ax.grid(True, color="#EEE", lw=0.6)
        ax.tick_params(labelsize=7)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
    axes[-1].set_xlabel(f"t [{unit}]", fontsize=8)
    if title:
        axes[0].set_title(title, fontsize=10)
    fig.tight_layout()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    print("✓", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("-o", "--out")
    ap.add_argument("--names", nargs="*", default=[], help="CH1=A CH2=F")
    ap.add_argument("--ref", help="지연 기준 신호 이름")
    ap.add_argument("--json", help="measured.json 에 결과 병합")
    ap.add_argument("--key", help="json 안에서 쓸 키 (기본: 파일 이름)")
    ap.add_argument("--title")
    a = ap.parse_args()

    t, chans = load_csv(a.csv)
    ren = dict(kv.split("=", 1) for kv in a.names)
    chans = {ren.get(k, k): v for k, v in chans.items()}
    meas = {k: edge_times(t, v) for k, v in chans.items()}
    if a.ref:
        for k in chans:
            if k != a.ref:
                meas[k]["delay_from_" + a.ref] = prop_delay(meas[a.ref], meas[k])

    print(f"| 신호 | V_low | V_high | t_rise | t_fall | 지연 ({a.ref or '-'} 기준) |")
    print("|:-:|:-:|:-:|:-:|:-:|:-:|")
    for k, m in meas.items():
        dl = m.get("delay_from_" + str(a.ref), {})
        dls = ", ".join(f"{x} {fmt_t(y)}" for x, y in dl.items()) or "-"
        print(f"| {k} | {m['V_low']:.2f} V | {m['V_high']:.2f} V | "
              f"{fmt_t(m['t_rise']) if 't_rise' in m else '-'} | {fmt_t(m['t_fall']) if 't_fall' in m else '-'} | {dls} |")

    if a.out:
        plot(t, chans, a.out, a.title)
    if a.json:
        p = Path(a.json)
        data = json.loads(p.read_text()) if p.exists() else {}
        slim = {k: {kk: vv for kk, vv in m.items() if not kk.startswith("edges_")} for k, m in meas.items()}
        data.setdefault("scope", {})[a.key or a.csv.stem] = slim
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        print("✓", p)


if __name__ == "__main__":
    main()
