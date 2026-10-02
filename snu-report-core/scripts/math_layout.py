"""Editable OMML layout: allow vertical growth; flag horizontal overflow for rewriting.

Width estimates are conservative diagnostics, not a substitute for page rendering.
Never resize a formula to unreadable text or change its mathematical content.
"""
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


def put(parent, tag, **attrs):
    for old in parent.findall(qn(tag)):
        parent.remove(old)
    element = OxmlElement(tag)
    for key, value in attrs.items():
        element.set(qn(key), str(value))
    parent.append(element)
    return element


def ensure(parent, tag):
    element = parent.find(qn(tag))
    if element is None:
        element = OxmlElement(tag)
        parent.insert(0, element)
    return element


def is_display(paragraph):
    return paragraph.find(qn('m:oMathPara')) is not None or (
        paragraph.find(qn('m:oMath')) is not None
        and not ''.join(t.text or '' for t in paragraph.iter(qn('w:t'))).strip())


def group_script_arguments(root):
    """Keep multi-token scripts horizontal in Word and MathML-based previews.

    A transparent OMML box groups the original nodes without merging runs,
    changing their styling, or losing a unary minus in a signed exponent.
    """
    count = 0
    for tag in ('m:sub', 'm:sup', 'm:deg'):
        for argument in list(root.iter(qn(tag))):
            children = [c for c in argument if c.tag != qn('m:argPr')]
            if len(children) <= 1:
                continue
            box = OxmlElement('m:box')
            content = OxmlElement('m:e')
            box.append(content)
            argument.insert(argument.index(children[0]), box)
            for child in children:
                content.append(child)
            count += 1
    return count


def format_math(doc, style):
    """Center display equations; retain inline flow and native fractions/subscripts."""
    spacing = style.get('spacing', {})
    settings = ensure(doc.settings.element, 'm:mathPr')
    put(settings, 'm:mathFont', **{'m:val':'Cambria Math'})
    put(settings, 'm:defJc', **{'m:val':'center'})
    group_script_arguments(doc.element.body)
    count = 0
    for paragraph in doc.element.body.iter(qn('w:p')):
        if paragraph.find('.//' + qn('m:oMath')) is None:
            continue
        ppr = ensure(paragraph, 'w:pPr')
        # Exact line height or a document grid can clip fractions and tall operators.
        put(ppr, 'w:snapToGrid', **{'w:val':0})
        line = ppr.find(qn('w:spacing'))
        if is_display(paragraph):
            put(ppr, 'w:jc', **{'w:val':'center'})
            put(ppr, 'w:ind', **{'w:left':0, 'w:right':0, 'w:firstLine':0})
            put(ppr, 'w:keepLines')
            put(ppr, 'w:contextualSpacing', **{'w:val':0})
            put(ppr, 'w:spacing', **{'w:before':round(spacing.get('math_before', 8)*20),
                'w:after':round(spacing.get('math_after', 8)*20),
                'w:line':round(spacing.get('math_line', 1.25)*240), 'w:lineRule':'auto'})
            for mathpara in paragraph.findall(qn('m:oMathPara')):
                put(ensure(mathpara, 'm:oMathParaPr'), 'm:jc', **{'m:val':'center'})
        elif line is None or line.get(qn('w:lineRule')) != 'auto':
            if line is None:
                line = ensure(ppr, 'w:spacing')
            line.set(qn('w:lineRule'), 'auto')
            line.set(qn('w:line'), str(round(spacing.get('line', 1.35)*240)))
        for run in paragraph.iter(qn('m:r')):
            rpr = ensure(run, 'w:rPr')
            put(rpr, 'w:rFonts', **{'w:ascii':'Cambria Math', 'w:hAnsi':'Cambria Math',
                                      'w:cs':'Cambria Math', 'w:eastAsia':'Cambria Math'})
            # Character compression and baseline offsets must not leak from body styles.
            put(rpr, 'w:spacing', **{'w:val':0})
            put(rpr, 'w:position', **{'w:val':0})
            put(rpr, 'w:w', **{'w:val':100})
            for old in rpr.findall(qn('w:fitText')):
                rpr.remove(old)
        for row in paragraph.iterancestors(qn('w:tr')):
            for height in row.findall('./' + qn('w:trPr') + '/' + qn('w:trHeight')):
                if height.get(qn('w:hRule')) == 'exact':
                    height.set(qn('w:hRule'), 'atLeast')
        count += 1
    return count


def width_pt(node, size=11):
    """Estimate the widest line of an OMML tree, respecting stacked structures."""
    from docx_post import text_pt
    tag = node.tag.rsplit('}', 1)[-1]
    if tag.endswith('Pr'):
        return 0
    if tag == 't':
        return text_pt(node.text or '', size)
    children = list(node)
    def part(name, scale=1):
        child = node.find(qn('m:' + name))
        return width_pt(child, size*scale) if child is not None else 0
    if tag == 'f':
        return max(part('num'), part('den')) + size*.6
    if tag in ('sSub', 'sSup', 'sSubSup'):
        return part('e') + max(part('sub', .72), part('sup', .72))
    if tag in ('limLow', 'limUpp'):
        return max(part('e'), part('lim', .72))
    if tag == 'rad':
        return part('e') + size + part('deg', .6)
    if tag == 'd':
        return sum(width_pt(c, size) for c in children) + size
    if tag == 'nary':
        return part('e') + max(size*1.2, part('sub', .72), part('sup', .72))
    if tag == 'eqArr':
        return max((width_pt(c, size) for c in children), default=0)
    if tag == 'm':
        rows = [[width_pt(c, size) for c in row.findall(qn('m:e'))]
                for row in node.findall(qn('m:mr'))]
        cols = max(map(len, rows), default=0)
        return sum(max((row[i] if i < len(row) else 0 for row in rows), default=0)
                   for i in range(cols)) + max(0, cols-1)*size
    return sum(width_pt(c, size) for c in children)


def available_width_pt(doc, paragraph):
    section_widths = []
    for section in doc.sections:
        width = (section.page_width-section.left_margin-section.right_margin)/12700
        cols = section._sectPr.find(qn('w:cols'))
        if cols is not None:
            explicit = [int(c.get(qn('w:w')))/20 for c in cols.findall(qn('w:col')) if c.get(qn('w:w'))]
            count = int(cols.get(qn('w:num'), 1))
            width = min(explicit) if explicit else (width-(count-1)*int(cols.get(qn('w:space'), 720))/20)/count
        section_widths.append(width)
    width = min(section_widths)
    cell = next(paragraph.iterancestors(qn('w:tc')), None)
    if cell is not None:
        tcpr = cell.find(qn('w:tcPr'))
        if tcpr is not None:
            cw = tcpr.find(qn('w:tcW'))
            if cw is not None and cw.get(qn('w:type')) == 'dxa':
                width = min(width, int(cw.get(qn('w:w')))/20)
            for side in ('left', 'right'):
                margin = tcpr.find('./' + qn('w:tcMar') + '/' + qn('w:' + side))
                width -= int(margin.get(qn('w:w'), 100))/20 if margin is not None else 5
    return width


def layout_issues(doc):
    issues = []
    for tag in ('m:sub', 'm:sup', 'm:deg'):
        for argument in doc.element.body.iter(qn(tag)):
            if len([c for c in argument if c.tag != qn('m:argPr')]) > 1:
                issues.append('여러 조각의 첨자/지수가 묶이지 않음 — 미리보기 세로 쌓임·부호 누락 위험')
    for paragraph in doc.element.body.iter(qn('w:p')):
        maths = list(paragraph.iter(qn('m:oMath')))
        if not maths:
            continue
        ppr = paragraph.find(qn('w:pPr'))
        spacing = ppr.find(qn('w:spacing')) if ppr is not None else None
        if spacing is None or spacing.get(qn('w:lineRule')) != 'auto':
            issues.append('수식 문단의 자동 줄 높이가 지정되지 않음 — 수식 잘림 위험')
        if is_display(paragraph):
            align = ppr.find(qn('w:jc')) if ppr is not None else None
            if align is None or align.get(qn('w:val')) != 'center':
                issues.append('독립 수식이 가운데 정렬되지 않음')
            for mp in paragraph.findall(qn('m:oMathPara')):
                jc = mp.find('./' + qn('m:oMathParaPr') + '/' + qn('m:jc'))
                if jc is None or jc.get(qn('m:val')) != 'center':
                    issues.append('OMML 독립 수식 정렬이 center가 아님')
        for row in paragraph.iterancestors(qn('w:tr')):
            if any(h.get(qn('w:hRule')) == 'exact' for h in row.iter(qn('w:trHeight'))):
                issues.append('수식이 고정 높이 표 행에 있음 — 분수·첨자 잘림 위험')
        widths = []
        for math in maths:
            sizes = [int(s.get(qn('w:val')))/2 for s in math.iter(qn('w:sz'))]
            widths.append(width_pt(math, max(sizes, default=11)))
        width = sum(widths) if is_display(paragraph) else max(widths)
        if width > available_width_pt(doc, paragraph)*.94:
            issues.append('수식 폭이 사용 공간에 비해 큼 — 일반식/대입/결과를 여러 독립 수식으로 나누고 재검토')
    return sorted(set(issues))
