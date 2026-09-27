#!/usr/bin/env python3
"""pandoc이 만든 docx 후처리 (build.py가 호출)

사용자 서식 규칙 (예시: Table.1 / Fig.1 양식)
1. 표: 표 자체의 맨 아래에 '캡션 행'(전체 열 병합)을 붙인다. 캡션은 굵게, 가운데.
2. 그림: 1열 2행 표(테두리 있음) — 윗칸 그림, 아랫칸 캡션. 틀 전체 가운데.
3. 표 칸: 모든 칸 구분선, 글자 가운데 정렬, 줄 간격 1.0, 머리행 글자는 임의 줄바꿈 없이 열 너비를 맞춤
   (불가피하면 공백·괄호 앞에서 끊음).
4. 본문 문단 첫머리 공백 한 칸.
5. Word에서 표·그림과 캡션이 같은 쪽에 있도록 keepNext/cantSplit 설정 (Word가 처리).
"""
from __future__ import annotations

import copy
import re
import unicodedata

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

TW_PER_PT = 20
TW_PER_MM = 56.7
SAFETY = 1.15   # 글자 폭 추정 여유


# ───────────────────────── text width ─────────────────────────
def char_em(ch: str) -> float:
    if ch == " ":
        return 0.28
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 1.0
    if ch in "→←⊕·∙Ω±≈≤≥×−":
        return 0.9
    if ch.isupper():
        return 0.66
    if ch in "il.,:;|'!()[]":
        return 0.34
    if ch.isdigit():
        return 0.58
    return 0.56


def text_pt(text: str, size: float, bold=False) -> float:
    return sum(char_em(c) for c in text) * size * SAFETY * (1.06 if bold else 1.0)


def longest_word_pt(text: str, size: float) -> float:
    return max((text_pt(w, size) for w in re.split(r"\s+", text) if w), default=0)


def split_header(text: str) -> list[str]:
    """머리행 두 줄 나누기: '(' 앞 > 가운데에 가까운 공백."""
    if "(" in text and text.index("(") > 0:
        i = text.index("(")
        return [text[:i].rstrip(), text[i:]]
    spaces = [m.start() for m in re.finditer(" ", text)]
    if not spaces:
        return [text]
    i = min(spaces, key=lambda s: abs(s - len(text) / 2))
    return [text[:i], text[i + 1:]]


# ───────────────────────── xml helpers ─────────────────────────
def _el(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k), str(v))
    return e


def p_style(p) -> str | None:
    ppr = p.find(qn("w:pPr"))
    ps = ppr.find(qn("w:pStyle")) if ppr is not None else None
    return ps.get(qn("w:val")) if ps is not None else None


_TEXT_TAGS = (qn("w:t"), qn("m:t"))


def p_text(el) -> str:
    """문단·셀의 글자 (Word 수식 m:t 포함 — 열 너비 계산에 필요)."""
    return "".join(t.text or "" for t in el.iter() if t.tag in _TEXT_TAGS)


MATH_FACTOR = 1.4   # Word 수식(Cambria Math 기울임, 연산자 여백)은 같은 글자 수의 본문보다 넓다


def el_pt(el, size: float) -> float:
    """문단·셀의 추정 폭 (pt). 수식 글자는 MATH_FACTOR배로 센다."""
    tot = 0.0
    for t in el.iter():
        if t.tag in _TEXT_TAGS and t.text:
            w = sum(char_em(c) for c in t.text)
            tot += w * (MATH_FACTOR if t.tag == qn("m:t") else 1.0)
    return tot * size * SAFETY


def _ppr(p):
    ppr = p.find(qn("w:pPr"))
    if ppr is None:
        ppr = _el("w:pPr")
        p.insert(0, ppr)
    return ppr


def _set_child(parent, tag, **attrs):
    for old in parent.findall(qn(tag)):
        parent.remove(old)
    e = _el(tag, **attrs)
    parent.append(e)
    return e


def para_center_tight(p, keep_next=False, before=0, after=0, line=240):
    ppr = _ppr(p)
    for tag in ("w:keepNext", "w:spacing", "w:ind", "w:jc"):
        for old in ppr.findall(qn(tag)):
            ppr.remove(old)
    if keep_next:
        ppr.append(_el("w:keepNext"))
    ppr.append(_el("w:spacing", **{"w:before": before, "w:after": after, "w:line": line, "w:lineRule": "auto"}))
    ppr.append(_el("w:ind", **{"w:left": 0, "w:right": 0, "w:firstLine": 0}))
    ppr.append(_el("w:jc", **{"w:val": "center"}))


def _borders(tag, val="single", sz=4, color="000000"):
    b = _el(tag)
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        b.append(_el(f"w:{side}", **{"w:val": val, "w:sz": sz, "w:space": 0, "w:color": color}))
    return b


def _run_size(r, size_pt):
    rpr = r.find(qn("w:rPr"))
    if rpr is None:
        rpr = _el("w:rPr")
        r.insert(0, rpr)
    for old in rpr.findall(qn("w:sz")) + rpr.findall(qn("w:szCs")):
        rpr.remove(old)
    rpr.append(_el("w:sz", **{"w:val": int(size_pt * 2)}))
    rpr.append(_el("w:szCs", **{"w:val": int(size_pt * 2)}))


def _bold_runs(p):
    for r in p.iter(qn("w:r")):
        rpr = r.find(qn("w:rPr"))
        if rpr is None:
            rpr = _el("w:rPr")
            r.insert(0, rpr)
        if rpr.find(qn("w:b")) is None:
            rpr.insert(0, _el("w:b"))


# ───────────────────────── table autofit ─────────────────────────
def autofit_table(tbl, max_tw: float, size: float, pad_pt=10.0) -> list[int]:
    rows = tbl.findall(qn("w:tr"))
    grid = [tr.findall(qn("w:tc")) for tr in rows]
    ncol = max(len(r) for r in grid)
    htxt = [p_text(tc) for tc in grid[0]] + [""] * (ncol - len(grid[0]))
    body = grid[1:]
    nat_h = [el_pt(tc, size) for tc in grid[0]] + [0.0] * (ncol - len(grid[0]))
    nat_b = [max([el_pt(p, size) for r in body if i < len(r) for p in r[i].iter(qn("w:p"))] or [0])
             for i in range(ncol)]
    word_b = [max([longest_word_pt(p_text(r[i]), size) for r in body if i < len(r)] or [0]) for i in range(ncol)]
    split = [None] * ncol
    max_pt = max_tw / TW_PER_PT

    def need():
        return [max(nat_h[i], nat_b[i]) + pad_pt for i in range(ncol)]

    widths = need()
    if sum(widths) > max_pt:  # 머리행이 본문보다 넓은 열부터 두 줄로
        for i in sorted(range(ncol), key=lambda i: nat_h[i] - nat_b[i], reverse=True):
            if nat_h[i] <= nat_b[i]:
                break
            parts = split_header(htxt[i])
            if len(parts) == 2:
                split[i] = parts
                nat_h[i] = max(text_pt(x, size) for x in parts)
                widths = need()
                if sum(widths) <= max_pt:
                    break
    if sum(widths) > max_pt:  # 본문 줄바꿈 허용
        mins = [max(nat_h[i], word_b[i]) + pad_pt for i in range(ncol)]
        extra = max_pt - sum(mins)
        if extra >= 0:
            slack = [widths[i] - mins[i] for i in range(ncol)]
            tot = sum(slack) or 1
            widths = [mins[i] + extra * slack[i] / tot for i in range(ncol)]
        else:
            widths = [w * max_pt / sum(mins) for w in mins]
    tw = [int(w * TW_PER_PT) for w in widths]

    for i, parts in enumerate(split):  # 머리행 줄 나누기
        if not parts or i >= len(grid[0]):
            continue
        ps = grid[0][i].findall(qn("w:p"))
        runs = ps[0].findall(qn("w:r")) if ps else []
        if not runs:
            continue
        rpr = runs[0].find(qn("w:rPr"))
        for r in runs:
            ps[0].remove(r)
        for k, txt in enumerate(parts):
            r = _el("w:r")
            if rpr is not None:
                r.append(copy.deepcopy(rpr))
            if k:
                r.append(_el("w:br"))
            t = _el("w:t")
            t.text = txt
            t.set(qn("xml:space"), "preserve")
            r.append(t)
            ps[0].append(r)

    set_widths(tbl, tw)
    return tw


def set_widths(tbl, tw):
    tblpr = tbl.find(qn("w:tblPr"))
    for tag in ("w:tblW", "w:jc", "w:tblLayout", "w:tblInd"):
        for old in tblpr.findall(qn(tag)):
            tblpr.remove(old)
    tblpr.append(_el("w:tblW", **{"w:w": sum(tw), "w:type": "dxa"}))
    tblpr.append(_el("w:jc", **{"w:val": "center"}))
    tblpr.append(_el("w:tblLayout", **{"w:type": "fixed"}))
    g = tbl.find(qn("w:tblGrid"))
    if g is not None:
        tbl.remove(g)
    g = _el("w:tblGrid")
    for w in tw:
        g.append(_el("w:gridCol", **{"w:w": w}))
    tblpr.addnext(g)
    for tr in tbl.findall(qn("w:tr")):
        for i, tc in enumerate(tr.findall(qn("w:tc"))):
            tcpr = tc.find(qn("w:tcPr"))
            if tcpr is None:
                tcpr = _el("w:tcPr")
                tc.insert(0, tcpr)
            for old in tcpr.findall(qn("w:tcW")):
                tcpr.remove(old)
            tcpr.insert(0, _el("w:tcW", **{"w:w": tw[min(i, len(tw) - 1)], "w:type": "dxa"}))


def tidy_cells(tbl, size, line=240):
    """표 칸: 가운데 정렬, 여백 0, 줄 간격 1.0, 글자 크기 고정, 세로 가운데."""
    for tr in tbl.findall(qn("w:tr")):
        for tc in tr.findall(qn("w:tc")):
            tcpr = tc.find(qn("w:tcPr"))
            if tcpr is None:
                tcpr = _el("w:tcPr")
                tc.insert(0, tcpr)
            _set_child(tcpr, "w:vAlign", **{"w:val": "center"})
            for p in tc.findall(qn("w:p")):
                para_center_tight(p, keep_next=True, line=line)
                for r in p.iter(qn("w:r")):
                    _run_size(r, size)


def add_caption_row(tbl, cap_p, total_tw: int, bold=False):
    ncol = len(tbl.find(qn("w:tblGrid")).findall(qn("w:gridCol")))
    tr = _el("w:tr")
    trpr = _el("w:trPr")
    trpr.append(_el("w:cantSplit"))
    tr.append(trpr)
    tc = _el("w:tc")
    tcpr = _el("w:tcPr")
    tcpr.append(_el("w:tcW", **{"w:w": total_tw, "w:type": "dxa"}))
    if ncol > 1:
        tcpr.append(_el("w:gridSpan", **{"w:val": ncol}))
    tcpr.append(_el("w:vAlign", **{"w:val": "center"}))
    tc.append(tcpr)
    para_center_tight(cap_p, keep_next=False, before=20, after=20)
    if bold:
        _bold_runs(cap_p)
    tc.append(cap_p)
    tr.append(tc)
    tbl.append(tr)
    for row in tbl.findall(qn("w:tr"))[:-1]:
        rp = row.find(qn("w:trPr"))
        if rp is None:
            rp = _el("w:trPr")
            row.insert(0, rp)
        if rp.find(qn("w:cantSplit")) is None:
            rp.append(_el("w:cantSplit"))


def figure_frame(img_p, cap_p, width_tw: int, border="single", bold=False):
    t = _el("w:tbl")
    pr = _el("w:tblPr")
    pr.append(_el("w:tblW", **{"w:w": width_tw, "w:type": "dxa"}))
    pr.append(_el("w:jc", **{"w:val": "center"}))
    pr.append(_borders("w:tblBorders", "single" if border == "single" else "nil"))
    pr.append(_el("w:tblLayout", **{"w:type": "fixed"}))
    mar = _el("w:tblCellMar")
    for side, v in (("top", 60), ("left", 80), ("bottom", 60), ("right", 80)):
        mar.append(_el(f"w:{side}", **{"w:w": v, "w:type": "dxa"}))
    pr.append(mar)
    t.append(pr)
    g = _el("w:tblGrid")
    g.append(_el("w:gridCol", **{"w:w": width_tw}))
    t.append(g)
    for k, p in enumerate((img_p, cap_p)):
        if p is None:
            continue
        tr = _el("w:tr")
        trpr = _el("w:trPr")
        trpr.append(_el("w:cantSplit"))
        tr.append(trpr)
        tc = _el("w:tc")
        tcpr = _el("w:tcPr")
        tcpr.append(_el("w:tcW", **{"w:w": width_tw, "w:type": "dxa"}))
        tcpr.append(_el("w:vAlign", **{"w:val": "center"}))
        tc.append(tcpr)
        if k == 0:
            para_center_tight(p, keep_next=True, before=40, after=40)
        else:
            para_center_tight(p, keep_next=False, before=20, after=20)
            if bold:
                _bold_runs(p)
        tc.append(p)
        tr.append(tc)
        t.append(tr)
    return t


def _image_width_tw(p) -> int:
    ext = p.find(".//" + qn("wp:extent"))
    return int(int(ext.get("cx")) / 635) if ext is not None else 4000


def _spacer_after(el):
    """표·그림 틀 뒤 본문과의 간격용 빈 문단."""
    p = _el("w:p")
    ppr = _el("w:pPr")
    ppr.append(_el("w:spacing", **{"w:before": 0, "w:after": 0, "w:line": 160, "w:lineRule": "exact"}))
    p.append(ppr)
    el.addnext(p)


def frame_all(doc, st: dict, usable_tw: float):
    body = doc.element.body
    tsize = st.get("table", {}).get("font_size", st["size"]["table"])
    border = st.get("frames", {}).get("border", "single")
    cap_bold = bool(st.get("frames", {}).get("caption_bold", False))
    children = list(body)
    n_tbl = n_fig = 0
    i = 0
    while i < len(children):
        el = children[i]
        if el.tag == qn("w:p") and p_style(el) == "TableCaption" and i + 1 < len(children) and children[i + 1].tag == qn("w:tbl"):
            tbl = children[i + 1]
            tidy_cells(tbl, tsize)
            tw = autofit_table(tbl, usable_tw, tsize)
            cap_need = text_pt(p_text(el), st["size"]["caption"], bold=cap_bold) * TW_PER_PT + 400
            if cap_need > sum(tw):  # 캡션이 표보다 넓으면 열을 비례 확대
                scale = min(cap_need, usable_tw) / sum(tw)
                tw = [int(w * scale) for w in tw]
                set_widths(tbl, tw)
            add_caption_row(tbl, el, sum(tw), bold=cap_bold)
            _spacer_after(tbl)
            n_tbl += 1
            i += 2
            continue
        if el.tag == qn("w:tbl"):
            tidy_cells(el, tsize)
            autofit_table(el, usable_tw, tsize)
            n_tbl += 1
            i += 1
            continue
        if el.tag == qn("w:p") and p_style(el) in ("CaptionedFigure", "Figure") and el.find(".//" + qn("w:drawing")) is not None:
            cap = children[i + 1] if i + 1 < len(children) and p_style(children[i + 1]) == "ImageCaption" else None
            if st.get("frames", {}).get("figure_width", "full") == "full":
                width = int(usable_tw)
            else:
                width = int(min(_image_width_tw(el) + 400, usable_tw))
            prev = el.getprevious()
            frame = figure_frame(el, cap, width, border, bold=cap_bold)
            if prev is not None:
                prev.addnext(frame)
            else:
                body.insert(0, frame)
            _spacer_after(frame)
            n_fig += 1
            i += 2 if cap is not None else 1
            continue
        i += 1
    return n_tbl, n_fig


def dash_bullets(doc) -> int:
    """글머리 기호를 '-'로 (사용자 지정). 번호 목록(1. 2. 3.)은 그대로."""
    try:
        numbering = doc.part.numbering_part.element
    except Exception:  # noqa: BLE001
        return 0
    n = 0
    for lvl in numbering.iter(qn("w:lvl")):
        fmt = lvl.find(qn("w:numFmt"))
        if fmt is None or fmt.get(qn("w:val")) != "bullet":
            continue
        txt = lvl.find(qn("w:lvlText"))
        if txt is not None:
            txt.set(qn("w:val"), "-")
        rpr = lvl.find(qn("w:rPr"))
        if rpr is not None:
            for f in rpr.findall(qn("w:rFonts")):
                rpr.remove(f)
        n += 1
    # 목록 들여쓰기를 얕게: 단계마다 7 mm, 번호·기호 뒤 3.5 mm
    for lvl in numbering.iter(qn("w:lvl")):
        ilvl = int(lvl.get(qn("w:ilvl"), "0"))
        ppr = lvl.find(qn("w:pPr"))
        if ppr is None:
            ppr = _el("w:pPr")
            lvl.append(ppr)
        for old in ppr.findall(qn("w:ind")):
            ppr.remove(old)
        ppr.append(_el("w:ind", **{"w:left": 400 * (ilvl + 1), "w:hanging": 200 if ilvl else 300}))
    return n


_AFTER_AUTOSPACE = ("bidi", "adjustRightInd", "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents",
                    "suppressOverlap", "jc", "textDirection", "textAlignment", "textboxTightWrap", "outlineLvl",
                    "divId", "cnfStyle", "rPr", "sectPr", "pPrChange")


def no_autospace(doc) -> int:
    """모든 문단에 한글-영문·숫자 자동 간격 끄기 (Word·LibreOffice 모두 "7 조" → "7조")."""
    n = 0
    for p in doc.element.body.iter(qn("w:p")):
        ppr = p.find(qn("w:pPr"))
        if ppr is None:
            ppr = _el("w:pPr")
            p.insert(0, ppr)
        for tag in ("w:autoSpaceDE", "w:autoSpaceDN"):
            old = ppr.find(qn(tag))
            if old is not None:
                ppr.remove(old)
        anchor = next((c for c in ppr if c.tag.split("}")[1] in _AFTER_AUTOSPACE), None)
        for tag in ("w:autoSpaceDE", "w:autoSpaceDN"):
            el = _el(tag, **{"w:val": "0"})
            if anchor is not None:
                anchor.addprevious(el)
            else:
                ppr.append(el)
        n += 1
    return n


def leading_space(doc, styles=("BodyText", "FirstParagraph")):
    n = 0
    for p in doc.element.body.findall(qn("w:p")):
        if p_style(p) not in styles:
            continue
        ppr = p.find(qn("w:pPr"))
        if ppr is not None and ppr.find(qn("w:numPr")) is not None:  # 목록 항목은 제외
            continue
        txt = p_text(p)
        if not txt.strip() or txt.startswith(" "):
            continue
        first = next((c for c in p if c.tag in (qn("w:r"), qn("m:oMath"), qn("m:oMathPara"), qn("w:hyperlink"))), None)
        if first is None or first.tag == qn("m:oMathPara"):
            continue
        r = _el("w:r")
        t = _el("w:t")
        t.text = " "
        t.set(qn("xml:space"), "preserve")
        r.append(t)
        first.addprevious(r)
        n += 1
    return n


def modern_word(doc) -> int:
    """Word 호환 모드 해제.
    pandoc docx에는 compatibilityMode가 없어 Word가 '[호환 모드]'로 열고, 저장할 때
    '표의 대체 텍스트가 제거됩니다' 경고를 띄운다. 표 대체 텍스트(tblCaption)는 캡션 행과 중복이라 지우고,
    문서를 Word 2013 이후 형식(15)으로 표시한다."""
    n = 0
    for tag in ("w:tblCaption", "w:tblDescription"):
        for el in list(doc.element.body.iter(qn(tag))):
            el.getparent().remove(el)
            n += 1
    settings = doc.settings.element
    compat = settings.find(qn("w:compat"))
    if compat is None:
        compat = _el("w:compat")
        anchor = next((c for c in settings if c.tag in (qn("w:docVars"), qn("w:rsids"), qn("m:mathPr"),
                                                       qn("w:themeFontLang"), qn("w:clrSchemeMapping"))), None)
        if anchor is not None:
            anchor.addprevious(compat)
        else:
            settings.append(compat)
    for cs in compat.findall(qn("w:compatSetting")):
        if cs.get(qn("w:name")) == "compatibilityMode":
            compat.remove(cs)
    compat.append(_el("w:compatSetting", **{"w:name": "compatibilityMode",
                                            "w:uri": "http://schemas.microsoft.com/office/word", "w:val": "15"}))
    return n


def postprocess(docx_path, st: dict):
    from docx import Document

    doc = Document(docx_path)
    m = st["page"]["margin_mm"]
    usable_tw = (210 - m["left"] - m["right"]) * TW_PER_MM
    cols = int(st["page"].get("columns", 1))
    if cols > 1:
        usable_tw = (usable_tw - st["page"]["column_gap_mm"] * TW_PER_MM) / cols
    res = {}
    if st.get("frames", {}).get("enabled", True):
        res["frames"] = frame_all(doc, st, usable_tw)
    if not st.get("spacing", {}).get("auto_space_latin", False):
        res["no_autospace"] = no_autospace(doc)
    if st.get("spacing", {}).get("leading_space", True):
        res["leading_space"] = leading_space(doc)
    res["bullets"] = dash_bullets(doc)
    res["table_alt_removed"] = modern_word(doc)
    from ooxml_order import normalize_document
    res["schema_order_fixed"] = normalize_document(doc)
    doc.save(docx_path)
    return res


# ───────────────────────── 미리보기(PDF) 전용: 쪽 갈림 보정 ─────────────────────────
# Word는 keepNext/cantSplit으로 표·캡션을 같은 쪽에 두지만 LibreOffice는 무시한다.
# 제출용 docx는 건드리지 않고, 미리보기 PDF를 만들 때 사본에만 쪽 나누기를 넣는다.
def _caption_regex(st: dict):
    num = st["numbering"]
    head = num.get("caption_format", "{prefix}.{n} - {text}").split("{text}")[0]
    rx = ""
    for part in re.split(r"(\{prefix\}|\{n\})", head):
        if part == "{prefix}":
            rx += "(" + "|".join(map(re.escape, (num["figure_prefix"], num["table_prefix"]))) + ")"
        elif part == "{n}":
            rx += r"(\d+)"
        else:
            rx += r"\s*".join(re.escape(c) for c in part.replace(" ", ""))
        rx += r"\s*"
    return re.compile("^" + rx)


def split_captions(pdf_path, st: dict) -> list[tuple[str, int]]:
    try:
        import pymupdf
    except ImportError:
        return []
    rx = _caption_regex(st)
    top_pt = st["page"]["margin_mm"]["top"] * 72 / 25.4 - 6
    found = []
    for page in pymupdf.open(str(pdf_path)):
        blocks = [b for b in page.get_text("dict")["blocks"] if b["bbox"][1] >= top_pt]
        if not blocks:
            continue
        first = min(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
        if first["type"] != 0:
            continue
        txt = " ".join(sp["text"] for ln in first["lines"] for sp in ln["spans"]).strip()
        m = rx.match(txt)
        if m:
            found.append((m.group(1), int(m.group(2))))
    return found


def break_before_frames(docx_path, targets, st: dict) -> int:
    from docx import Document

    doc = Document(docx_path)
    rx = _caption_regex(st)
    n = 0
    for tbl in doc.element.body.findall(qn("w:tbl")):
        rows = tbl.findall(qn("w:tr"))
        m = rx.match(p_text(rows[-1]).strip()) if rows else None
        if not m or (m.group(1), int(m.group(2))) not in targets:
            continue
        p = _el("w:p")
        ppr = _el("w:pPr")
        ppr.append(_el("w:pageBreakBefore"))
        ppr.append(_el("w:spacing", **{"w:before": 0, "w:after": 0, "w:line": 20, "w:lineRule": "exact"}))
        p.append(ppr)
        tbl.addprevious(p)
        n += 1
    doc.save(docx_path)
    return n
