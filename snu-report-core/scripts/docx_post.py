#!/usr/bin/env python3
"""pandoc이 만든 docx 후처리 (build.py가 호출)

사용자 서식 규칙 (예시: Table.1 / Fig.1 양식)
1. 표: 표 자체의 맨 아래에 '캡션 행'(전체 열 병합)을 붙인다. 캡션은 보통 굵기, 가운데.
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
    # 생략하면 캡션 스타일의 keepNext=true를 상속해 다음 문항까지 묶일 수 있다.
    ppr.append(_el("w:keepNext", **{"w:val": "1" if keep_next else "0"}))
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
def autofit_table(tbl, max_tw: float, size: float, pad_pt=14.0) -> list[int]:
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


def tidy_cells(tbl, size, line=240, padding=100):
    """셀 여백을 확보한다. 짧은 표만 묶고 긴 표는 머리행을 반복한다."""
    rows = tbl.findall(qn("w:tr"))
    for index, tr in enumerate(rows):
        trpr = tr.find(qn("w:trPr"))
        if trpr is None:
            trpr = _el("w:trPr")
            tr.insert(0, trpr)
        _set_child(trpr, "w:cantSplit")
        if index == 0:
            _set_child(trpr, "w:tblHeader")
        for tc in tr.findall(qn("w:tc")):
            tcpr = tc.find(qn("w:tcPr"))
            if tcpr is None:
                tcpr = _el("w:tcPr")
                tc.insert(0, tcpr)
            _set_child(tcpr, "w:vAlign", **{"w:val": "center"})
            margins = _set_child(tcpr, "w:tcMar")
            for side in ("top", "bottom", "left", "right"):
                margins.append(_el(f"w:{side}", **{"w:w": padding, "w:type": "dxa"}))
            for p in tc.findall(qn("w:p")):
                para_center_tight(p, keep_next=(len(rows) <= 8 and index < len(rows)-1), line=line)
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
    # 마지막 데이터 행과 캡션만 반드시 붙인다. 긴 표 전체를 한 쪽에 묶지 않는다.
    for p in tbl.findall(qn("w:tr"))[-2].iter(qn("w:p")):
        _set_child(_ppr(p), "w:keepNext")


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
    """표끼리 합쳐지지 않도록 하는 최소 문단. 본문 앞에는 빈 줄을 넣지 않는다."""
    following = el.getnext()
    if following is not None and following.tag == qn("w:p"):
        return
    p = _el("w:p")
    ppr = _el("w:pPr")
    ppr.append(_el("w:spacing", **{"w:before": 0, "w:after": 0, "w:line": 20, "w:lineRule": "exact"}))
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
            tidy_cells(tbl, tsize, padding=st.get("table", {}).get("cell_padding_twips", 100))
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
            tidy_cells(el, tsize, padding=st.get("table", {}).get("cell_padding_twips", 100))
            autofit_table(el, usable_tw, tsize)
            n_tbl += 1
            i += 1
            continue
        if el.tag == qn("w:p") and p_style(el) in ("CaptionedFigure", "Figure") and el.find(".//" + qn("w:drawing")) is not None:
            cap = children[i + 1] if i + 1 < len(children) and p_style(children[i + 1]) == "ImageCaption" else None
            if st.get("frames", {}).get("figure_width", "fit") == "full":
                width = int(usable_tw)
            else:
                caption_width = text_pt(p_text(cap), st["size"]["caption"]) * TW_PER_PT + 200 if cap is not None else 0
                width = int(min(max(_image_width_tw(el) + 200, caption_width), usable_tw))
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


def math_size(doc, inline_pt: float, display_pt: float) -> int:
    """수식 글자 크기. Cambria Math는 같은 pt의 맑은 고딕보다 커 보여서 본문보다 조금 작게 둔다.
    m:r 안에 w:rPr(w:sz)를 넣는다 (OMML 순서: m:rPr → w:rPr → m:t)."""
    n = 0
    body = doc.element.body
    for om in body.iter(qn("m:oMath")):
        display = om.getparent() is not None and om.getparent().tag == qn("m:oMathPara")
        half = str(int(round((display_pt if display else inline_pt) * 2)))
        for r in om.iter(qn("m:r")):
            rpr = r.find(qn("w:rPr"))
            if rpr is None:
                rpr = OxmlElement("w:rPr")
                mrpr = r.find(qn("m:rPr"))
                (mrpr.addnext(rpr) if mrpr is not None else r.insert(0, rpr))
            for tag in ("w:sz", "w:szCs"):
                el = rpr.find(qn(tag))
                if el is None:
                    el = OxmlElement(tag)
                    rpr.append(el)
                el.set(qn("w:val"), half)
            _upright(r, rpr)
            n += 1
    return n


_UPRIGHT_TXT = re.compile(r"[A-Za-zΑ-Ωα-ωµμΩ]")
_CAP_GREEK = re.compile(r"^[ΓΔΘΛΞΠΣΦΨΩ]$")


def _upright(r, rpr):
    """세움꼴(m:sty p)인 글자 — 함수 이름, 단위 — 와 대문자 그리스(Δ)를 '일반 텍스트'(m:nor)로.
    Word는 m:sty p를 따르지만 LibreOffice(미리보기·PDF 변환)는 m:nor만 세운다. 글꼴은 Cambria Math로 맞춘다.
    (OMML 스키마에서 m:nor와 m:sty는 둘 중 하나라서 m:sty는 뺀다)"""
    t = "".join(x.text or "" for x in r.findall(qn("m:t")))
    mrpr = r.find(qn("m:rPr"))
    sty = mrpr.find(qn("m:sty")) if mrpr is not None else None
    plain = sty is not None and sty.get(qn("m:val")) == "p" and _UPRIGHT_TXT.search(t)
    if not (plain or _CAP_GREEK.match(t.strip())):
        return
    if mrpr is None:
        mrpr = OxmlElement("m:rPr")
        r.insert(0, mrpr)
    if sty is not None:
        mrpr.remove(sty)
    for sc in mrpr.findall(qn("m:scr")):
        mrpr.remove(sc)
    if mrpr.find(qn("m:nor")) is None:
        nor = OxmlElement("m:nor")
        lit = mrpr.find(qn("m:lit"))
        (lit.addnext(nor) if lit is not None else mrpr.insert(0, nor))
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for a in ("w:ascii", "w:hAnsi", "w:cs"):
        fonts.set(qn(a), "Cambria Math")


_TALL = ("m:f", "m:nary", "m:rad", "m:m", "m:eqArr", "m:limLow", "m:limUpp", "m:groupChr")


def flatten_parens(doc) -> int:
    """늘어나는 괄호(m:d) 중 안에 분수·근호 같은 큰 식이 없는 것을 보통 괄호 글자로 바꾼다.
    LibreOffice(미리보기·PDF 변환)는 m:d 괄호를 가늘게 그려 세로줄(|t|)처럼 보인다. Word에서도 모양은 같다."""
    n = 0
    body = doc.element.body
    for d in list(body.iter(qn("m:d"))):
        dpr = d.find(qn("m:dPr"))
        def chr_of(tag, default):
            el = dpr.find(qn(tag)) if dpr is not None else None
            return el.get(qn("m:val"), default) if el is not None else default
        beg, end = chr_of("m:begChr", "("), chr_of("m:endChr", ")")
        es = d.findall(qn("m:e"))
        if (beg, end) not in (("(", ")"), ("[", "]")) or len(es) != 1:
            continue
        if any(True for t in _TALL for _ in es[0].iter(qn(t))):
            continue
        parent = d.getparent()
        idx = list(parent).index(d)
        def paren(ch):
            r = OxmlElement("m:r")
            rpr = OxmlElement("m:rPr")
            sty = OxmlElement("m:sty")
            sty.set(qn("m:val"), "p")
            rpr.append(sty)
            r.append(rpr)
            t = OxmlElement("m:t")
            t.text = ch
            r.append(t)
            return r
        new = [paren(beg)] + list(es[0]) + [paren(end)]
        parent.remove(d)
        for k, el in enumerate(new):
            parent.insert(idx + k, el)
        n += 1
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
    # 사진의 비율을 유지하고 그림+캡션이 한 쪽을 넘지 않게 한다.
    section = doc.sections[0]
    frames = st.get("frames", {})
    max_w = min(int(section.page_width - section.left_margin - section.right_margin) - 120000,
                int(float(frames.get("max_width_mm", 140))*36000))
    max_h = min(int((section.page_height - section.top_margin - section.bottom_margin) *
                   float(frames.get("max_height_fraction", 0.55))),
                int(float(frames.get("max_height_mm", 95))*36000))
    res["images_resized"] = fit_images(doc, max_w, max_h,
                                       int(float(frames.get("portrait_max_height_mm", 80))*36000))
    if st.get("frames", {}).get("enabled", True):
        res["frames"] = frame_all(doc, st, usable_tw)
    if not st.get("spacing", {}).get("auto_space_latin", False):
        res["no_autospace"] = no_autospace(doc)
    if st.get("spacing", {}).get("leading_space", True):
        res["leading_space"] = leading_space(doc)
    res["parens"] = flatten_parens(doc)
    sz = st.get("size", {})
    res["math_runs"] = math_size(doc, float(sz.get("math", sz.get("body", 11) - 1)),
                                 float(sz.get("math_display", sz.get("body", 11))))
    res["bullets"] = dash_bullets(doc)
    res["table_alt_removed"] = modern_word(doc)
    res["paragraphs_cleaned"] = clean_paragraphs(doc, st)
    from math_layout import format_math
    res["math_layout"] = format_math(doc, st)
    res["figure_gaps"] = space_after_figures(doc, st)
    res["flow_groups"] = keep_related_content(doc)
    res["black_text"] = force_black_text(doc)
    from ooxml_order import normalize_document
    res["schema_order_fixed"] = normalize_document(doc)
    doc.save(docx_path)
    return res


def space_after_figures(doc, st: dict) -> int:
    """사진+캡션 뒤 본문을 12pt 띄운다. 빈 Enter를 추가하지 않는다."""
    gap = round(float(st.get("spacing", {}).get("figure_after", 12))*20)
    count = 0
    for element in list(doc.element.body):
        if element.find('.//' + qn('w:drawing')) is None:
            continue
        following = element.getnext()
        if following is not None and p_style(following) == 'ImageCaption':
            following = following.getnext()
        if following is None or following.tag != qn('w:p'):
            continue
        ppr = _ppr(following)
        spacing = ppr.find(qn('w:spacing'))
        if spacing is None:
            spacing = _set_child(ppr, 'w:spacing')
        if not p_text(following).strip() and following.find('.//' + qn('w:drawing')) is None:
            # 두 표 사이의 필수 구분 문단 하나만 간격 역할을 맡는다.
            spacing.set(qn('w:lineRule'), 'exact')
            spacing.set(qn('w:line'), str(gap))
        else:
            spacing.set(qn('w:before'), str(max(gap, int(spacing.get(qn('w:before'), 0)))))
            spacing.set(qn('w:beforeAutospacing'), '0')
            _set_child(ppr, 'w:contextualSpacing', **{'w:val':'0'})
        count += 1
    return count


def keep_related_content(doc) -> int:
    """도입 설명과 직후의 식/그림을 붙인다. 문항 전체를 한 덩어리로 묶지 않는다."""
    children = list(doc.element.body)
    count = 0
    for index, element in enumerate(children[:-1]):
        following = children[index + 1]
        if p_style(following) == "MissingFigure":
            if element.tag == qn("w:tbl"):
                rows = element.findall(qn("w:tr"))
                for caption in rows[-1].iter(qn("w:p")) if rows else ():
                    _set_child(_ppr(caption), "w:keepNext")
                    count += 1
            elif element.tag == qn("w:p") and p_text(element).strip():
                _set_child(_ppr(element), "w:keepNext")
                count += 1
            continue
        if element.tag != qn("w:p") or not p_text(element).strip():
            continue
        if p_style(element) in ("DocTitle", "DocSubtitle", "DocMeta"):
            continue
        display_math = following.find(qn("m:oMathPara")) is not None
        calculation_intro = (
            index + 2 < len(children)
            and following.tag == qn("w:p")
            and children[index+2].find(qn("m:oMathPara")) is not None
            and element.find(qn("m:oMathPara")) is None
            and len(p_text(element)) + len(p_text(following)) <= 300
        )
        figure_intro = (
            index + 2 < len(children)
            and following.tag == qn("w:p")
            and children[index+2].tag == qn("w:tbl")
            and children[index+2].find(".//" + qn("w:drawing")) is not None
            and len(p_text(element)) + len(p_text(following)) <= 300
        )
        # 짧은 도입만 그림과 묶는다. 긴 본문까지 묶으면 큰 빈칸이 생긴다.
        figure = following.tag == qn("w:tbl") and following.find(".//" + qn("w:drawing")) is not None
        if display_math or calculation_intro or figure_intro or (figure and len(p_text(element)) <= 240):
            _set_child(_ppr(element), "w:keepNext")
            count += 1
    return count


def fit_images(doc, max_width: int, max_height: int, portrait_height: int | None = None) -> int:
    """wp와 DrawingML의 치수를 같은 비율로 줄인다. 확대하지 않는다."""
    count = 0
    for inline in doc.element.body.iter(qn("wp:inline")):
        extent = inline.find(qn("wp:extent"))
        if extent is None:
            continue
        width, height = int(extent.get("cx")), int(extent.get("cy"))
        if width <= 0 or height <= 0:
            continue
        height_limit = min(max_height, portrait_height) if portrait_height and height / width >= 1.25 else max_height
        scale = min(1.0, max_width / width, height_limit / height)
        if scale < 1:
            for element in [extent, *inline.findall(".//" + qn("a:xfrm") + "/" + qn("a:ext"))]:
                element.set("cx", str(int(width * scale)))
                element.set("cy", str(int(height * scale)))
            count += 1
    return count


def force_black_text(doc) -> int:
    """링크/수식/직접 서식/테마/머리말/꼬리말까지 글자색을 명시적으로 검정으로 고정."""
    roots = [doc.element, doc.styles.element]
    for section in doc.sections:
        roots.extend(h._element for h in (section.header, section.first_page_header,
                     section.even_page_header, section.footer, section.first_page_footer, section.even_page_footer))
    count = 0
    for root in roots:
        for run in list(root.iter(qn("w:r"))) + list(root.iter(qn("m:r"))):
            rpr = run.find(qn("w:rPr"))
            if rpr is None:
                rpr = _el("w:rPr")
                mrpr = run.find(qn("m:rPr"))
                if mrpr is not None:
                    mrpr.addnext(rpr)
                else:
                    run.insert(0, rpr)
            _set_child(rpr, "w:color", **{"w:val": "000000"})
            count += 1
        for rpr in root.iter(qn("w:rPr")):
            _set_child(rpr, "w:color", **{"w:val": "000000"})
    return count


def clean_paragraphs(doc, st: dict) -> int:
    """빈 Enter와 본문의 강제 줄바꿈을 정리하고 문단 간격을 서식으로 지정."""
    body = doc.element.body
    count = 0
    text_styles = {None, "Normal", "BodyText", "FirstParagraph", "Compact"}
    for p in list(body.findall(qn("w:p"))):
        structural = any(p.find('.//' + qn(tag)) is not None for tag in
                         ("w:drawing", "m:oMath", "m:oMathPara", "w:sectPr", "w:pageBreakBefore", "w:bookmarkStart"))
        breaks = list(p.iter(qn("w:br")))
        page_break = any(b.get(qn("w:type")) in ("page", "column") for b in breaks)
        if not p_text(p).strip() and not structural and not page_break:
            # Word의 연속 표가 합쳐지는 것을 막는 한 개의 최소 문단은 유지한다.
            previous, following = p.getprevious(), p.getnext()
            if previous is not None and following is not None and previous.tag == following.tag == qn("w:tbl"):
                _set_child(_ppr(p), "w:spacing", **{"w:before": 0, "w:after": 0, "w:line": 20, "w:lineRule": "exact"})
            else:
                body.remove(p)
                count += 1
            continue
        if p_style(p) not in text_styles or structural:
            continue
        spacing = st.get("spacing", {})
        _set_child(_ppr(p), "w:spacing", **{"w:before": 0,
            "w:after": int(float(spacing.get("para_after", 6))*20),
            "w:line": int(float(spacing.get("line", 1.35))*240), "w:lineRule": "auto"})
        _set_child(_ppr(p), "w:widowControl")
        if spacing.get("body_hard_breaks", "space") == "space":
            for br in breaks:
                if br.get(qn("w:type"), "textWrapping") == "textWrapping":
                    space = _el("w:t", **{"xml:space": "preserve"})
                    space.text = " "
                    br.getparent().replace(br, space)
                    count += 1
    return count


# ───────────────────────── 실제 DOCX의 쪽 갈림 보정 ─────────────────────────
# Word는 keepNext/cantSplit으로 표·캡션을 같은 쪽에 두지만 LibreOffice는 무시한다.
# 검토하는 DOCX와 전달하는 DOCX가 같아야 하므로 원본에 쪽 나누기를 넣는다.
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
        previous = tbl.getprevious()
        if previous is not None and previous.find(".//" + qn("w:pageBreakBefore")) is not None:
            continue  # 같은 틀 앞에 페이지 나누기를 반복 삽입하지 않는다.
        p = _el("w:p")
        ppr = _el("w:pPr")
        ppr.append(_el("w:pageBreakBefore"))
        ppr.append(_el("w:spacing", **{"w:before": 0, "w:after": 0, "w:line": 20, "w:lineRule": "exact"}))
        p.append(ppr)
        tbl.addprevious(p)
        n += 1
    doc.save(docx_path)
    return n
