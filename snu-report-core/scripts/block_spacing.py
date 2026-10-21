"""Real, editable blank paragraphs at report block boundaries."""
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

SPACER_IDS = {'FigureSpacer', 'BlockSpacer'}
TITLE_IDS = {'DocTitle', 'DocSubtitle', 'DocMeta'}
CODE_IDS = {'SourceCode', 'CodeBlock', 'Verbatim'}


def style_id(element):
    prop = element.find('./' + qn('w:pPr') + '/' + qn('w:pStyle'))
    return prop.get(qn('w:val')) if prop is not None else None


def plain_blank(element):
    """Do not consume fields, bookmarks, page/section breaks or drawing anchors."""
    if element.tag != qn('w:p'):
        return False
    return all(node.tag in {qn(t) for t in ('w:p', 'w:pPr', 'w:r', 'w:rPr', 'w:t')}
               or any(parent.tag in {qn('w:pPr'), qn('w:rPr')} for parent in node.iterancestors())
               for node in element.iter()) and not ''.join(element.itertext()).strip() and not any(
        element.find('.//' + qn(tag)) is not None
        for tag in ('w:sectPr', 'w:pageBreakBefore'))


def kind(element):
    if element.find('.//' + qn('w:drawing')) is not None:
        return 'figure'
    if element.tag == qn('w:tbl'):
        return 'table'
    sid = style_id(element)
    if sid in TITLE_IDS:
        return 'title'
    if sid in CODE_IDS:
        return 'code'
    if sid == 'ImageCaption':
        return 'figure_caption'
    if sid == 'TableCaption':
        return 'table_caption'
    if element.tag == qn('w:p'):
        from math_layout import is_display
        if is_display(element):
            return 'math'
    return 'body'


def boundary(left, right):
    """One gap per boundary; consecutive code lines and title lines stay intact."""
    a, b = kind(left), kind(right)
    if a == 'figure' and b == 'figure_caption':
        return None
    if a == 'table_caption' and b == 'table':
        return None
    if a == b and a in {'code', 'title'}:
        return None
    if a in {'figure', 'figure_caption'}:
        return 'Figure Spacer'
    if a in {'table', 'title', 'math', 'code'} or b in {'math', 'code'}:
        return 'Block Spacer'
    return None


def boundaries(doc):
    """Visit body-level boundaries only, preserving structural elements as barriers."""
    previous, blanks, markers = None, [], []
    for element in doc.element.body:
        if element.tag in {qn('w:bookmarkStart'), qn('w:bookmarkEnd')}:
            markers.append(element)
            continue
        if plain_blank(element):
            blanks.append(element)
            continue
        if element.tag not in {qn('w:p'), qn('w:tbl')} or (
            element.tag == qn('w:p') and any(element.find('.//' + qn(tag)) is not None
                for tag in ('w:sectPr', 'w:pageBreakBefore', 'w:br', 'w:fldChar', 'w:fldSimple'))
            and not ''.join(element.itertext()).strip()
        ):
            # Pandoc can close a section bookmark after its final figure.
            if previous is not None and kind(previous) in {'figure', 'figure_caption'} and markers:
                yield previous, element, blanks, 'Figure Spacer'
            previous, blanks, markers = None, [], []
            continue
        if previous is not None:
            yield previous, element, blanks, boundary(previous, element)
        previous, blanks, markers = element, [], []


def put(parent, tag, **attrs):
    for old in parent.findall(qn(tag)):
        parent.remove(old)
    child = OxmlElement(tag)
    for key, value in attrs.items():
        child.set(qn(key), str(value))
    parent.append(child)
    return child


def space_blocks(doc, config, figures_only=False):
    """Insert exactly one Enter; running cleanup and this pass again is idempotent."""
    spacing = config.get('spacing', {})
    for name, key in [('Figure Spacer', 'figure_after'), ('Block Spacer', 'block_gap')]:
        if name not in doc.styles:
            doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        style = doc.styles[name]
        style.font.size = Pt(float(spacing.get(key, 12)))
        fmt = style.paragraph_format
        fmt.space_before = fmt.space_after = Pt(0)
        fmt.line_spacing = 1.0
        fmt.keep_with_next = True
        fmt.keep_together = True
    count = 0
    for left, right, blanks, name in list(boundaries(doc)):
        if not name or (figures_only and name != 'Figure Spacer'):
            continue
        spacer = blanks[0] if blanks else OxmlElement('w:p')
        if not blanks:
            left.addnext(spacer)
        for extra in blanks[1:]:
            extra.getparent().remove(extra)
        ppr = spacer.get_or_add_pPr()
        put(ppr, 'w:pStyle', **{'w:val': doc.styles[name].style_id})
        put(ppr, 'w:spacing', **{'w:before': 0, 'w:after': 0,
                                'w:line': 240, 'w:lineRule': 'auto'})
        put(ppr, 'w:keepNext')
        put(ppr, 'w:keepLines')
        mark = ppr.find(qn('w:rPr'))
        if mark is None:
            mark = OxmlElement('w:rPr')
            ppr.append(mark)
        size = round(doc.styles[name].font.size.pt * 2)
        put(mark, 'w:sz', **{'w:val': size})
        put(mark, 'w:szCs', **{'w:val': size})
        # Separate equations are independent blocks, not one long keepNext chain.
        if kind(left) == 'math':
            put(left.get_or_add_pPr(), 'w:keepNext', **{'w:val': 0})
        count += 1
    return count


def gap_issues(doc):
    errors = []
    for left, right, blanks, required in boundaries(doc):
        if required and len(blanks) != 1:
            errors.append('수식·코드·표·그림·제목 정보 사이 실제 빈 문단(Enter)이 정확히 한 줄이 아님')
    return sorted(set(errors))
