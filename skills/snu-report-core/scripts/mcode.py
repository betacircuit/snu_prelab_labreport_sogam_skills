#!/usr/bin/env python3
"""MATLAB 과제 코드 검사·실행·제출 묶음 (기초전자기학 및 연습 HW, snu-em-hw)

  python mcode.py check courses/em/hw01/code/HW1.m --problems 1 2 3 --forbid "1:sinc,subplot"   # 제출 규칙·과제 제약 검사
  python mcode.py run   courses/em/hw01/code/HW1.m       # MATLAB(없으면 Octave)로 실행 → figs/figN.png, code/run.log
  python mcode.py pack  courses/em/hw01 [--pdf 파일.pdf]  # 제출용 zip: HW1_이름_학번.zip = PDF + HW1.m

검사 (과목 스킬 references/course.md의 제출 규칙)
  - 파일 이름이 HW{N}.m
  - 첫 줄이 'clc; clear;'
  - 한글 등 비ASCII 문자가 없다 (주석은 영어로)
  - 문제마다 '%% Problem N' 절이 있고, 절마다 주석이 있다 (코드 6줄에 주석 1줄 안쪽이면 경고)
"""
from __future__ import annotations

import _console  # noqa: F401  (Windows에서 한글·기호 출력)
import argparse
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ws import find_tool, find_workspace  # noqa: E402

SECTION_RE = re.compile(r"^\s*%%\s*(?:Problem|Prob\.?|P)\s*([0-9]+(?:\.[0-9a-z]+)?|[0-9]+\s*\([a-z]\))", re.I)


def check(path: Path, problems: list[str] | None = None, forbid: list[str] | None = None) -> tuple[list[str], list[str]]:
    """→ (오류, 경고). forbid: ['1:sinc,subplot'] = Problem 1에서 쓰면 안 되는 함수 (과제 제약)"""
    errs, warns = [], []
    if not re.fullmatch(r"HW\d+\.m", path.name):
        errs.append(f"파일 이름 '{path.name}' — HW1.m 꼴이어야 한다")
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    first = next((ln for ln in lines if ln.strip()), "")
    if re.sub(r"\s+", " ", first.strip()) not in ("clc; clear;", "clc; clear; close all;", "clc; clear all;"):
        errs.append(f"첫 줄이 'clc; clear;'가 아니다: '{first.strip()[:40]}'")
    for i, ln in enumerate(lines, 1):
        bad = [c for c in ln if ord(c) > 127]
        if bad:
            errs.append(f"{i}행에 비ASCII 문자 '{''.join(bad[:6])}' — 주석·문자열은 영어로")
    # 문제 절
    secs: list[tuple[str, list[str]]] = []
    for ln in lines:
        m = SECTION_RE.match(ln)
        if m:
            secs.append((m.group(1).replace(" ", ""), []))
        elif secs:
            secs[-1][1].append(ln)
    if not secs:
        errs.append("'%% Problem 1' 같은 문제 절이 없다 — 문제마다 절을 나누고 영어 주석을 단다")
    for num, body in secs:
        code = [ln for ln in body if ln.strip() and not ln.strip().startswith("%")]
        com = [ln for ln in body if "%" in ln and ln.strip() not in ("%", "%%")]
        if not com:
            errs.append(f"Problem {num}: 주석이 없다")
        elif len(code) > 6 * len(com):
            warns.append(f"Problem {num}: 코드 {len(code)}줄에 주석 {len(com)}줄 — 무엇을 계산하는지 주석을 더 단다")
    for rule in forbid or []:
        num, _, funcs = rule.partition(":")
        body = next((b for n, b in secs if n == num.strip()), None)
        if body is None:
            continue
        code_only = "\n".join(ln.split("%", 1)[0] for ln in body)   # 주석은 빼고
        for fn in filter(None, (f.strip() for f in funcs.split(","))):
            if re.search(rf"(?<![\w.]){re.escape(fn)}\s*\(", code_only):
                errs.append(f"Problem {num}: 금지된 함수 {fn}()를 썼다 (과제 제약)")
    if problems:
        have = {n for n, _ in secs}
        miss = [p for p in problems if p not in have]
        if miss:
            errs.append(f"코드에 없는 문제: {', '.join(miss)}")
    return errs, warns


CODE_TAG = re.compile(r"(?m)^\{\{\s*code\s*:\s*(?:Problem|Prob\.?|P)?\s*([^}]+?)\s*\}\}\s*$")


def sections(path: Path) -> dict[str, str]:
    """HW.m → {'1': '%% Problem 1 ...\n코드', ...} (절 머리 줄 포함)"""
    out, cur = {}, None
    for ln in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = SECTION_RE.match(ln)
        if m:
            cur = m.group(1).replace(" ", "")
            out[cur] = [ln]
        elif cur:
            out[cur].append(ln)
    return {k: "\n".join(v).rstrip() for k, v in out.items()}


def include_code(md: str, path: Path) -> tuple[str, list[str]]:
    """원고의 {{code: Problem 1}} 줄을 m-file의 그 절 코드 블록으로 바꾼다 (보고서 코드 = 제출 코드)."""
    secs = sections(path) if path.exists() else {}
    missing = []

    def rep(m):
        k = m.group(1).replace(" ", "")
        if k not in secs:
            missing.append(k)
            return f"[TODO: {path.name}에 Problem {k} 절이 없음]"
        return "```matlab\n" + secs[k] + "\n```"
    return CODE_TAG.sub(rep, md), missing


SAVE_FIGS = ("__h = findall(0, 'type', 'figure'); "
             "for __i = 1:numel(__h), __n = __h(__i); if isobject(__n), __n = get(__n, 'Number'); end; "
             "print(__h(__i), fullfile('{figs}', sprintf('fig%d.png', __n)), '-dpng', '-r200'); end")


def run(path: Path, figs: Path | None = None, timeout: int = 600) -> int:
    """MATLAB 또는 Octave로 실행한다. 그림은 figs/figN.png (N = figure 번호), 출력은 code/run.log"""
    path = path.resolve()
    figs = (figs or path.parent.parent / "figs").resolve()
    figs.mkdir(parents=True, exist_ok=True)
    save = SAVE_FIGS.format(figs=figs.as_posix())
    body = f"cd('{path.parent.as_posix()}'); run('{path.name}'); {save}"
    if find_tool("matlab"):
        cmd, who = [find_tool("matlab"), "-batch", body], "MATLAB"
    elif find_tool("octave-cli") or find_tool("octave"):
        exe = find_tool("octave-cli") or find_tool("octave")
        pre = "set(0, 'defaultfigurevisible', 'off'); "
        cmd, who = [exe, "--no-gui", "--quiet", "--no-window-system", "--eval", pre + body], "Octave"
    else:
        print("✗ MATLAB도 Octave도 없다 — 사용자에게 HW 코드를 실행해 그림(PNG)과 명령 창 출력을 달라고 한다")
        return 2
    log = path.parent / "run.log"
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    log.write_text(r.stdout + ("\n--- stderr ---\n" + r.stderr if r.stderr.strip() else ""), encoding="utf-8")
    pngs = sorted(figs.glob("fig*.png"))
    print(f"{'✓' if r.returncode == 0 else '✗'} {who} 실행 (종료 코드 {r.returncode}) — 출력 {log}, 그림 {len(pngs)}개 → {figs}")
    if r.returncode != 0:
        print(r.stderr.strip()[-1500:] or r.stdout.strip()[-1500:])
    elif who == "Octave":
        print("  (Octave로 돌렸다. MATLAB 전용 함수가 있으면 결과가 다를 수 있으니 보고서 전에 사용자 MATLAB에서 한 번 확인 부탁)")
    return r.returncode


def pack(hw_dir: Path, pdf: Path | None = None) -> Path:
    """제출용 zip: <stem>.zip 안에 <stem>.pdf 와 HW{N}.m"""
    from build import load_vars, submission_stem
    hw_dir = hw_dir.resolve()
    v = load_vars(hw_dir, "hw")
    stem = submission_stem("hw", v)
    code = hw_dir / "code" / f"HW{v['lab_num']}.m"
    if not code.exists():
        sys.exit(f"✗ 코드가 없다: {code}")
    ws = find_workspace(hw_dir)
    cands = [pdf] if pdf else [hw_dir / "build" / f"{stem}.pdf", (ws / "out" / str(v.get("key")) / f"{stem}.pdf") if ws else None]
    pdf = next((Path(c) for c in cands if c and Path(c).exists()), None)
    if pdf is None:
        sys.exit(f"✗ PDF가 없다 — Word에서 '{stem}.pdf'로 저장한 뒤 --pdf로 알려 준다")
    errs, _ = check(code)
    if errs:
        sys.exit("✗ 코드 검사 실패:\n  - " + "\n  - ".join(errs))
    out = hw_dir / "build" / f"{stem}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pdf, f"{stem}.pdf")
        z.write(code, code.name)
    if ws:
        d = ws / "out" / str(v.get("key"))
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out, d / out.name)
    print(f"✓ 제출 묶음 {out.name}: {stem}.pdf + {code.name}")
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("m", type=Path); c.add_argument("--problems", nargs="*")
    c.add_argument("--forbid", nargs="*", help="과제 제약: '1:sinc,subplot' = Problem 1에서 sinc(), subplot() 금지")
    r = sub.add_parser("run"); r.add_argument("m", type=Path); r.add_argument("--figs", type=Path)
    p = sub.add_parser("pack"); p.add_argument("hw_dir", type=Path); p.add_argument("--pdf", type=Path)
    a = ap.parse_args()
    if a.cmd == "check":
        errs, warns = check(a.m, a.problems, a.forbid)
        for w in warns:
            print("  ⚠", w)
        for e in errs:
            print("  ✗", e)
        print("✓ 코드 검사 통과" if not errs else f"코드 검사: 오류 {len(errs)}건")
        return 1 if errs else 0
    if a.cmd == "run":
        return run(a.m, a.figs)
    pack(a.hw_dir, a.pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
