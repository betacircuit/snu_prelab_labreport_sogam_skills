#!/usr/bin/env python3
"""MATLAB 과제 코드 검사·실행·제출 묶음 (기초전자기학 및 연습 HW, snu-em-hw)

  python mcode.py check courses/em/hw01/code/HW1.m --problems 1 2 3 --forbid "1:sinc,subplot"   # 제출 규칙·과제 제약 검사
  python mcode.py run   courses/em/hw01/code/HW1.m       # MATLAB(없으면 Octave)로 실행 → figs/figN.png, code/run.log
  python mcode.py pack  courses/em/hw01 [--pdf 파일.pdf]  # 제출용 zip: HW1_이름_학번.zip = PDF + HW1.m

검사 (과목 스킬 references/course.md의 제출 규칙) — 코드는 절대 고치지 않는다. 걸린 것은 본인에게 채팅으로 알리기만 한다.
  - 첫 줄 'clc; clear;' (두 줄로 나뉘었으면 참고)
  - 한글 주석 (참고 — 과제 공지는 영어 주석)
  - 문제 절('%% Problem N', '%% 문제 N')마다 주석이 있다
  - --forbid: 과제가 금지한 함수
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

SECTION_RE = re.compile(r"^\s*%%\s*(?:Problem|Prob\.?|P|Q|문제|과제)\s*([0-9]+(?:\.[0-9a-z]+)?|[0-9]+\s*\([a-z]\))", re.I)


def check(path: Path, problems: list[str] | None = None, forbid: list[str] | None = None) -> tuple[list[str], list[str]]:
    """→ (알릴 것, 참고). 코드는 절대 고치지 않는다 — 결과는 채팅으로 알리기만 한다.
    forbid: ['1:sinc,subplot'] = Problem 1에서 쓰면 안 되는 함수 (과제 제약)"""
    notes, info = [], []
    if not re.fullmatch(r"HW\d+\.m", path.name):
        info.append(f"파일 이름 '{path.name}' — zip에는 HW1.m 이름으로 넣는다 (pack이 처리)")
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    heads = [re.sub(r"\s+", " ", ln.strip()) for ln in lines if ln.strip() and not ln.strip().startswith("%")][:2]
    if not heads or not re.match(r"clc;?\s*clear", heads[0]):
        if len(heads) == 2 and heads[0].startswith("clc") and heads[1].startswith("clear"):
            info.append("clc;와 clear;가 두 줄로 나뉘어 있다 — 과제 공지는 '첫 줄에 clc; clear;' (본인에게 한 줄로 합칠지 물어본다)")
        else:
            notes.append(f"첫 줄이 'clc; clear;'가 아니다: '{(heads[0] if heads else '')[:40]}'")
    kor = [i for i, ln in enumerate(lines, 1) if "%" in ln and re.search(r"[가-힣]", ln.split("%", 1)[1])]
    if kor:
        info.append(f"한글 주석 {len(kor)}줄 ({', '.join(map(str, kor[:6]))}행) — 과제 공지는 '코드 주석(영어)'. 문제 제목 같은 한글이면 괜찮은지 본인에게 확인")
    # 문제 절
    secs: list[tuple[str, list[str]]] = []
    for ln in lines:
        m = SECTION_RE.match(ln)
        if m:
            secs.append((m.group(1).replace(" ", ""), []))
        elif secs:
            secs[-1][1].append(ln)
    if not secs:
        info.append("'%% Problem 1'·'%% 문제 1' 같은 문제 절이 없다 — 보고서에서 문제별 코드 사진으로 나눠 보인다")
    for num, body in secs:
        code = [ln for ln in body if ln.strip() and not ln.strip().startswith("%")]
        com = [ln for ln in body if "%" in ln and ln.strip() not in ("%", "%%")]
        if not com:
            notes.append(f"문제 {num}: 주석이 없다 (과제 공지: 문제마다 영어 주석)")
    for rule in forbid or []:
        num, _, funcs = rule.partition(":")
        body = next((b for n, b in secs if n == num.strip()), None)
        if body is None:
            continue
        code_only = "\n".join(ln.split("%", 1)[0] for ln in body)   # 주석은 빼고
        for fn in filter(None, (f.strip() for f in funcs.split(","))):
            if re.search(rf"(?<![\w.]){re.escape(fn)}\s*\(", code_only):
                notes.append(f"문제 {num}: 과제가 금지한 {fn}()를 썼다")
    if problems:
        have = {n for n, _ in secs}
        miss = [p for p in problems if p not in have]
        if miss and secs:
            notes.append(f"코드에서 절을 못 찾은 문제: {', '.join(miss)}")
    return notes, info


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


# 그림 수치 요약: 결과 사진에서 읽은 값(축 범위, 봉우리, 곡선 수)을 대조하는 용도. 보고서에는 넣지 않는다
FIG_DATA = ("__fid = fopen('{out}', 'w'); __h = findall(0, 'type', 'figure'); "
            "for __i = 1:numel(__h), __n = __h(__i); if isobject(__n), __n = get(__n, 'Number'); end; "
            "__ax = flipud(findall(__h(__i), 'type', 'axes')); "   # 만든 순서 (subplot 위 칸부터)
            "for __k = 1:numel(__ax), __a = __ax(__k); if strcmpi(get(__a, 'Tag'), 'legend'), continue; end; __xl = get(__a, 'XLim'); __yl = get(__a, 'YLim'); "
            "__L = findall(__a, 'type', 'line'); __q = findall(__a, 'type', 'hggroup'); "
            "fprintf(__fid, 'figure %d axes %d: xlim [%g, %g], ylim [%g, %g], lines %d, other %d\\n', __n, __k, __xl(1), __xl(2), __yl(1), __yl(2), numel(__L), numel(__q)); "
            "for __m = 1:numel(__L), __x = get(__L(__m), 'XData'); __y = get(__L(__m), 'YData'); __nm = get(__L(__m), 'DisplayName'); "
            "if isempty(__y) || ~isnumeric(__y), continue; end; [__y1, __i1] = max(__y(:)); [__y0, __i0] = min(__y(:)); "
            "fprintf(__fid, '  line %d \"%s\": %d points, max %.4g at x = %.4g, min %.4g at x = %.4g\\n', __m, __nm, numel(__y), __y1, __x(__i1), __y0, __x(__i0)); "
            "end; end; end; fclose(__fid);")


def run(path: Path, figs: Path | None = None, timeout: int = 600) -> int:
    """MATLAB 또는 Octave로 실행한다. 그림은 figs/figN.png (N = figure 번호), 출력은 code/run.log,
    그림 수치 요약(축 범위, 선마다 최댓값·최솟값 위치)은 code/figdata.txt — 사진 판독 대조용"""
    path = path.resolve()
    figs = (figs or path.parent.parent / "figs").resolve()
    figs.mkdir(parents=True, exist_ok=True)
    save = SAVE_FIGS.format(figs=figs.as_posix())
    data = path.parent / "figdata.txt"
    body = f"cd('{path.parent.as_posix()}'); run('{path.name}'); {save}; {FIG_DATA.format(out=data.as_posix())}"
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
    if data.exists():
        print(f"  그림 수치 요약 {data.name} — 결과 사진에서 읽은 축 범위·극값·곡선 수와 대조한다 (보고서에는 사진 값만)")
        print("    " + "\n    ".join(data.read_text(encoding="utf-8", errors="replace").splitlines()[:20]))
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
        ms = sorted((hw_dir / "code").glob("*.m"))
        if len(ms) != 1:
            sys.exit(f"✗ 코드가 없다: {code}")
        code = ms[0]
    ws = find_workspace(hw_dir)
    cands = [pdf] if pdf else [hw_dir / "build" / f"{stem}.pdf", (ws / "out" / str(v.get("key")) / f"{stem}.pdf") if ws else None]
    pdf = next((Path(c) for c in cands if c and Path(c).exists()), None)
    if pdf is None:
        sys.exit(f"✗ PDF가 없다 — Word에서 '{stem}.pdf'로 저장한 뒤 --pdf로 알려 준다")
    notes, _ = check(code)
    for e in notes:
        print("  ! 알릴 것:", e)
    out = hw_dir / "build" / f"{stem}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pdf, f"{stem}.pdf")
        z.write(code, f"HW{v['lab_num']}.m")   # 본인 파일 그대로, 이름만 규칙대로
    if ws:
        d = ws / "out" / str(v.get("key"))
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out, d / out.name)
    print(f"✓ 제출 묶음 {out.name}: {stem}.pdf + HW{v['lab_num']}.m")
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
        notes, info = check(a.m, a.problems, a.forbid)
        for e in notes:
            print("  ! 알릴 것:", e)
        for w in info:
            print("  · 참고:", w)
        print("✓ 코드 검사 통과" if not notes else f"코드 검사: 알릴 것 {len(notes)}건 — 코드는 고치지 말고 본인에게 채팅으로 알린다")
        return 1 if notes else 0
    if a.cmd == "run":
        return run(a.m, a.figs)
    pack(a.hw_dir, a.pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
