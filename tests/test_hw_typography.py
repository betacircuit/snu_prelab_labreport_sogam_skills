"""Synthetic regressions for HW typography; actual report pages are reviewed separately."""
from pathlib import Path
import re
import sys
import tempfile
import unittest
from PIL import Image
from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
import yaml
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'snu-report-core/scripts'))
from build import preprocess
from screenshot_layout import normalize_screenshots, homework_sections
from docx_post import math_size
from math_layout import format_math
from ooxml_order import normalize_document


class HomeworkTypographyTests(unittest.TestCase):
    def setUp(self):
        self.style = yaml.safe_load((ROOT/'snu-report-core/templates/style.yaml').read_text(encoding='utf-8'))

    def test_crop_width_and_zoom_preserve_physical_line_pitch_and_pixels(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            widths, pitches = [300, 600, 900], [20, 20, 30]
            raw = []
            original = []
            for n, (width, pitch) in enumerate(zip(widths, pitches)):
                path = folder/f'{n}.png'
                Image.new('RGB', (width, 180), 'blue').save(path)
                original.append(path.read_bytes())
                raw.append(f'![Code]({n}.png){{#fig:c{n} width=100% line-px={pitch}}}')
            result = normalize_screenshots('\n'.join(raw), folder, folder, self.style)
            physical = [float(x) for x in re.findall(r'width=([0-9.]+)pt', result)]
            for n, (pt, px, pitch) in enumerate(zip(physical, widths, pitches)):
                self.assertAlmostEqual(pt/px*pitch, 10.5, places=3)
                self.assertEqual((folder/f'{n}.png').read_bytes(), original[n])
            self.assertNotIn('line-px', result)
            graph = '![Plot](0.png){width=100%}'
            self.assertEqual(normalize_screenshots(graph, folder, folder, self.style), graph)

    def test_long_screenshot_requires_split_instead_of_individual_shrink(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            Image.new('RGB', (600, 1800), 'white').save(folder/'long.png')
            with self.assertRaisesRegex(ValueError, 'split'):
                normalize_screenshots('![Code](long.png){line-px=24}', folder, folder, self.style)

    def test_numbered_plain_and_legacy_headings_keep_photo_validation_active(self):
        for heading in ['Problem 1) Plot', '1. Plot', 'Plot']:
            raw = '# '+heading+'\n\n![Code](figs/p1_code.png)\n\n# 2. Roots\n\n![Result](figs/p2_result.png)'
            sections = list(homework_sections(raw))
            self.assertEqual([n for n, _ in sections], ['1', '2'])
            self.assertIn('p1_code', sections[0][1])
            self.assertNotIn('p2_result', sections[0][1])
            formatted, warnings = preprocess(raw, self.style)
            self.assertFalse(warnings)
            self.assertTrue(formatted.startswith('# 1. Plot'))
            self.assertNotIn('Problem', formatted)

    def test_native_operator_spacing_retains_upright_functions_and_units(self):
        raw = r'$$f(x)=sin(x)+2\ V$$'
        formatted, _ = preprocess(raw, self.style)
        self.assertNotIn(r'\text{ }', formatted)
        self.assertIn(r'\sin', formatted)
        self.assertIn(r'\mathrm{V}', formatted)

    def test_fraction_and_signed_script_use_same_base_size_without_losing_content(self):
        doc = Document()
        p = doc.add_paragraph()
        p._p.append(parse_xml('<m:oMathPara '+nsdecls('m','w')+'><m:oMath>'
            '<m:f><m:num><m:r><m:t>1</m:t></m:r></m:num><m:den><m:r><m:t>x</m:t></m:r></m:den></m:f>'
            '<m:sSup><m:e><m:r><m:t>10</m:t></m:r></m:e><m:sup><m:r><m:t>−</m:t></m:r><m:r><m:t>5</m:t></m:r></m:sup></m:sSup>'
            '</m:oMath></m:oMathPara>'))
        before = [t.text for t in p._p.iter(qn('m:t'))]
        math_size(doc, 11, 11)
        format_math(doc, self.style)
        normalize_document(doc)
        self.assertEqual(before, [t.text for t in p._p.iter(qn('m:t'))])
        for control in p._p.iter(qn('m:ctrlPr')):
            self.assertEqual(control.find('.//'+qn('w:sz')).get(qn('w:val')), '22')
        self.assertEqual(p._p.find('./'+qn('w:pPr')+'/'+qn('w:rPr')+'/'+qn('w:sz')).get(qn('w:val')), '22')
        self.assertIsNotNone(p._p.find('.//'+qn('m:f')))
        self.assertIsNotNone(p._p.find('.//'+qn('m:sup')+'/'+qn('m:box')))
