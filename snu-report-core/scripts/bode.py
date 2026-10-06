#!/usr/bin/env python3
"""보드 선도·페이저도·주파수 응답 표 — 회로이론 보고서용 (흑백, figures.md 그래프 규칙).

  # 이론 전달 함수(w = 각주파수, s = jw, f = 주파수)와 부품값으로 보드 선도
  python bode.py plot --tf "1/(1 - w**2*L*C + 1j*w*L/R)" -p L=10m,C=100n,R=1k \
      --fmin 100 --fmax 100k -o figs/bode.png
  # 같은 그림에 LTspice 결과(raw)와 측정값(csv)을 겹친다
  python bode.py plot --tf "..." -p ... --sim out.raw:v(out) --meas data/bode.csv -o figs/bode.png
  # 보고서 표: 주파수별 |H|, dB, 위상(°)
  python bode.py table --tf "..." -p ... --at 100,1k,5k,10k
  # 페이저도: 이름=크기∠각도(°)
  python bode.py phasor "V_s=1∠0" "V_R=0.8∠-37" "V_C=0.6∠-127" -o figs/phasor.png

측정 csv 열 (첫 줄 머리): f(Hz)와 [gain_db | gain | vin,vout] 중 하나, 선택 phase_deg.
진폭을 Vpp로 적었든 Vrms로 적었든 vin·vout이 같은 종류면 된다.

위상은 이어지게 그린다(−180°에서 +180°로 뛰지 않게). 보고서 본문에는 이 프로그램 이름이나
계산 함수 이름을 쓰지 않는다 — 위상 식은 tan⁻¹ + 구간 나눔으로 (snu-circuit-lab/references/notation.md).
"""
from __future__ import annotations

import _console  # noqa: F401  (Windows에서 한글·기호 출력)
import argparse
import csv
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

SUFFIX = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6, "m": 1e-3,
          "k": 1e3, "K": 1e3, "meg": 1e6, "M": 1e6, "G": 1e9}


def si(tok: str) -> float:
    """'10m', '100n', '4.7k', '1meg', '2.2µ' → float. 단위 글자(F, H, Ω, Hz)는 무시."""
    t = tok.strip().replace("Ω", "").replace("ohm", "")
    m = re.fullmatch(r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(meg|[fpnuµμmkKMG])?\s*(?:F|H|Hz|V|A|s)?", t)
    if not m:
        raise ValueError(f"값을 읽을 수 없음: {tok!r} (예: 10m, 100n, 4.7k, 1meg)")
    mult = m.group(2) or ""
    return float(m.group(1)) * SUFFIX.get(mult, 1.0)


def params(spec: str | None) -> dict[str, float]:
    out: dict[str, float] = {}
    for part in filter(None, (x.strip() for x in (spec or "").split(","))):
        k, _, v = part.partition("=")
        if not _:
            raise ValueError(f"'이름=값' 꼴이 아님: {part}")
        out[k.strip()] = si(v)
    return out


def response(tf: str, p: dict[str, float], f):
    """전달 함수 식을 주파수 배열에서 계산 (복소수 배열)"""
    import numpy as np
    w = 2 * np.pi * np.asarray(f, dtype=float)
    env = {"np": np, "pi": np.pi, "sqrt": np.sqrt, "exp": np.exp, "j": 1j,
           "w": w, "s": 1j * w, "f": np.asarray(f, dtype=float), **p}
    try:
        h = eval(tf, {"__builtins__": {}}, env)   # noqa: S307 — 에이전트가 쓴 회로 식만 받는다
    except NameError as e:
        sys.exit(f"✗ 식에 값이 없는 기호: {e}. -p 이름=값으로 준다 (w=각주파수, s=jw, f=주파수)")
    return np.broadcast_to(np.asarray(h, dtype=complex), w.shape)


def phase_deg(h):
    """이어지는 위상(°). 낮은 주파수 끝이 −180°–180° 안에 오게 맞춘다"""
    import numpy as np
    ph = np.degrees(np.unwrap(np.angle(h)))
    k = np.round(ph[0] / 360.0) if abs(ph[0]) > 180 else 0
    return ph - 360.0 * k


def read_meas(path: Path):
    """측정 csv → (f, dB, 위상 또는 None)"""
    import numpy as np
    rows = list(csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines()))
    if not rows:
        sys.exit(f"✗ 측정 파일이 비었다: {path}")
    keys = {k.strip().lower(): k for k in rows[0]}

    def col(*names):
        for n in names:
            if n in keys:
                return np.array([float(r[keys[n]]) for r in rows])
        return None

    f = col("f", "f_hz", "freq", "frequency", "주파수")
    if f is None:
        sys.exit(f"✗ {path}: 주파수 열(f)이 없다. 있는 열: {', '.join(rows[0])}")
    db = col("gain_db", "db")
    if db is None:
        g = col("gain", "ratio")
        if g is None:
            vin, vout = col("vin"), col("vout")
            if vin is None or vout is None:
                sys.exit(f"✗ {path}: gain_db, gain, vin·vout 중 하나가 있어야 한다")
            g = vout / vin
        db = 20 * np.log10(np.abs(g))
    return f, db, col("phase_deg", "phase", "위상")


def _style(ax):
    ax.grid(True, which="both", color="#cccccc", lw=0.5)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)


def _fonts():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from circuit_kit import TEXT_FAMILY
    plt.rcParams.update({"font.family": TEXT_FAMILY, "mathtext.fontset": "dejavusans", "axes.unicode_minus": False})
    return plt


def plot(a) -> Path:
    import numpy as np
    plt = _fonts()
    p = params(a.params)
    f = np.logspace(math.log10(si(a.fmin)), math.log10(si(a.fmax)), 600)
    series = []   # (이름, f, dB, 위상, 선 모양)
    if a.tf:
        h = response(a.tf, p, f)
        series.append((a.tf_label, f, 20 * np.log10(np.abs(h)), phase_deg(h), dict(color="k", ls="-", lw=1.3)))
    if a.sim:
        from spice import read_raw, trace
        raw, _, name = a.sim.partition(":")
        rr = read_raw(Path(raw))
        y = np.asarray(trace(rr, name or "v(out)"))
        x = np.asarray(rr.x).real
        series.insert(0, (a.sim_label, x, 20 * np.log10(np.abs(y)), phase_deg(y), dict(color="0.6", ls="-", lw=3.2, solid_capstyle="butt")))   # 이론과 겹쳐도 보이게 굵은 회색 띠를 밑에
    meas = None
    if a.meas:
        fm, dbm, phm = read_meas(Path(a.meas))
        meas = (a.meas_label, fm, dbm, phm)
    if not series and meas is None:
        sys.exit("✗ 그릴 것이 없다: --tf, --sim, --meas 중 하나는 준다")

    both = not a.mag_only
    fig, axes = plt.subplots(2 if both else 1, 1, figsize=(6, 4.6 if both else 2.8), sharex=True)
    axes = list(np.atleast_1d(axes))
    am = axes[0]
    for name, x, db, ph, st in series:
        am.semilogx(x, db, label=name, **st)
        if both:
            axes[1].semilogx(x, ph, **st)
    if meas:
        name, fm, dbm, phm = meas
        am.semilogx(fm, dbm, "o", mfc="white", mec="k", ms=5, ls="none", label=name)
        if both and phm is not None:
            axes[1].semilogx(fm, phm, "o", mfc="white", mec="k", ms=5, ls="none")
    if a.mark_3db and a.tf:
        h = response(a.tf, p, f)
        db = 20 * np.log10(np.abs(h))
        ref = passband_db(f, db)
        fcs = crossings(f, db, ref - 3.0103)
        for k, fc in enumerate(fcs):
            for ax in axes:
                ax.axvline(fc, color="0.4", ls=":", lw=0.9)
            am.annotate(fmt_f(fc), (fc, 0.04), xycoords=("data", "axes fraction"), xytext=(3, 0),
                        textcoords="offset points", fontsize=9, ha="left", va="bottom",
                        bbox=dict(fc="white", ec="none", pad=0.5))   # 곡선과 겹치지 않게 축 아래쪽에
            print(f"  −3 dB 주파수: {fmt_f(fc)} (기준 {ref:.2f} dB)")
    am.set_ylabel("크기 [dB]")
    if both:
        axes[1].set_ylabel("위상 [°]")
        lo, hi = axes[1].get_ylim()
        step = 45 if hi - lo <= 360 else 90
        axes[1].set_yticks(np.arange(math.floor(lo / step) * step, hi + 1, step))
    axes[-1].set_xlabel("주파수 [Hz]")
    for ax in axes:
        _style(ax)
    if len(series) + (1 if meas else 0) > 1:
        hs, ls = am.get_legend_handles_labels()
        order = sorted(range(len(ls)), key=lambda i: [a.tf_label, a.sim_label, a.meas_label].index(ls[i]))
        am.legend([hs[i] for i in order], [ls[i] for i in order], frameon=False, fontsize=9)   # 이론 → 시뮬레이션 → 측정
    fig.tight_layout()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=220)
    print(f"✓ {out}")
    return out


def passband_db(f, db) -> float:
    """−3 dB 기준: 평평한 끝(통과대역)의 값. 양 끝이 다 기울어 있으면(대역 통과) 최댓값"""
    import numpy as np
    lf = np.log10(f)
    n = max(3, len(f) // 20)
    flat = []
    for sl in (slice(0, n), slice(-n, None)):
        slope = (db[sl][-1] - db[sl][0]) / (lf[sl][-1] - lf[sl][0])   # dB/decade
        if abs(slope) < 3:
            flat.append(float(db[sl].mean()))
    return max(flat) if flat else float(db.max())


def crossings(f, db, level) -> list[float]:
    import numpy as np
    out = []
    for i in np.where(np.diff(np.sign(db - level)))[0]:
        out.append(float(f[i] * (f[i + 1] / f[i]) ** ((level - db[i]) / (db[i + 1] - db[i]))))
    return out


def fmt_f(x: float) -> str:
    for div, unit in ((1e6, "MHz"), (1e3, "kHz"), (1, "Hz")):
        if x >= div:
            return f"{x / div:.3g} {unit}"
    return f"{x:.3g} Hz"


def table(a):
    import numpy as np
    p = params(a.params)
    fs = [si(x) for x in a.at.split(",")]
    fine = np.logspace(math.log10(min(fs)) - 2, math.log10(max(fs)), 2000)
    ph_all = phase_deg(response(a.tf, p, np.concatenate([fine, fs])))[len(fine):]   # 낮은 주파수부터 이어 붙인 위상
    h = response(a.tf, p, fs)
    print("| 주파수 | $\\lvert H\\rvert$ | 크기 [dB] | 위상 [°] |\n|---:|---:|---:|---:|")
    for fi, hi, ph in zip(fs, h, ph_all):
        print(f"| {fmt_f(fi)} | {abs(hi):.4g} | {20 * math.log10(abs(hi)):.2f} | {ph:.1f} |")


def phasor(a) -> Path:
    import numpy as np
    plt = _fonts()
    vecs = []
    for spec in a.vectors:
        m = re.fullmatch(r"\s*([^=]+?)\s*=\s*([-+\d.eE]+)\s*(?:∠|<|@)\s*([-+\d.eE]+)\s*°?\s*", spec)
        if not m:
            sys.exit(f"✗ '{spec}' — 이름=크기∠각도 꼴로 (예: V_R=0.8∠-37)")
        vecs.append((m.group(1), float(m.group(2)), float(m.group(3))))
    rmax = max(r for _, r, _ in vecs)
    fig, ax = plt.subplots(figsize=(4.2, 4.2))
    styles = ["-", "--", "-.", ":"]
    for i, (name, r, deg) in enumerate(vecs):
        x, y = r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg))
        ax.annotate("", (x, y), (0, 0), arrowprops=dict(arrowstyle="-|>", color="k", lw=1.3, ls=styles[i % 4], shrinkA=0, shrinkB=0))
        lab = name if name.startswith("$") else "$" + (name if "_" not in name else name.split("_", 1)[0] + "_{" + name.split("_", 1)[1] + "}") + "$"
        off = 0.06 * rmax
        ax.text(x + off * math.cos(math.radians(deg)), y + off * math.sin(math.radians(deg)), lab,
                ha="left" if x >= 0 else "right", va="bottom" if y >= 0 else "top", fontsize=11)
    lim = 1.25 * rmax
    ax.axhline(0, color="0.5", lw=0.6)
    ax.axvline(0, color="0.5", lw=0.6)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.set_xlabel("실수부" + (f" [{a.unit}]" if a.unit else ""))
    ax.set_ylabel("허수부" + (f" [{a.unit}]" if a.unit else ""))
    _style(ax)
    fig.tight_layout()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=220)
    print(f"✓ {out}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plot")
    p.add_argument("--tf", help="전달 함수 식 (w, s=jw, f, 부품 기호)")
    p.add_argument("-p", "--params", help="부품값 L=10m,C=100n,R=1k")
    p.add_argument("--fmin", default="10")
    p.add_argument("--fmax", default="1meg")
    p.add_argument("--sim", help="LTspice raw:신호 (예: out.raw:v(out))")
    p.add_argument("--meas", help="측정 csv")
    p.add_argument("--tf-label", default="이론")
    p.add_argument("--sim-label", default="LTspice 시뮬레이션")
    p.add_argument("--meas-label", default="측정")
    p.add_argument("--mag-only", action="store_true", help="크기만")
    p.add_argument("--mark-3db", action="store_true", help="이론 곡선의 −3 dB 주파수 표시")
    p.add_argument("-o", "--out", required=True)
    t = sub.add_parser("table")
    t.add_argument("--tf", required=True)
    t.add_argument("-p", "--params")
    t.add_argument("--at", required=True, help="주파수 목록 100,1k,10k")
    v = sub.add_parser("phasor")
    v.add_argument("vectors", nargs="+", help="이름=크기∠각도(°)")
    v.add_argument("--unit", default="V")
    v.add_argument("-o", "--out", required=True)
    a = ap.parse_args(argv)
    {"plot": plot, "table": table, "phasor": phasor}[a.cmd](a)


if __name__ == "__main__":
    main()
