#!/usr/bin/env python3
"""style.yaml → reference.docx (pandoc용 스타일 템플릿)

사용:
  python make_template.py                       # templates/reference.docx 생성 (머리말 변수 비움)
  python make_template.py --out ref.docx --var week=03 --var kind=Prelab ...

build.py 가 문서마다 이 함수를 호출해서 머리말에 주차/제목을 채운 템플릿을 만든다.
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

import yaml
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE.parent / "templates"


# ───────────────────────── helpers ─────────────────────────
def _rgb(hexstr: str) -> RGBColor:
    return RGBColor.from_string(hexstr.upper())


def _set_fonts(rpr_owner, en: str, ko: str):
    """rPr에 ascii/hAnsi(영문)와 eastAsia(한글) 글꼴을 모두 지정."""
    rpr = rpr_owner.get_or_add_rPr() if hasattr(rpr_owner, "get_or_add_rPr") else rpr_owner
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
        rfonts.attrib.pop(qn(attr), None)
    rfonts.set(qn("w:ascii"), en)
    rfonts.set(qn("w:hAnsi"), en)
    rfonts.set(qn("w:cs"), en)
    rfonts.set(qn("w:eastAsia"), ko)
    lang = rpr.find(qn("w:lang"))
    if lang is None:
        lang = OxmlElement("w:lang")
        rpr.append(lang)
    lang.set(qn("w:eastAsia"), "ko-KR")


def _style_font(style, en, ko, size=None, bold=None, color=None, italic=False):
    style.font.name = en
    if size is not None:
        style.font.size = Pt(size)
    if bold is not None:
        style.font.bold = bold
    style.font.italic = italic
    if color:
        style.font.color.rgb = _rgb(color)
    _set_fonts(style.element, en, ko)


def _para_spacing(style, before=None, after=None, line=None, indent=None, align=None, keep_next=None):
    pf = style.paragraph_format
    if before is not None:
        pf.space_before = Pt(before)
    if after is not None:
        pf.space_after = Pt(after)
    if line is not None:
        pf.line_spacing = line
    if indent is not None:
        pf.first_line_indent = Pt(indent)
    if align is not None:
        pf.alignment = align
    if keep_next is not None:
        pf.keep_with_next = keep_next


def _style(doc, name):
    """이름으로 스타일 찾기 (pandoc 템플릿은 'Heading 1'을 대문자로 저장해 python-docx 기본 조회가 실패함)."""
    for s in doc.styles:
        if s.name.lower() == name.lower():
            return s
    raise KeyError(name)


def _get_or_add_style(doc, name, based_on="Normal"):
    from docx.enum.style import WD_STYLE_TYPE

    try:
        return _style(doc, name)
    except KeyError:
        s = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        s.base_style = _style(doc, based_on)
        return s


def _border(tag, sz, color, val="single"):
    el = OxmlElement(f"w:{tag}")
    el.set(qn("w:val"), val)
    el.set(qn("w:sz"), str(sz))
    el.set(qn("w:space"), "0")
    el.set(qn("w:color"), color)
    return el


def _style_table(doc, st):
    """pandoc 표 스타일('Table')을 논문식 3선 표로 교체."""
    tbl_style = _style(doc, "Table").element
    # 기존 tblPr / tblStylePr 제거 후 재작성
    for child in list(tbl_style):
        if child.tag in (qn("w:tblPr"), qn("w:tblStylePr"), qn("w:rPr"), qn("w:pPr")):
            tbl_style.remove(child)

    accent = st["colors"]["accent"]
    ppr = OxmlElement("w:pPr")
    sp = OxmlElement("w:spacing")
    sp.set(qn("w:before"), "20")
    sp.set(qn("w:after"), "20")
    sp.set(qn("w:line"), "240")
    sp.set(qn("w:lineRule"), "auto")
    ppr.append(sp)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "center")
    ppr.append(jc)
    tbl_style.append(ppr)

    rpr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(st.get("table", {}).get("font_size", st["size"]["table"]) * 2)))
    rpr.append(sz)
    tbl_style.append(rpr)
    _set_fonts(rpr, st["fonts"]["body_en"], st["fonts"]["body_ko"])

    tblpr = OxmlElement("w:tblPr")
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), "center")
    tblpr.append(jc)
    borders = OxmlElement("w:tblBorders")  # 전체 격자 (모든 칸 구분선)
    for side, sz in (("top", 8), ("left", 4), ("bottom", 8), ("right", 4), ("insideH", 4), ("insideV", 4)):
        borders.append(_border(side, sz, accent))
    tblpr.append(borders)
    mar = OxmlElement("w:tblCellMar")
    for side in ("left", "right"):
        m = OxmlElement(f"w:{side}")
        m.set(qn("w:w"), "80")
        m.set(qn("w:type"), "dxa")
        mar.append(m)
    tblpr.append(mar)
    tbl_style.append(tblpr)

    tcfg = st.get("table", {})
    first = OxmlElement("w:tblStylePr")
    first.set(qn("w:type"), "firstRow")
    frpr = OxmlElement("w:rPr")
    if tcfg.get("header_bold", False):
        frpr.append(OxmlElement("w:b"))
    else:
        b0 = OxmlElement("w:b")
        b0.set(qn("w:val"), "0")
        frpr.append(b0)
    first.append(frpr)
    fill = str(tcfg.get("header_fill", "none"))
    if fill.lower() not in ("none", "", "ffffff"):
        ftcpr = OxmlElement("w:tcPr")
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), fill)
        ftcpr.append(shd)
        first.append(ftcpr)
    tbl_style.append(first)


def _add_field(paragraph, instr: str):
    run = paragraph.add_run()
    for kind, text in (("begin", None), ("instr", instr), ("separate", None), ("text", "1"), ("end", None)):
        if kind == "instr":
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = f" {text} "
        elif kind == "text":
            el = OxmlElement("w:t")
            el.text = text
        else:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), kind)
        run._r.append(el)
    return run


def _fill(tmpl: str, vars: dict) -> str:
    class D(dict):
        def __missing__(self, k):
            return ""

    return tmpl.format_map(D(vars)).strip(" ·")


def _bottom_rule_style(style, color, sz=6):
    ppr = style.element.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    pbdr.append(_border("bottom", sz, color))
    ppr.append(pbdr)


def _bottom_rule(paragraph, color, sz=4):
    ppr = paragraph._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    pbdr.append(_border("bottom", sz, color))
    ppr.append(pbdr)


# ───────────────────────── main builder ─────────────────────────
def build_reference(style_path: Path, out: Path, vars: dict | None = None) -> Path:
    vars = vars or {}
    st = yaml.safe_load(Path(style_path).read_text(encoding="utf-8"))
    F, S, SP, C = st["fonts"], st["size"], st["spacing"], st["colors"]

    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "default.docx"
        with open(base, "wb") as fh:
            subprocess.run(
                ["pandoc", "--print-default-data-file", "reference.docx"], stdout=fh, check=True
            )
        doc = Document(base)

    # docDefaults: 모든 스타일의 기본 글꼴
    defaults = doc.styles.element.find(qn("w:docDefaults"))
    rpr_default = defaults.find(qn("w:rPrDefault")).find(qn("w:rPr"))
    _set_fonts(rpr_default, F["body_en"], F["body_ko"])
    # 한글과 영문·숫자 사이 자동 간격 끄기 (Word 기본값은 켜짐 → "7 조", "4 개"처럼 벌어짐. 한글(HWP)과 같게)
    ppr_default = defaults.find(qn("w:pPrDefault")).find(qn("w:pPr"))
    for tag in ("w:autoSpaceDE", "w:autoSpaceDN"):  # 스키마 순서: DE → DN → spacing
        old = ppr_default.find(qn(tag))
        if old is not None:
            ppr_default.remove(old)
        el = OxmlElement(tag)
        el.set(qn("w:val"), "0")
        sp_el = ppr_default.find(qn("w:spacing"))
        if sp_el is not None:
            sp_el.addprevious(el)
        else:
            ppr_default.append(el)
    # LibreOffice는 docDefaults 값을 무시하므로 Normal 스타일에도 넣는다
    nppr = _style(doc, "Normal").element.get_or_add_pPr()
    for tag in ("w:autoSpaceDE", "w:autoSpaceDN"):
        el = OxmlElement(tag)
        el.set(qn("w:val"), "0")
        nppr.append(el)

    # 본문
    for name in ("Normal", "Body Text", "First Paragraph", "Compact", "Block Text", "Definition"):
        s = _style(doc, name)
        _style_font(s, F["body_en"], F["body_ko"], S["body"], color=C["text"])
        compact = name == "Compact"
        _para_spacing(
            s,
            before=0,
            after=1 if compact else SP["para_after"],
            line=SP["line"] if not compact else 1.2,
            indent=SP["first_line_indent"] if name in ("Body Text",) else 0,
            align=WD_ALIGN_PARAGRAPH.JUSTIFY if name in ("Body Text", "First Paragraph") else None,
        )

    # 제목
    for lvl, key in ((1, "h1"), (2, "h2"), (3, "h3")):
        s = _style(doc, f"Heading {lvl}")
        _style_font(s, F["heading_en"], F["heading_ko"], S[key], bold=True, color=C["accent"] if lvl < 3 else C["text"])
        _para_spacing(s, before=SP[f"{key}_before"], after=SP[f"{key}_after"], line=1.15, keep_next=True)

    # 제목(표지용)
    for name, size, bold, color in (
        ("Title", 24, True, C["accent"]),
        ("Subtitle", 13, False, C["muted"]),
        ("Author", S["body"], False, C["text"]),
        ("Date", S["body"], False, C["muted"]),
    ):
        s = _style(doc, name)
        _style_font(s, F["heading_en"], F["heading_ko"], size, bold=bold, color=color)
        _para_spacing(s, before=0, after=6, line=1.2, align=WD_ALIGN_PARAGRAPH.LEFT)

    # 캡션
    for name in ("Caption", "Image Caption", "Table Caption"):
        s = _style(doc, name)
        _style_font(s, F["heading_en"], F["heading_ko"], S["caption"],
                    bold=bool(st.get("frames", {}).get("caption_bold", False)), color=C["muted"])
        _para_spacing(s, before=3, after=10, line=1.2, align=WD_ALIGN_PARAGRAPH.CENTER)
    _para_spacing(_style(doc, "Table Caption"), before=8, after=4, keep_next=True)
    for name in ("Figure", "Captioned Figure"):
        _para_spacing(_style(doc, name), before=6, after=0, align=WD_ALIGN_PARAGRAPH.CENTER, keep_next=True)

    # 코드
    src = _get_or_add_style(doc, "Source Code")
    _style_font(src, F["mono"], F["heading_ko"], S["code"])
    _para_spacing(src, before=2, after=6, line=1.15, align=WD_ALIGN_PARAGRAPH.LEFT)
    ppr = src.element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F5F6F8")
    ppr.append(shd)
    vc = _style(doc, "Verbatim Char")
    _style_font(vc, F["mono"], F["heading_ko"], S["code"])

    # 표지(page 모드) 전용 스타일
    cov = _get_or_add_style(doc, "Cover Meta")
    _style_font(cov, F["heading_en"], F["heading_ko"], 11, color=C["text"])
    _para_spacing(cov, before=0, after=2, line=1.3, align=WD_ALIGN_PARAGRAPH.LEFT)
    kick = _get_or_add_style(doc, "Cover Kicker")
    _style_font(kick, F["heading_en"], F["heading_ko"], 10.5, bold=True, color=C["accent"])
    _para_spacing(kick, before=0, after=4, line=1.2)

    # 제목 블록(block 모드) 스타일: 가운데 제목 + 오른쪽 정렬 정보 줄
    dt_ = _get_or_add_style(doc, "Doc Title")
    _style_font(dt_, F["heading_en"], F["heading_ko"], S.get("title", 16), bold=True, color=C["text"])
    _para_spacing(dt_, before=0, after=10, line=1.2, align=WD_ALIGN_PARAGRAPH.CENTER)
    align = {"center": WD_ALIGN_PARAGRAPH.CENTER, "right": WD_ALIGN_PARAGRAPH.RIGHT,
             "left": WD_ALIGN_PARAGRAPH.LEFT}[st.get("title_block", {}).get("align", "center")]
    ds = _get_or_add_style(doc, "Doc Subtitle")
    _style_font(ds, F["heading_en"], F["heading_ko"], S.get("subtitle", 13), bold=False, color=C["text"])
    _para_spacing(ds, before=0, after=8, line=1.2, align=WD_ALIGN_PARAGRAPH.CENTER)
    dm = _get_or_add_style(doc, "Doc Meta")
    _style_font(dm, F["body_en"], F["body_ko"], S.get("meta", S["body"]), color=C["text"])
    _para_spacing(dm, before=0, after=0, line=1.35, align=align)
    dr = _get_or_add_style(doc, "Doc Rule")
    _para_spacing(dr, before=0, after=10, line=1.0)
    dr.font.size = Pt(4)
    _bottom_rule_style(dr, C["accent"] if st.get("title_block", {}).get("rule", True) else "FFFFFF")

    # 상태 표시([TODO], [확인 필요] 등) 형광펜 문자 스타일
    from docx.enum.style import WD_STYLE_TYPE

    try:
        mk = _style(doc, "Marker")
    except KeyError:
        mk = doc.styles.add_style("Marker", WD_STYLE_TYPE.CHARACTER)
    mrpr = mk.element.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), C.get("marker_fill", "FFF2A8"))
    mrpr.append(shd)
    mk.font.bold = True

    _style_table(doc, st)

    # 페이지
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Mm(210), Mm(297)
    m = st["page"]["margin_mm"]
    sec.top_margin, sec.bottom_margin = Mm(m["top"]), Mm(m["bottom"])
    sec.left_margin, sec.right_margin = Mm(m["left"]), Mm(m["right"])
    sec.header_distance, sec.footer_distance = Mm(10), Mm(10)
    cover_page = st.get("title_block", {}).get("mode", "block") == "page"
    sec.different_first_page_header_footer = cover_page  # 표지에는 머리말/꼬리말 없음

    # 머리말 (둘 다 비면 생략)
    left = _fill(st["header"]["left"], vars)
    right = _fill(st["header"]["right"], vars)
    if left or right:
        p = sec.header.paragraphs[0]
        p.text = ""
        usable = Mm(210 - m["left"] - m["right"])
        p.paragraph_format.tab_stops.add_tab_stop(usable, alignment=2)  # RIGHT
        r = p.add_run(f"{left}\t{right}")
        r.font.size = Pt(S["header_footer"])
        r.font.color.rgb = _rgb(C["muted"])
        _set_fonts(r._r, F["heading_en"], F["heading_ko"])
        _bottom_rule(p, "D0D5DD")

    # 꼬리말: 쪽 번호
    ftr = sec.footer
    fp = ftr.paragraphs[0]
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = _add_field(fp, "PAGE")
    run.font.size = Pt(S["header_footer"])
    run.font.color.rgb = _rgb(C["muted"])

    # 다단
    cols = int(st["page"].get("columns", 1))
    if cols > 1:
        sectpr = sec._sectPr
        c = sectpr.find(qn("w:cols"))
        if c is None:
            c = OxmlElement("w:cols")
            sectpr.append(c)
        c.set(qn("w:num"), str(cols))
        c.set(qn("w:space"), str(int(st["page"]["column_gap_mm"] * 56.7)))

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", default=str(TEMPLATES / "style.yaml"))
    ap.add_argument("--out", default=str(TEMPLATES / "reference.docx"))
    ap.add_argument("--var", action="append", default=[], help="key=value (머리말 변수)")
    a = ap.parse_args()
    v = dict(kv.split("=", 1) for kv in a.var)
    print(build_reference(Path(a.style), Path(a.out), v))
