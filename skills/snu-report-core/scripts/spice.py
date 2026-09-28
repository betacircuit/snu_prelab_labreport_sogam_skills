#!/usr/bin/env python3
"""SPICE 넷리스트 검사·실행·그래프 — LTspice에서도 ngspice에서도 그대로 돌아가는 파일만 넘기기 위해.

  python spice.py lint  circuit.cir                         # LTspice·ngspice 공통 문법 검사
  python spice.py run   circuit.cir                         # ngspice로 실행 → circuit.raw, .meas 결과 출력
  python spice.py plot  circuit.raw -t "v(in),v(out)" -o figs/tran.png     # 과도 응답 (흑백)
  python spice.py plot  circuit.raw -t "v(out)" -o figs/bode.png --bode    # AC: 크기(dB)·위상
  python spice.py value circuit.raw -t "v(out)" --at 1m                   # 한 시점(주파수)의 값
  python spice.py nodes circuit.cir                         # 소자·노드 연결표 (LTspice에서 회로도를 그릴 때)

raw 파일은 ngspice가 만든 것과 LTspice가 만든 것 모두 읽는다 (spicelib).
넷리스트 규칙과 LTspice 캡처 절차는 snu-circuit-lab의 references/ltspice.md.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SUFFIX = {"f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9, "t": 1e12}
LTSPICE_ONLY_MODELS = {"universalopamp", "universalopamp2", "opamp2", "lt1001", "lt1006", "lt1013", "lt1028", "lt1037",
                       "lt1056", "lm741", "ua741", "lm358", "tl081", "1n4148", "1n4001", "1n914", "2n3904", "2n3906",
                       "2n2222", "2n7002", "bs170", "irf530", "irf9530"}


def num(tok: str) -> float | None:
    m = re.fullmatch(r"([-+]?\d*\.?\d+(?:e[-+]?\d+)?)(meg|[fpnuµmkgt])?[a-zΩ]*", tok.strip().lower())
    if not m:
        return None
    return float(m.group(1)) * SUFFIX.get(m.group(2) or "", 1.0)


def logical_lines(text: str) -> list[tuple[int, str]]:
    """'+' 이어쓰기를 합친 (줄 번호, 내용). 첫 줄은 제목이라 뺀다."""
    out: list[tuple[int, str]] = []
    for i, raw in enumerate(text.splitlines()[1:], 2):
        ln = raw.split(";")[0].rstrip()
        if not ln.strip() or ln.lstrip().startswith("*"):
            continue
        if ln.lstrip().startswith("+") and out:
            out[-1] = (out[-1][0], out[-1][1] + " " + ln.lstrip()[1:])
        else:
            out.append((i, ln.strip()))
    return out


def lint(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    issues = []
    if any(ord(c) > 127 for c in text):
        issues.append("비ASCII 문자(한글 주석 등) — LTspice 버전에 따라 깨진다. 넷리스트는 영어로만 쓴다")
    lines = logical_lines(text)
    first = text.splitlines()[0] if text.strip() else ""
    if re.match(r"^\s*[RCLVIDQMXEFGHB]\w*\s", first, re.I):
        issues.append("1행은 제목 줄이라 무시된다 — 첫 소자가 1행에 있으면 사라진다. 1행에 '* 제목'을 쓴다")
    nodes, defined_models, defined_subckts, used = set(), set(), set(), []
    has_analysis = False
    analyses = [ln.split()[0].lower() for _, ln in lines if ln.split()[0].lower() in (".tran", ".ac", ".dc", ".noise")]
    if len(analyses) > 1:
        issues.append(f"분석이 {len(analyses)}개 ({', '.join(analyses)}) — 파일마다 하나만. raw에는 첫 분석만 남는다")
    for ln_no, ln in lines:
        low = ln.lower()
        tok = ln.split()
        head = tok[0].lower()
        if head == ".model" and len(tok) > 1:
            defined_models.add(tok[1].lower())
        elif head == ".subckt" and len(tok) > 1:
            defined_subckts.add(tok[1].lower())
        elif head == ".tran":
            has_analysis = True
            args = [a for a in tok[1:] if not a.lower().startswith(("uic", "startup", "steady", "nodiscard"))]
            if len(args) < 2 or (num(args[0]) or 0) <= 0:
                issues.append(f"{ln_no}행 '{ln}': ngspice는 .tran <Tstep> <Tstop>에서 Tstep > 0이 필요하다 (예: .tran 1u 10m)")
        elif head in (".ac", ".dc", ".op", ".noise", ".tf"):
            has_analysis = True
        elif head == ".step":
            issues.append(f"{ln_no}행: .step은 LTspice 전용 — ngspice 검증은 값마다 파일을 나눠 돌리고, LTspice용 파일에만 .step을 둔다")
        elif head in (".meas", ".measure"):
            if len(tok) < 2 or tok[1].lower() not in ("tran", "ac", "dc", "op", "noise", "tf"):
                issues.append(f"{ln_no}행: .meas 뒤에 분석 종류를 쓴다 (.meas tran name …) — ngspice는 생략하면 에러")
            elif tok[1].lower() == "ac":
                issues.append(f"{ln_no}행: .meas ac는 LTspice(복소수)와 ngspice(실수부) 결과가 다르다 — AC 값은 spice.py value로 읽는다")
        elif head in (".lib", ".inc", ".include") and not Path(tok[-1].strip('"')).exists():
            issues.append(f"{ln_no}행 {head} {tok[-1]}: 파일이 없다 — LTspice 설치 폴더 라이브러리에 기대지 말고 모델을 넷리스트에 넣는다")
        elif head[0] in "rclvidqmjxefghbsw" and not head.startswith("."):
            letter = head[0]
            n_nodes = {"r": 2, "c": 2, "l": 2, "v": 2, "i": 2, "d": 2, "q": 3, "m": 4, "j": 3, "e": 4, "g": 4,
                       "f": 2, "h": 2, "b": 2, "s": 4, "w": 2}.get(letter)
            if letter == "x":
                args = [t for t in tok[1:] if "=" not in t]
                nodes.update(a.lower() for a in args[:-1])
                used.append((ln_no, "subckt", args[-1].lower() if args else ""))
            elif n_nodes:
                nodes.update(t.lower() for t in tok[1:1 + n_nodes])
            if letter in "rcl" and len(tok) >= 4:
                val = tok[3]
                if re.fullmatch(r"\d*\.?\d+M(?![Ee][Gg])\w*", val):
                    issues.append(f"{ln_no}행 {tok[0]}={val}: SPICE에서 M은 밀리(10⁻³)다. 메가면 {val[:-1] if val.endswith('M') else val}Meg")
                if num(val) is None and not val.startswith("{"):
                    issues.append(f"{ln_no}행 {tok[0]}={val}: 값을 읽을 수 없다 (숫자+접미사, 예 4.7k, 100n, 1Meg)")
            if letter in "dqmj" and len(tok) > 1 + n_nodes:
                used.append((ln_no, "model", tok[1 + n_nodes].lower()))
    for ln_no, kind, name in used:
        if kind == "model" and name not in defined_models:
            extra = " (LTspice 기본 라이브러리 모델이라 ngspice에는 없다)" if name in LTSPICE_ONLY_MODELS else ""
            issues.append(f"{ln_no}행: 모델 '{name}'의 .model이 파일에 없다{extra} → .model 줄을 넣는다")
        if kind == "subckt" and name not in defined_subckts:
            extra = " (LTspice 전용 부품)" if name in LTSPICE_ONLY_MODELS else ""
            issues.append(f"{ln_no}행: 부분회로 '{name}'의 .subckt가 파일에 없다{extra} → 이상적 op-amp는 E 소스로, 실제 부품은 .subckt를 넣는다")
    if "0" not in nodes and "gnd" not in nodes:
        issues.append("접지 노드 0이 없다 — 기준 노드를 0으로 연결한다")
    if not has_analysis:
        issues.append("분석 명령(.tran, .ac, .dc, .op)이 없다")
    if not re.search(r"(?im)^\s*\.end\s*$", text):
        issues.append(".end가 없다 — 마지막 줄에 .end")
    return issues


def run(path: Path) -> Path:
    exe = shutil.which("ngspice")
    if not exe:
        sys.exit("✗ ngspice 없음 — Linux: apt-get install ngspice, macOS: brew install ngspice, "
                 "Windows: https://ngspice.sourceforge.io/download.html")
    raw = path.with_suffix(".raw").resolve()
    log = path.with_suffix(".log")
    # 원본은 그대로 두고, 실행용 사본에 control 블록을 붙여 .meas 출력과 raw 저장을 한 번에 한다
    # (-r 옵션만 쓰면 .meas 결과가 안 찍히고, -r 없이 돌리면 AC 분석이 저장되지 않는다)
    text = path.read_text(encoding="utf-8", errors="replace")
    body = re.sub(r"(?im)^\s*\.end\s*$", "", text).rstrip("\n")
    control = f".control\nset filetype=binary\nrun\nwrite {raw}\nquit\n.endc\n"
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / path.name
        tmp.write_text(body + "\n" + control + ".end\n", encoding="utf-8")
        r = subprocess.run([exe, "-b", str(tmp)], capture_output=True, text=True, cwd=path.resolve().parent)
    out = r.stdout + r.stderr
    log.write_text(out, encoding="utf-8")
    if raw.exists():   # write 명령은 변수 줄의 'grid=3' 앞을 공백으로 써서 spicelib가 축을 못 찾는다 → 탭으로
        data = raw.read_bytes()
        cut = data.find(b"Binary:\n")
        if cut > 0:
            raw.write_bytes(data[:cut].replace(b" grid=", b"\tgrid=") + data[cut:])
    errs = [ln.strip() for ln in out.splitlines()
            if re.search(r"(?i)\berror\b|fatal|singular matrix|timestep too small|unknown (model|subckt)", ln)]
    if r.returncode or errs or not raw.exists():
        print("✗ ngspice 실패:", *(errs[:8] or out.strip().splitlines()[-8:]), f"(전체 로그: {log})", sep="\n  ")
        sys.exit(1)
    meas, on = [], False
    for ln in out.splitlines():
        if "Measurements for" in ln:
            on = True
        elif on and re.match(r"^\s*\w+\s+=\s+[-+]?[\d.]", ln):
            meas.append(" ".join(ln.split()))
        elif on and ln.strip().startswith("Total"):
            on = False
    print(f"✓ {raw}")
    print("  신호:", ", ".join(read_raw(raw).get_trace_names()))
    for m in meas:
        print("  .meas", m)
    return raw


class Raw:
    """raw 파일 한 개 (첫 번째 plot). names: 신호 이름, x: 축(시간·주파수), data[name]: 값."""

    def __init__(self, names: list[str], x, data: dict):
        self.names, self.x, self.data = names, x, data

    def get_trace_names(self):
        return self.names


def _read_ngspice(path: Path) -> Raw:
    import numpy as np
    data = path.read_bytes()
    cut = data.find(b"Binary:\n")
    ascii_mode = cut < 0
    if ascii_mode:
        cut = data.find(b"Values:\n")
    head = data[:cut].decode("ascii", errors="replace").splitlines()
    info, names, in_vars = {}, [], False
    for ln in head:
        if in_vars and ln.startswith(("\t", " ")):
            names.append(ln.split()[1])
            continue
        in_vars = ln.startswith("Variables:")
        if ":" in ln and not in_vars:
            k, v = ln.split(":", 1)
            info[k.strip()] = v.strip()
    nvar, npts = int(info["No. Variables"]), int(info["No. Points"])
    cplx = "complex" in info.get("Flags", "")
    body = data[cut + len(b"Binary:\n"):] if not ascii_mode else data[cut + len(b"Values:\n"):]
    if ascii_mode:
        vals = []
        for tok in body.decode().split():
            if "," in tok:
                a, b = tok.split(","); vals.append(complex(float(a), float(b)))
            elif re.fullmatch(r"[-+]?[\d.]+(e[-+]?\d+)?", tok, re.I):
                vals.append(float(tok))
        arr = np.array(vals).reshape(npts, -1)[:, -nvar:]
    else:
        arr = np.frombuffer(body, dtype=np.complex128 if cplx else np.float64, count=npts * nvar).reshape(npts, nvar)
    cols = {n: arr[:, i] for i, n in enumerate(names)}
    return Raw(names, np.abs(arr[:, 0].real), cols)


def read_raw(path: Path) -> Raw:
    """ngspice raw는 직접 읽고, LTspice raw(UTF-16 머리글)는 spicelib로 읽는다."""
    import numpy as np
    head = path.read_bytes()[:400]
    if head[1:2] != b"\x00":
        return _read_ngspice(path)
    from spicelib import RawRead
    rr = RawRead(str(path), dialect="ltspice", verbose=False)
    names = rr.get_trace_names()
    cols = {n: np.asarray(rr.get_trace(n).get_wave()) for n in names}
    return Raw(names, np.abs(np.asarray(rr.get_axis()).real), cols)


def trace(rr: Raw, name: str):
    names = {n.lower(): n for n in rr.names}
    key = names.get(name.lower())
    if key is None:
        sys.exit(f"✗ 신호 '{name}' 없음. 있는 것: {', '.join(rr.names)}")
    return rr.data[key]


def axis(rr: Raw):
    return rr.x


def plot(raw: Path, traces: list[str], out: Path, bode: bool, xlabel: str | None, title: str | None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from circuit_kit import TEXT_FAMILY
    plt.rcParams.update({"font.family": TEXT_FAMILY, "mathtext.fontset": "dejavusans", "axes.unicode_minus": False})
    rr = read_raw(raw)
    x = axis(rr)
    styles = ["-", "--", ":", "-."]
    if bode:
        fig, (a1, a2) = plt.subplots(2, 1, figsize=(6, 4.4), sharex=True)
        for i, t in enumerate(traces):
            y = np.asarray(trace(rr, t))
            a1.semilogx(x, 20 * np.log10(np.abs(y)), "k" + styles[i % 4], lw=1.2, label=t)
            a2.semilogx(x, np.degrees(np.unwrap(np.angle(y))), "k" + styles[i % 4], lw=1.2)
        a1.set_ylabel("크기 (dB)")
        a2.set_ylabel("위상 (°)")
        a2.set_xlabel(xlabel or "주파수 (Hz)")
        for a in (a1, a2):
            a.grid(True, which="both", color="0.85", lw=0.5)
        if len(traces) > 1:
            a1.legend(frameon=False)
    else:
        fig, a = plt.subplots(figsize=(6, 3.2))
        scale, unit = 1.0, "s"
        if x.max() < 1e-3:
            scale, unit = 1e6, "µs"
        elif x.max() < 1:
            scale, unit = 1e3, "ms"
        for i, t in enumerate(traces):
            y = np.asarray(trace(rr, t)).real
            a.plot(x * scale, y, "k" + styles[i % 4], lw=1.2, label=t)
        a.set_xlabel(xlabel or f"시간 ({unit})")
        a.set_ylabel("전압 (V)" if all(t.lower().startswith("v") for t in traces) else "값")
        a.grid(True, color="0.85", lw=0.5)
        if len(traces) > 1:
            a.legend(frameon=False)
    if title:
        fig.suptitle(title)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    print(f"✓ {out}")


def value(raw: Path, name: str, at: float):
    import numpy as np
    rr = read_raw(raw)
    x = axis(rr)
    y = np.asarray(trace(rr, name))
    v = np.interp(at, x, y.real) + (1j * np.interp(at, x, y.imag) if np.iscomplexobj(y) else 0)
    if np.iscomplexobj(y):
        print(f"{name} @ {at:g}: |{abs(v):.6g}| ({20 * np.log10(abs(v)):.3f} dB), {np.degrees(np.angle(v)):.2f}°")
    else:
        print(f"{name} @ {at:g}: {float(np.real(v)):.6g}")


def nodes(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    conn: dict[str, list[str]] = {}
    print("| 소자 | 연결 노드 | 값·모델 |\n|---|---|---|")
    counts = {"r": 2, "c": 2, "l": 2, "v": 2, "i": 2, "d": 2, "q": 3, "m": 4, "j": 3, "e": 4, "g": 4, "b": 2}
    for _, ln in logical_lines(text):
        tok = ln.split()
        head = tok[0].lower()
        if head.startswith(".") or head[0] not in counts and head[0] != "x":
            continue
        if head[0] == "x":
            args = [t for t in tok[1:] if "=" not in t]
            ns, rest = args[:-1], args[-1:]
        else:
            n = counts[head[0]]
            ns, rest = tok[1:1 + n], tok[1 + n:]
        print(f"| {tok[0]} | {', '.join(ns)} | {' '.join(rest)} |")
        for nd in dict.fromkeys(ns):
            conn.setdefault(nd, []).append(tok[0])
    print("\n| 노드 | 붙는 소자 |\n|---|---|")
    for nd, els in sorted(conn.items(), key=lambda kv: (kv[0] != "0", kv[0])):
        print(f"| {'0 (GND)' if nd == '0' else nd} | {', '.join(els)} |")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("lint"); p.add_argument("cir", type=Path)
    p = sub.add_parser("run"); p.add_argument("cir", type=Path)
    p = sub.add_parser("plot"); p.add_argument("raw", type=Path); p.add_argument("-t", "--traces", required=True)
    p.add_argument("-o", "--out", type=Path, required=True); p.add_argument("--bode", action="store_true")
    p.add_argument("--xlabel"); p.add_argument("--title")
    p = sub.add_parser("nodes"); p.add_argument("cir", type=Path)
    p = sub.add_parser("value"); p.add_argument("raw", type=Path); p.add_argument("-t", "--trace", required=True)
    p.add_argument("--at", required=True)
    a = ap.parse_args()
    if a.cmd == "lint":
        issues = lint(a.cir)
        print("\n".join(f"⚠ {i}" for i in issues) if issues else "✓ LTspice·ngspice 공통 문법")
        sys.exit(1 if issues else 0)
    if a.cmd == "run":
        issues = lint(a.cir)
        if issues:
            print("\n".join(f"⚠ {i}" for i in issues))
            sys.exit("✗ lint부터 고친다")
        run(a.cir)
    elif a.cmd == "nodes":
        nodes(a.cir)
    elif a.cmd == "plot":
        plot(a.raw, [t.strip() for t in a.traces.split(",")], a.out, a.bode, a.xlabel, a.title)
    elif a.cmd == "value":
        at = num(a.at)
        if at is None:
            sys.exit(f"✗ --at 값을 읽을 수 없음: {a.at}")
        value(a.raw, a.trace, at)


if __name__ == "__main__":
    main()
