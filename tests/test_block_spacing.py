"""Blank Enter boundaries using synthetic report content only."""
from pathlib import Path
import sys
import unittest
from lxml import etree
from docx import Document
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'snu-report-core/scripts'))
from block_spacing import space_blocks, gap_issues, plain_blank
from docx_post import clean_paragraphs, keep_related_content


def formula(doc, display=True):
    p = doc.add_paragraph('Voltage ' if not display else '')
    math = '<m:oMath><m:r><m:t>V=1</m:t></m:r></m:oMath>'
    xml = '<m:oMathPara ' + nsdecls('m') + '>' + math + '</m:oMathPara>' if display else (
        '<m:oMath ' + nsdecls('m') + '><m:r><m:t>V=1</m:t></m:r></m:oMath>')
    p._p.append(parse_xml(xml))
    return p


class BlockSpacingTests(unittest.TestCase):
    def test_equations_have_real_enters_without_changing_native_math(self):
        doc = Document()
        intro = doc.add_paragraph('The values follow.')
        first, second = formula(doc), formula(doc)
        table = doc.add_table(rows=2, cols=1)
        table.cell(0, 0).text = '1'
        table.cell(1, 0).text = 'Table.1 - synthetic'
        tail = doc.add_paragraph('Interpretation.')
        original = [etree.tostring(node) for node in doc.element.body.iter(qn('m:oMath'))]
        keep_related_content(doc)
        space_blocks(doc, {})
        self.assertTrue(plain_blank(first._p.getprevious()))
        self.assertTrue(plain_blank(first._p.getnext()))
        self.assertTrue(plain_blank(second._p.getnext()))
        self.assertTrue(plain_blank(tail._p.getprevious()))
        self.assertTrue(intro.paragraph_format.keep_with_next)
        self.assertFalse(first.paragraph_format.keep_with_next)
        self.assertFalse(second.paragraph_format.keep_with_next)
        self.assertEqual(original, [etree.tostring(node) for node in doc.element.body.iter(qn('m:oMath'))])
        self.assertFalse(gap_issues(doc))

    def test_code_block_and_title_information_are_not_split_inside(self):
        doc = Document()
        for name in ('Doc Meta', 'Source Code'):
            doc.styles.add_style(name, 1)
        meta1 = doc.add_paragraph('Student', style='Doc Meta')
        meta2 = doc.add_paragraph('Date', style='Doc Meta')
        intro = doc.add_paragraph('Run these commands.')
        line1 = doc.add_paragraph('.step param x list 1 2', style='Source Code')
        line2 = doc.add_paragraph('.tran 1m', style='Source Code')
        tail = doc.add_paragraph('Interpretation.')
        space_blocks(doc, {})
        self.assertIs(meta1._p.getnext(), meta2._p)
        self.assertTrue(plain_blank(intro._p.getprevious()))
        self.assertTrue(plain_blank(line1._p.getprevious()))
        self.assertIs(line1._p.getnext(), line2._p)
        self.assertTrue(plain_blank(tail._p.getprevious()))

    def test_cleanup_and_repeated_spacing_reuse_one_blank(self):
        doc = Document()
        doc.add_paragraph('Intro.')
        doc.add_paragraph()
        doc.add_paragraph()
        formula(doc)
        doc.add_paragraph('Interpretation.')
        for _ in range(3):
            clean_paragraphs(doc, {})
            space_blocks(doc, {})
        self.assertEqual(sum(plain_blank(p._p) for p in doc.paragraphs), 2)
        self.assertFalse(gap_issues(doc))
        blank = next(p._p for p in doc.paragraphs if plain_blank(p._p))
        blank.getparent().remove(blank)
        self.assertTrue(gap_issues(doc))

    def test_inline_and_table_cell_math_do_not_add_blank_lines(self):
        doc = Document()
        formula(doc, display=False)
        tail = doc.add_paragraph('Body text.')
        table = doc.add_table(rows=1, cols=1)
        table.cell(0, 0).paragraphs[0]._p.append(parse_xml(
            '<m:oMathPara ' + nsdecls('m') + '><m:oMath><m:r><m:t>x</m:t></m:r></m:oMath></m:oMathPara>'))
        space_blocks(doc, {})
        self.assertEqual(len(doc.paragraphs), 2)
        self.assertEqual(len(table.cell(0, 0).paragraphs), 1)

    def test_figure_to_equation_shares_gap_and_preserves_structural_paragraphs(self):
        doc = Document()
        table = doc.add_table(rows=2, cols=1)
        table.cell(0, 0).paragraphs[0]._p.append(OxmlElement('w:drawing'))
        equation = formula(doc)
        bookmark = doc.add_paragraph()
        bookmark._p.append(OxmlElement('w:bookmarkStart'))
        page = doc.add_paragraph()
        page.paragraph_format.page_break_before = True
        doc.add_paragraph('Later text.')
        space_blocks(doc, {})
        self.assertEqual(equation._p.getprevious().find('.//' + qn('w:pStyle')).get(qn('w:val')), 'FigureSpacer')
        self.assertIsNotNone(bookmark._p.find(qn('w:bookmarkStart')))
        self.assertTrue(page.paragraph_format.page_break_before)
        self.assertFalse(plain_blank(bookmark._p))
        self.assertFalse(plain_blank(page._p))

    def test_body_bookmarks_do_not_hide_title_or_final_figure_boundaries(self):
        doc = Document()
        doc.styles.add_style('Doc Meta', 1)
        meta = doc.add_paragraph('Student', style='Doc Meta')
        heading = doc.add_paragraph('Exercise', style='Heading 1')
        heading._p.addprevious(OxmlElement('w:bookmarkStart'))
        table = doc.add_table(rows=1, cols=1)
        table.cell(0, 0).paragraphs[0]._p.append(OxmlElement('w:drawing'))
        table._tbl.addnext(OxmlElement('w:bookmarkEnd'))
        space_blocks(doc, {})
        self.assertTrue(plain_blank(meta._p.getnext()))
        self.assertTrue(plain_blank(table._tbl.getnext()))
        self.assertEqual(len(doc.element.body.findall(qn('w:bookmarkStart'))), 1)
        self.assertEqual(len(doc.element.body.findall(qn('w:bookmarkEnd'))), 1)
        self.assertFalse(gap_issues(doc))


if __name__ == '__main__':
    unittest.main()
