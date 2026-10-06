"""Block symbols, sequential simulation, notation/term checks, bode helpers and textbook question extraction."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

import schemdraw.elements as elm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'snu-report-core/scripts'))
from circuit_kit import Circuit, CircuitError
from proof import check_text, load_terms
import bode
from ingest import report_sections, requirements_yaml

MUX4 = {"Y": "(~S1 & ~S0 & D0) | (~S1 & S0 & D1) | (S1 & ~S0 & D2) | (S1 & S0 & D3)"}


def mux4(swap=False):
    c = Circuit()
    m = c.block("MUX4", at=(6, 0), name="U1")
    for i in range(4):
        p = c.pin_of(m, f"I{i}")
        c.add(elm.Line().at((2, p[1])).to(p))
        c.pin((2, p[1]), f"D{i}")
    for name, pin, y in (("S1", "S0" if swap else "S1", -3.4), ("S0", "S1" if swap else "S0", -4.0)):
        p = c.pin_of(m, pin)
        c.add(elm.Line().at(p).to((p[0], y)))
        c.add(elm.Line().at((p[0], y)).to((2, y)))
        c.pin((2, y), name)
    y = c.pin_of(m, "Y")
    c.add(elm.Line().at(y).right(0.8))
    c.pin((y[0] + 0.8, y[1]), "Y", side="out")
    return c


def wire(c, *pts):
    for a, b in zip(pts, pts[1:]):
        c.add(elm.Line().at(a).to(b))


def counter(four_way=False):
    """2-bit 동기 카운터: D0 = ~Q0, D1 = Q1 ^ Q0"""
    c = Circuit()
    f0 = c.block("DFF", at=(8, 0), name="FF0")
    f1 = c.block("DFF", at=(8, -4.5), name="FF1")
    P0, P1 = (lambda p: c.pin_of(f0, p)), (lambda p: c.pin_of(f1, p))
    c.pin((0, P0("CLK")[1]), "CLK")
    wire(c, (0, P0("CLK")[1]), P0("CLK"))
    c.node((1.0, P0("CLK")[1]))
    wire(c, (1.0, P0("CLK")[1]), (1.0, P1("CLK")[1]), P1("CLK"))
    q0, q1, d0, d1 = P0("Q"), P1("Q"), P0("D"), P1("D")
    top = q0[1] + 1.6
    up, down = q0[0] + 0.6, q0[0] + (0.6 if four_way else 1.0)
    wire(c, q0, (q0[0] + 1.6, q0[1]))
    c.pin((q0[0] + 1.6, q0[1]), "Q0", side="out")
    c.node((up, q0[1]))
    if down != up:
        c.node((down, q0[1]))
    wire(c, (up, q0[1]), (up, top + 0.6), (2.2, top + 0.6), (2.2, top))
    n = c.gate("NOT", out_at=(4.0, top), name="N1")
    wire(c, (2.2, top), n.start)
    wire(c, n.end, (4.6, top), (4.6, d0[1]), d0)
    x = c.gate("XOR", out_at=(4.9, d1[1]), name="X1")
    wire(c, x.out, d1)
    wire(c, (down, q0[1]), (down, q0[1] - 2.0), (2.6, q0[1] - 2.0), (2.6, x.in1[1]), x.in1)
    wire(c, q1, (q1[0] + 1.6, q1[1]))
    c.pin((q1[0] + 1.6, q1[1]), "Q1", side="out")
    c.node((q1[0] + 0.6, q1[1]))
    yb = P1("Qn")[1] - 1.0
    wire(c, (q1[0] + 0.6, q1[1]), (q1[0] + 0.6, yb), (2.2, yb), (2.2, x.in2[1]), x.in2)
    return c


class BlockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.dir = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_mux_draws_and_verifies(self):
        c = mux4()
        with contextlib.redirect_stdout(io.StringIO()):
            c.save(self.dir / "mux.png")
            self.assertTrue(c.verify(MUX4, kinds={"U1": "MUX4"}))

    def test_swapped_select_lines_fail_verification(self):
        with self.assertRaisesRegex(CircuitError, "진리표 불일치"):
            mux4(swap=True).verify(MUX4, quiet=True)

    def test_sync_counter_sequence_state_table_and_timing(self):
        c = counter()
        with contextlib.redirect_stdout(io.StringIO()):
            c.save(self.dir / "cnt.png")
            trace = c.verify_seq([{}] * 4, {"Q0": [1, 0, 1, 0], "Q1": [0, 1, 1, 0]}, kinds={"FF0": "DFF", "X1": "XOR"})
            c.timing(trace, ["CLK", "Q0", "Q1"], self.dir / "t.png")
        self.assertTrue((self.dir / "t.png").exists())
        table = c.state_table([])
        self.assertIn("| 00 | 10 |", table)
        self.assertIn("| 11 | 00 |", table)
        with self.assertRaisesRegex(CircuitError, "verify_seq"):
            c.verify({"Q0": "CLK"}, quiet=True)
        with self.assertRaisesRegex(CircuitError, "순차 회로 검증 실패"):
            c.verify_seq([{}] * 2, {"Q0": [0, 0]}, quiet=True)

    def test_four_wires_at_one_dot_are_rejected(self):
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(CircuitError, "네 갈래"):
            counter(four_way=True).save(self.dir / "bad.png")

    def test_ripple_counter_clocks_from_previous_stage(self):
        """T flip-flop 두 개: FF1의 CLK = FF0의 Q̄ (상승 에지) → 위로 세는 ripple counter"""
        c = Circuit()
        f0 = c.block("TFF", at=(6, 0), name="FF0")
        f1 = c.block("TFF", at=(13, 0), name="FF1")
        P0, P1 = (lambda p: c.pin_of(f0, p)), (lambda p: c.pin_of(f1, p))
        c.pin((0, P0("T")[1]), "T")
        wire(c, (0, P0("T")[1]), P0("T"))
        c.node((1, P0("T")[1]))
        wire(c, (1, P0("T")[1]), (1, 2.5), (8.5, 2.5), (8.5, P1("T")[1]), P1("T"))
        c.pin((0, P0("CLK")[1]), "CLK")
        wire(c, (0, P0("CLK")[1]), P0("CLK"))
        wire(c, P0("Qn"), (7.5, P0("Qn")[1]), (7.5, P1("CLK")[1] - 0.0), P1("CLK"))
        wire(c, P0("Q"), (6.8, P0("Q")[1]))
        c.pin((6.8, P0("Q")[1]), "Q0", side="out")
        wire(c, P1("Q"), (13.8, P1("Q")[1]))
        c.pin((13.8, P1("Q")[1]), "Q1", side="out")
        with contextlib.redirect_stdout(io.StringIO()):
            c.verify_seq([{"T": 1}] * 5, {"Q0": [1, 0, 1, 0, 1], "Q1": [0, 1, 1, 0, 0]})

    def test_gate_drawn_before_its_driver_still_connects(self):
        """출력 쪽 게이트를 먼저 그려도 중간 넷 이름이 같아야 한다 (예전에는 'Y가 그림에 없음')"""
        c = Circuit()
        g2 = c.gate("NOT", out_at=(5, 0), name="N2")
        g1 = c.gate("AND", out_at=(3, 0), name="A1")
        wire(c, g1.out, g2.start)
        for pin, nm in ((g1.in1, "A"), (g1.in2, "B")):
            wire(c, (1, pin[1]), pin)
            c.pin((1, pin[1]), nm)
        wire(c, g2.end, (g2.end[0] + 0.6, g2.end[1]))
        c.pin((g2.end[0] + 0.6, g2.end[1]), "Y", side="out")
        self.assertTrue(c.verify({"Y": "~(A & B)"}, quiet=True))

    def test_latches(self):
        c = Circuit()
        u = c.block("DLATCH", at=(5, 0), name="U1")
        for p in ("D", "EN"):
            q = c.pin_of(u, p)
            wire(c, (1, q[1]), q)
            c.pin((1, q[1]), p)
        q = c.pin_of(u, "Q")
        wire(c, q, (6, q[1]))
        c.pin((6, q[1]), "Q", side="out")
        with contextlib.redirect_stdout(io.StringIO()):
            tr = c.sequence([{"D": 1, "EN": 1}, {"D": 0, "EN": 0}, {"D": 0, "EN": 1}], clock="CLK")
        self.assertEqual([t["end"]["Q"] for t in tr], [1, 1, 0])


class NotationTermTests(unittest.TestCase):
    def test_code_names_block_and_textbook_notation_passes(self):
        bad = check_text("위상차는 사분면이 맞도록 atan2로 구하였다.\n\n$$\\angle H = \\operatorname{atan2}(b, a)$$\n")
        self.assertEqual(sum(w.startswith("[표기]") for w in bad), 2)
        good = check_text("위상은 다음과 같다.\n\n$$\\angle H = -\\tan^{-1}\\frac{\\omega L}{R}$$\n\n코드의 `atan2(y, x)`는 사분면을 구분한다.\n")
        self.assertFalse([w for w in good if w.startswith("[표기")])

    def test_terms_table_drives_warnings(self):
        self.assertTrue(load_terms())
        w = [x for x in check_text("출력과 반전 단자 사이에 음의 되먹임을 걸었다. 커패시터는 디커플링용이다. 게인이 커졌다.\n") if x.startswith("[용어]")]
        self.assertEqual(len(w), 3)   # '음의 되먹임'은 한 번만 (안의 '되먹임'을 다시 세지 않는다)
        self.assertTrue(any("negative feedback" in x for x in w))
        self.assertFalse([x for x in check_text("가상 단락과 차단 주파수, 커패시터와 저항.\n") if x.startswith("[용어]")])


class BodeTests(unittest.TestCase):
    def test_si_and_passband(self):
        import numpy as np
        self.assertAlmostEqual(bode.si("4.7k"), 4700)
        self.assertAlmostEqual(bode.si("100n"), 1e-7)
        self.assertAlmostEqual(bode.si("10mH"), 0.01)
        f = np.logspace(1, 6, 800)
        h = bode.response("1/(1+s*R*C)", {"R": 1e3, "C": 1e-7}, f)
        db = 20 * np.log10(abs(h))
        fc = bode.crossings(f, db, bode.passband_db(f, db) - 3.0103)
        self.assertEqual(len(fc), 1)
        self.assertAlmostEqual(fc[0], 1 / (2 * np.pi * 1e-4), delta=5)
        ph = bode.phase_deg(bode.response("1/(1 - w**2*L*C + s*R*C)", {"R": 1e3, "L": 1e-2, "C": 1e-7}, f))
        self.assertTrue(np.all(np.diff(ph) <= 1e-9) and ph[-1] < -170)   # −180°까지 끊김 없이


class TextbookQuestionTests(unittest.TestCase):
    TEXT = ("목차\n실험 1 계측 장비 .... 1\n실험 2 키르히호프 법칙 .... 9\n실험 3 RLC .... 17\n"
            "\f실험 1. 계측 장비\n1. 실험 목적\n멀티미터.\n2. 모의 실험 보고서\n(1) 전압을 계산하라.\n(2) 시뮬레이션하라.\n  1) 1 kHz\n"
            "\f3. 실험 방법\n생략\n4. 실험 보고서\n(1) 측정값을 비교하라.\n"
            "\f실험 2 키르히호프 법칙\n1. 모의 실험 보고서\n① KVL을 확인하라.\n② KCL을 확인하라.\n"
            "\f2. 실험 보고서\n① 표 2-1을 완성하라.\n")

    def test_sections_pick_the_lab_chapter_with_pages(self):
        s1 = report_sections(self.TEXT, 1)
        self.assertEqual([i for i, *_ in s1["prelab"]["items"]], ["(1)", "(2)"])
        self.assertNotIn("실험 방법", s1["prelab"]["items"][1][1])
        self.assertEqual(s1["report"]["page"], 3)
        s2 = report_sections(self.TEXT, 2)
        self.assertEqual([i for i, *_ in s2["prelab"]["items"]], ["①", "②"])
        self.assertEqual((s2["report"]["page"], s2["report"]["items"][0][2]), (5, 5))
        self.assertEqual(report_sections(self.TEXT, 3), {})

    def test_requirements_draft_is_provisional(self):
        import yaml
        data = yaml.safe_load(requirements_yaml(report_sections(self.TEXT, 1), "../materials/textbook.pdf"))
        self.assertEqual(data["scope"]["prelab"]["status"], "provisional")
        self.assertEqual({i["status"] for i in data["items"]}, {"missing"})
        self.assertEqual(len(data["items"]), 3)


if __name__ == "__main__":
    unittest.main()
