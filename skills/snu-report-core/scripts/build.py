#!/usr/bin/env python3
"""마크다운 원고 → 스타일 적용된 docx → pdf

사용:
  python build.py <lab_dir> prelab           # <lab_dir>/prelab/prelab.md  → build/prelab01_학번_이름.docx
  python build.py <lab_dir> report           # <lab_dir>/report/report.md  → build/lab01_학번_이름.docx
  python build.py <lab_dir> report --pdf     # + 미리보기 PDF (build/preview/) — 확인용
  python build.py <lab_dir> report --final   # 미해결 상태 표시가 남아 있으면 실패

사용자에게 주는 결과물은 항상 .docx (수정 가능). PDF 변환·제출은 사용자가 Word에서 한다.

원고 문법 (pandoc markdown + 아래 확장):
  # 제목               → 자동 번호 "1." / "1.1)" (style.yaml numbering.heading)
  # 4.2 3-bit comparator → "2. 4.2) 3-bit comparator" (가이드북 문항 번호에 ')'를 붙인다, proof.normalize_headings)
  ## 4.2 가 설계         → "2.1) 가) 설계" (상위 절과 같은 문항 번호는 되풀이하지 않는다)
  # 참고문헌 {-}        → 번호 없는 제목
  ![캡션](figs/a.png){#fig:and width=60%}   → 틀 안 "Fig.1 - 캡션" (style.yaml caption_format)
  Table: 캡션 {#tbl:tt}                      → 표 맨 아래 캡션 행 "Table.1 - 캡션"
  @fig:and, @tbl:tt                          → "Fig.1", "Table.1"
  $\\overline{A}B + A\\overline{B}$            → Word 수식
  상태 표시 (references/evidence.md):
    [TODO: …] [미제공: …] [확인 필요: …] [판독 불가: …]  → 초안에서 형광펜, --final 이면 빌드 중단
    [미측정: …] [미수행: …]                            → 초안에서 형광펜, --final 이면 경고
                                                          (최종본에서는 문장으로 풀어 쓸 것)
"""
from __future__ import annotations

import _console  # noqa: F401  (Windows에서 한글·기호 출력)
import argparse
import copy
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml
from docx import Document
from docx.oxml.ns import qn

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"
sys.path.insert(0, str(HERE))
from docx_post import break_before_frames, postprocess, split_captions  # noqa: E402
from make_template import build_reference  # noqa: E402
from ws import course_defaults, find_tool, find_workspace, remember_engine  # noqa: E402

KIND_LABEL = {"prelab": "Prelab Report", "report": "Lab Report", "sogam": "Seminar Reflection", "hw": "Homework"}
KIND_KO = {"prelab": "예비보고서", "report": "결과보고서", "sogam": "소감문", "hw": "결과 보고서"}
SRC = {"prelab": "prelab/prelab.md", "report": "report/report.md", "sogam": "sogam.md", "hw": "hw.md"}
BLOCKING = ("TODO", "미제공", "확인 필요", "판독 불가")
SOFT = ("미측정", "미수행")
MARK_RE = re.compile(r"\[(" + "|".join(BLOCKING + SOFT) + r")(?::[^\]]*)?\]")


# ───────────────────────── config ─────────────────────────
def find_upward(start: Path, name: str) -> Path | None:
    for d in [start, *start.parents]:
        if (d / name).exists():
            return d / name
    return None


class _D(dict):
    def __missing__(self, k):
        return ""


def load_vars(lab_dir: Path, kind: str) -> dict:
    meta = yaml.safe_load((lab_dir / "meta.yaml").read_text(encoding="utf-8")) or {}
    prof_path = find_upward(lab_dir, "profile.yaml")
    prof = yaml.safe_load(prof_path.read_text(encoding="utf-8")) if prof_path else {}
    # 과목 설정: 과목 스킬의 course.yaml(과목명, 파일명 규칙) ← 작업 폴더 courses/<과목>/course.yaml(조, 조원)
    course_path = find_upward(lab_dir, "course.yaml")
    over = (yaml.safe_load(course_path.read_text(encoding="utf-8")) or {}) if course_path else {}
    key = str(over.get("key") or lab_dir.resolve().parent.name)
    course = {**course_defaults(key), **over, "key": key}
    v = _D({**(prof or {}), **course, **meta})
    v["kind"] = KIND_LABEL[kind]
    v["kind_key"] = kind
    lab = meta.get("lab", meta.get("week", meta.get("hw", "")))
    v["lab"] = f"{int(lab):02d}" if str(lab).isdigit() else str(lab)
    mates = v.get("teammates") or []
    v["teammates"] = ", ".join(m["name"] if isinstance(m, dict) else str(m) for m in mates)
    v["lab_date"] = str(v.get("lab_date", ""))
    v["lab_num"] = str(int(lab)) if str(lab).isdigit() else str(lab)
    v["kind_ko"] = KIND_KO[kind]
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v["lab_date"])
    v["lab_date_ko"] = f"{m.group(1)}년 {int(m.group(2))}월 {int(m.group(3))}일" if m else v["lab_date"]
    v["team"] = str(v.get("team", "") or "")
    return v


def fill_line(tmpl: str, v: dict) -> str | None:
    """변수가 하나라도 비어 있으면 None (그 줄 생략)."""
    keys = re.findall(r"\{(\w+)\}", tmpl)
    if any(not str(v.get(k, "")).strip() or str(v.get(k, "")).startswith("[") for k in keys):
        return None
    return tmpl.format_map(v)


# ───────────────────────── 제출 파일명 (Lab00 가이드라인: 틀리면 감점) ─────────────────────────
FILENAME_RE = re.compile(r"^(prelab|lab)\d{2}_\d{4}-\d{5}_[가-힣A-Za-z]+$")
HW_FILENAME_RE = re.compile(r"^HW\d+_[가-힣A-Za-z]+_\d{4}-\d{5}$")   # 기초전자기학: HW1_홍길동_2025-12345


DEFAULT_FILENAME = {"prelab": "prelab{lab}_{student_id}_{name}", "report": "lab{lab}_{student_id}_{name}",
                    "sogam": "sogam{lab}_{student_id}_{name}", "hw": "HW{lab_num}_{name}_{student_id}"}


def submission_stem(kind: str, v: dict) -> str:
    """course.yaml의 filename 규칙. prelab/report는 prelab01_2025-12345_홍길동 형식을 검사한다."""
    tmpl = (v.get("filename") or {}).get(kind) or DEFAULT_FILENAME[kind]
    stem = tmpl.format_map(v)
    if kind in ("prelab", "report") and not FILENAME_RE.match(stem):
        sys.exit(f"✗ 제출 파일명 규칙 위반: {stem!r} — profile.yaml의 student_id(2025-12345 형식)/name, course.yaml의 filename, meta.yaml의 lab 확인")
    if kind == "hw" and not HW_FILENAME_RE.match(stem):
        sys.exit(f"✗ 제출 파일명 규칙 위반: {stem!r} — HW1_홍길동_2025-12345 꼴 (profile.yaml, meta.yaml의 hw 확인)")
    return stem



# ───────────────────────── 수식 띄어쓰기 ─────────────────────────
_BINOPS = [r"\approx", r"\times", r"\oplus", r"\cdot", r"\neq", r"\leq", r"\geq", r"\le", r"\ge", "=", "+", "<", ">"]
MATH_RE = re.compile(r"(?<!\\)(\$\$.+?\$\$|\$[^$\n]+?\$)", re.S)


def space_math(expr: str) -> str:
    """이항 연산자(=, +, −, ×, ≈ …) 양옆과 단위 앞에 공백. 첨자 안은 건드리지 않는다."""
    sp = r"\text{ }"   # Word·LibreOffice·한컴 모두에서 보이는 공백 (\; 같은 수식 공백은 일부 뷰어가 무시)
    expr = expr.replace("\\qquad", r"\text{      }").replace("\\quad", r"\text{   }")
    expr = expr.replace("\\ ", sp).replace("\\,", sp).replace("\\;", sp)
    out, i, n = [], 0, len(expr)
    while i < n:
        c = expr[i]
        if c in "_^" and i + 1 < n and expr[i + 1] == "{":  # 첨자 블록은 그대로
            depth, j = 0, i + 1
            while j < n:
                depth += expr[j] == "{"
                depth -= expr[j] == "}"
                j += 1
                if depth == 0:
                    break
            out.append(expr[i:j])
            i = j
            continue
        op = next((o for o in _BINOPS if expr.startswith(o, i) and not (o[0] == "\\" and i + len(o) < n and expr[i + len(o)].isalpha())), None)
        prev = "".join(out).rstrip()
        if op is None and c == "-" and prev and (prev[-1].isalnum() or prev[-1] in "})"):
            op = "-"
        if op:
            while out and out[-1] in (" ", sp):
                out.pop()
            out.append(sp + op + sp)
            i += len(op)
            while i < n and expr[i] == " ":
                i += 1
            if expr.startswith(sp, i):
                i += len(sp)
            continue
        if expr.startswith(sp, i) and out and out[-1].endswith(sp):
            i += len(sp)
            continue
        out.append(c)
        i += 1
    return "".join(out)


# ───────────────────────── 수식 글자 세우기 ─────────────────────────
# 변수만 기울임. 함수 이름(sin, sinc …)과 단위(V/m, F/m, N m^2/C^2 …)는 바로 세운다 (사용자 지적: 과도한 기울임).
_FUNCS = ("sinh", "cosh", "tanh", "sin", "cos", "tan", "cot", "sec", "csc", "exp", "log", "ln", "arctan", "arcsin", "arccos")
_FUNC_RE = re.compile(r"(?<![\\A-Za-z])(sinc|" + "|".join(_FUNCS) + r")(?![A-Za-z])")
_UATOM = r"(?:[pnuµμmckMG]?(?:Hz|Wb|rad|dB|V|A|Ω|F|H|s|m|C|N|J|W|T|S|g|K)|\\Omega)(?:\^\{?-?\d+\}?)?"
_UNIT_RE = re.compile(r"(?P<pre>[\d}])(?P<sp>\s*(?:\\[ ,;:]|~)\s*|\s+)(?P<u>" + _UATOM +
                      r"(?:\s*(?:/|\\cdot|\\[ ,;])\s*" + _UATOM + r")*)(?![A-Za-z{])")
_PROTECT_RE = re.compile(r"\\(?:text|mathrm|operatorname|mathit|mathbf)\s*\{[^{}]*\}")


def upright_math(expr: str) -> str:
    """수식 안 함수 이름은 \\sin·\\operatorname{sinc}로, 숫자 뒤 단위는 \\mathrm{…}으로 (이미 \\text·\\mathrm이면 그대로)."""
    parts, last = [], 0
    for m in _PROTECT_RE.finditer(expr):
        parts.append((expr[last:m.start()], True))
        parts.append((m.group(0), False))
        last = m.end()
    parts.append((expr[last:], True))
    out = []
    for seg, edit in parts:
        if edit:
            seg = _FUNC_RE.sub(lambda m: r"\operatorname{sinc}" if m.group(1) == "sinc" else "\\" + m.group(1), seg)
            seg = _UNIT_RE.sub(lambda m: m["pre"] + r"\ " + r"\mathrm{" + re.sub(r"\\ ", r"\\,", m["u"].strip()) + "}", seg)
        out.append(seg)
    return "".join(out)


def space_all_math(text: str) -> str:
    parts = re.split(r"(```.*?```)", text, flags=re.S)
    for k in range(0, len(parts), 2):
        parts[k] = MATH_RE.sub(lambda m: (m.group(0)[:2] + space_math(upright_math(m.group(0)[2:-2])) + m.group(0)[-2:])
                               if m.group(0).startswith("$$") else "$" + space_math(upright_math(m.group(0)[1:-1])) + "$", parts[k])
    return "".join(parts)

NBSP = "\u00a0"
UNIT_RE = re.compile(r"(?<=\d) (?=(?:ns|us|ms|s|mV|V|mA|Ω|kΩ|MΩ|pF|nF|uF|Hz|kHz|MHz)(?![A-Za-z]))")
SHORT_EQ_RE = re.compile(r"(?<![A-Za-z0-9_\\{])([A-Za-z]) = ([A-Za-z0-9.]{1,4})(?![A-Za-z0-9_.])")


def nbsp_text(text: str) -> str:
    """수식 밖의 짧은 식(B = 1)과 숫자·단위(10 ns) 사이 공백을 줄바꿈 없는 공백으로."""
    parts = re.split(r"(```.*?```|\$\$.*?\$\$|\$[^$\n]+\$)", text, flags=re.S)
    for k in range(0, len(parts), 2):
        seg = UNIT_RE.sub(NBSP, parts[k])
        parts[k] = SHORT_EQ_RE.sub(lambda m: f"{m.group(1)}{NBSP}={NBSP}{m.group(2)}", seg)
    return "".join(parts)


# ───────────────────────── preprocessing ─────────────────────────
IMG_RE = re.compile(r"^(\s*)!\[(?P<cap>.*?)\]\((?P<src>[^)]+)\)(?P<attr>\{[^}]*\})?\s*$")
TBLCAP_RE = re.compile(r"^Table:\s*(?P<cap>.*?)\s*(?P<attr>\{[^}]*\})?\s*$")
HEAD_RE = re.compile(r"^(?P<hash>#{1,3})\s+(?P<text>.+?)\s*(?P<attr>\{[^}]*\})?\s*$")
ID_RE = re.compile(r"#((?:fig|tbl):[A-Za-z0-9_-]+)")


def _strip_id(attr: str | None) -> str:
    if not attr:
        return ""
    rest = ID_RE.sub("", attr[1:-1]).strip()
    return "{" + rest + "}" if rest else ""


def preprocess(md: str, st: dict) -> tuple[str, list[str]]:
    num = st["numbering"]
    fig_p, tbl_p = num["figure_prefix"], num["table_prefix"]
    cap_fmt = num.get("caption_format", "{prefix}.{n} - {text}")
    ref_fmt = num.get("ref_format", "{prefix}.{n}")
    labels: dict[str, str] = {}
    out, warnings = [], []
    nfig = ntbl = 0
    h = [0, 0, 0]
    in_code = False

    for line in md.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
            out.append(line)
            continue
        if in_code:
            out.append(line)
            continue

        m = HEAD_RE.match(line)
        if m:
            attr = m["attr"] or ""
            inner = attr[1:-1] if attr else ""
            unnumbered = bool(re.search(r"(^|\s)-(\s|$)", inner)) or ".unnumbered" in inner
            lvl = len(m["hash"])
            if num["heading"] and not unnumbered:
                h[lvl - 1] += 1
                for i in range(lvl, 3):
                    h[i] = 0
                fmts = num.get("heading_formats", ["{0}.", "{0}.{1}", "{0}.{1}.{2}"])
                n = fmts[lvl - 1].format(*h[:lvl])
                line = f"{m['hash']} {n} {m['text']} {attr}".rstrip()
            out.append(line)
            continue

        m = IMG_RE.match(line)
        if m and m["cap"]:
            nfig += 1
            for i in ID_RE.findall(m["attr"] or ""):
                labels[i] = ref_fmt.format(prefix=fig_p, n=nfig)
            cap = cap_fmt.format(prefix=fig_p, n=nfig, text=m["cap"])
            out.append(f"{m.group(1)}![{cap}]({m['src']}){_strip_id(m['attr'])}")
            continue

        m = TBLCAP_RE.match(line)
        if m:
            ntbl += 1
            for i in ID_RE.findall(m["attr"] or ""):
                labels[i] = ref_fmt.format(prefix=tbl_p, n=ntbl)
            out.append("Table: " + cap_fmt.format(prefix=tbl_p, n=ntbl, text=m["cap"]))
            continue

        # 상태 표시 형광펜
        line = MARK_RE.sub(lambda mm: f'[{mm.group(0).replace("[", "⟦").replace("]", "⟧")}]{{custom-style="Marker"}}', line)
        out.append(line)

    text = "\n".join(out)

    def ref(mm):
        key = mm.group(1)
        if key not in labels:
            warnings.append(f"정의되지 않은 참조: @{key}")
            return f"??{key}"
        return labels[key]

    text = re.sub(r"@((?:fig|tbl):[A-Za-z0-9_-]+)", ref, text)
    if st.get("math", {}).get("op_space", True):
        text = space_all_math(text)
    text = nbsp_text(text)
    return text, warnings


def title_md(v: dict, st: dict) -> str:
    tb = st.get("title_block", {})
    kind = v["kind_key"]
    title = tb.get(f"{kind}_title", "Lab {lab} : {title}").format_map(v)
    def pick(t):  # 한 줄에 후보 여러 개면 값이 다 채워지는 첫 후보 (조원이 없으면 조원 없는 줄로)
        for c in (t if isinstance(t, list) else [t]):
            got = fill_line(c, v)
            if got:
                return got
        return None
    lines = [x for x in (pick(t) for t in tb.get(f"{kind}_lines", [])) if x]
    if tb.get("mode", "block") == "page":
        meta = "\n".join(f"{x}\\" for x in lines).rstrip("\\")
        pb = '```{=openxml}\n<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n```'
        return (f'::: {{custom-style="Cover Kicker"}}\n{v.get("course", "")} · {v["kind"]}\n:::\n\n'
                f'::: {{custom-style="Title"}}\n{title}\n:::\n\n&nbsp;\n\n'
                f'::: {{custom-style="Cover Meta"}}\n{meta}\n:::\n\n{pb}\n')
    def gap(t: str) -> str:  # 두 칸 이상 공백은 em space로 (마크다운이 공백을 합치지 않게)
        return re.sub(r" {2,}", lambda mm: "\u2003" * (len(mm.group(0)) // 2), t)

    title_lines = "\\\n".join(gap(x.strip()) for x in title.split("\n") if x.strip())
    out = f'::: {{custom-style="Doc Title"}}\n{title_lines}\n:::\n\n'
    sub_t = tb.get(f"{kind}_subtitle")
    if sub_t:
        sub = fill_line(sub_t, v)
        if sub:
            out += f'::: {{custom-style="Doc Subtitle"}}\n{gap(sub)}\n:::\n\n'
    meta = "\n".join(f"{gap(x)}\\" for x in lines).rstrip("\\")
    if meta:
        out += f'::: {{custom-style="Doc Meta"}}\n{meta}\n:::\n\n'
    if tb.get("rule", False):
        out += '::: {custom-style="Doc Rule"}\n&nbsp;\n:::\n\n'
    return out


# ───────────────────────── postprocess ─────────────────────────
def one_column_cover(docx_path: Path):
    """본문이 다단일 때 표지는 1단으로 유지 (페이지 나누기 → 구역 나누기로 교체)."""
    doc = Document(docx_path)
    body_sect = doc.sections[-1]._sectPr
    for p in doc.paragraphs:
        brs = p._p.findall(".//" + qn("w:br"))
        if any(b.get(qn("w:type")) == "page" for b in brs):
            for r in list(p._p.findall(qn("w:r"))):
                p._p.remove(r)
            sp = copy.deepcopy(body_sect)
            cols = sp.find(qn("w:cols"))
            if cols is not None:
                cols.set(qn("w:num"), "1")
            p._p.get_or_add_pPr().append(sp)
            tp = body_sect.find(qn("w:titlePg"))
            if tp is not None:
                body_sect.remove(tp)
            break
    doc.save(docx_path)


def unescape_markers(docx_path: Path):
    """형광펜 표시용으로 바꿔 둔 ⟦ ⟧ 를 원래 대괄호로 되돌림."""
    doc = Document(docx_path)
    for t in doc.element.body.iter(qn("w:t")):
        if t.text and ("⟦" in t.text or "⟧" in t.text):
            t.text = t.text.replace("⟦", "[").replace("⟧", "]")
    doc.save(docx_path)


def to_pdf(docx_path: Path) -> Path:
    subprocess.run(
        [find_tool("soffice") or "soffice", "--headless", "--convert-to", "pdf", "--outdir", str(docx_path.parent), str(docx_path)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return docx_path.with_suffix(".pdf")


# ───────────────────────── main ─────────────────────────
def build(lab_dir: Path, kind: str, final=False, pdf=False, style_path: Path | None = None) -> Path:
    lab_dir = lab_dir.resolve()
    src = lab_dir / SRC[kind]
    src_dir = src.parent
    style_path = style_path or TEMPLATES / "style.yaml"
    st = yaml.safe_load(style_path.read_text(encoding="utf-8"))
    if kind == "hw":   # 과제는 'Problem 1)'이 곧 절 번호라 자동 번호(1.)를 붙이지 않는다
        st["numbering"]["heading"] = False
    v = load_vars(lab_dir, kind)

    raw = src.read_text(encoding="utf-8")
    code_free = re.sub(r"(?s)```.*?```", "", raw)
    marks = MARK_RE.findall(code_free)
    blocking = [m for m in MARK_RE.finditer(code_free) if m.group(1) in BLOCKING]
    soft = [m for m in MARK_RE.finditer(code_free) if m.group(1) in SOFT]
    if marks:
        print(f"⚠ 상태 표시 {len(marks)}개 (차단 {len(blocking)}, 미측정/미수행 {len(soft)})", file=sys.stderr)
        for m in (blocking + soft)[:15]:
            print("   ", m.group(0), file=sys.stderr)
    if final and blocking:
        sys.exit("✗ --final: [TODO]/[미제공]/[확인 필요]/[판독 불가]를 모두 해결한 뒤 다시 빌드하세요.")
    if final and soft:
        print("⚠ --final: [미측정]/[미수행] 표시는 최종본에서 문장으로 풀어 쓰는 것을 권장", file=sys.stderr)

    from style_check import check as style_check  # 문체 검사 (writing.md)
    for w in style_check(raw):
        print("  문체 ⚠", w, file=sys.stderr)
    from proof import check_text, docx_text, normalize_headings  # 오탈자 검사 (proofreading.md)
    raw, head_fixes = normalize_headings(raw)   # 가이드북 문항 번호: '4.2 …' → '4.2) …'
    for c in head_fixes:
        print("  제목 번호 고침:", c, file=sys.stderr)
    for w in check_text(raw):
        if not w.startswith("[제목 번호]"):
            print("  오탈자 ⚠", w, file=sys.stderr)

    code = lab_dir / "code" / f"HW{v['lab_num']}.m" if kind == "hw" else None
    if code is not None:   # 기초전자기학 HW: 같이 내는 MATLAB 코드 검사 (mcode.py)
        from mcode import check as mcheck
        if not code.exists():
            print(f"⚠ 코드 파일이 없다: {code}", file=sys.stderr)
        else:
            errs, cw = mcheck(code)
            for w in errs + cw:
                print("  코드 ⚠", w, file=sys.stderr)
        from mcode import include_code   # {{code: Problem 1}} → m-file의 그 절
        raw, missing = include_code(raw, code)
        for k in missing:
            print(f"⚠ {code.name}에 Problem {k} 절이 없다", file=sys.stderr)

    body, warns = preprocess(raw, st)
    for w in warns:
        print("⚠", w, file=sys.stderr)
    full = title_md(v, st) + "\n" + body

    stem = submission_stem(kind, v)
    out_dir = lab_dir / "build"
    out_dir.mkdir(exist_ok=True)
    out_docx = out_dir / f"{stem}.docx"

    with tempfile.TemporaryDirectory() as td:
        ref = build_reference(style_path, Path(td) / "ref.docx", v)
        md_tmp = Path(td) / "doc.md"
        md_tmp.write_text(full, encoding="utf-8")
        subprocess.run(
            [find_tool("pandoc") or "pandoc", str(md_tmp),
             "-f", "markdown+tex_math_dollars+pipe_tables+grid_tables+fenced_divs+raw_attribute+implicit_figures+bracketed_spans",
             "-o", str(out_docx), "--reference-doc", str(ref),
             "--resource-path", f"{src_dir}:{lab_dir}"],
            check=True,
        )
    unescape_markers(out_docx)
    res = postprocess(out_docx, st)
    if res.get("frames"):
        print(f"  표 {res['frames'][0]}개, 그림 {res['frames'][1]}개를 캡션 틀에 넣음")
    if st.get("title_block", {}).get("mode") == "page" and int(st["page"].get("columns", 1)) > 1:
        one_column_cover(out_docx)
    print("✓", out_docx)
    for w in check_text(docx_text(out_docx), is_docx=True):   # 빌드 결과를 다시 읽어 확인 (원고 검사와 겹치지 않는 것만)
        if w.startswith(("[제목 번호]", "[참조]", "[표시]", "[괄호]")):
            print("  결과물 ⚠", w, file=sys.stderr)
    # 전달용 사본: out/<과목>/파일명.docx (git에 올라가므로 GitHub에서도 받을 수 있다)
    ws = find_workspace(lab_dir)
    if ws:
        remember_engine(ws)
        deliver = ws / "out" / str(v.get("key") or lab_dir.parent.name)
        deliver.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_docx, deliver / out_docx.name)
        print("  전달용:", (deliver / out_docx.name).relative_to(ws))
    if pdf and find_tool("soffice"):
        # 미리보기 PDF: 제출용 docx는 그대로 두고 사본에서만 쪽 갈림 보정
        prev_dir = out_dir / "preview"
        prev_dir.mkdir(exist_ok=True)
        prev_docx = prev_dir / out_docx.name
        shutil.copy2(out_docx, prev_docx)
        out_pdf = to_pdf(prev_docx)
        for _ in range(8 if out_pdf.exists() else 0):
            splits = split_captions(out_pdf, st)
            if not splits or not break_before_frames(prev_docx, splits[:1], st):
                break
            out_pdf = to_pdf(prev_docx)
        print("  미리보기:", out_pdf) if out_pdf.exists() else print("⚠ PDF 변환 실패 (LibreOffice) — docx는 그대로 쓸 수 있다. Linux면 Writer가 빠졌을 수 있다: apt install libreoffice-writer", file=sys.stderr)
        if kind == "hw" and out_pdf.exists() and code is not None and code.exists():   # 제출용 PDF와 zip
            shutil.copy2(out_pdf, out_dir / f"{stem}.pdf")
            from mcode import pack
            try:
                pack(lab_dir, out_dir / f"{stem}.pdf")
            except SystemExit as e:
                print(e, file=sys.stderr)
    if kind == "hw" and code is not None and code.exists() and ws:
        shutil.copy2(code, ws / "out" / str(v.get("key") or lab_dir.parent.name) / code.name)
        if not (out_dir / f"{stem}.zip").exists():
            print(f"  제출: Word에서 '{stem}.pdf'로 저장 → python $E/mcode.py pack {lab_dir} --pdf <그 PDF> 로 zip")
    return out_docx


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("lab_dir", type=Path)
    ap.add_argument("kind", choices=["prelab", "report", "sogam", "hw"])
    ap.add_argument("--final", action="store_true", help="미해결 상태 표시가 남아 있으면 실패")
    ap.add_argument("--pdf", action="store_true", help="미리보기 PDF도 만든다 (build/preview/)")
    ap.add_argument("--style", type=Path)
    a = ap.parse_args()
    build(a.lab_dir, a.kind, final=a.final, pdf=a.pdf, style_path=a.style)
