"""Meaningful scope regressions for the HW-only prose and MATLAB comment checks."""
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'snu-report-core/scripts'))
from hw_style import prose_issues, comment_issues, comments

class HWStyleTests(unittest.TestCase):
    def test_prose_review_includes_headings_and_captions_but_preserves_math_and_paths(self):
        self.assertEqual(len(prose_issues('# Newton–Raphson\n값은 −0.25 V였다.\n![결과–비교](figs/a.png)')), 3)
        self.assertFalse(prose_issues(r'$x=−1$ and $$x−y=0$$'+'\n'+r'`a–b` [file](a–b.pdf) ![결과](figs/a–b.png)'))

    def test_matlab_strings_and_transposes_do_not_hide_actual_comments(self):
        source = "fprintf('%.3f%%', x); % residual\nA = B'; % transpose\ns = \"100%\"; % label\nt = 'it''s 50%'; % value"
        self.assertEqual([text for _, text in comments(source)], ['residual','transpose','label','value'])
        self.assertFalse(comment_issues(source))

    def test_workflow_context_is_flagged_without_banning_natural_english(self):
        self.assertTrue(comment_issues('% Plot the trajectories with their original blue and red colors.'))
        self.assertFalse(comment_issues('% fixed electrode\n% Keep the boundary values fixed.\n% original data before filtering'))
        self.assertFalse(comment_issues("text = 'as requested'; % text used as a label"))

    def test_block_comments_and_korean_comments_are_reviewed(self):
        self.assertEqual(len(comment_issues('%{\nas requested\n%}\nx = 1; % 초기값')), 2)
        self.assertFalse(comment_issues("s = '한글 문자열'; % label"))
