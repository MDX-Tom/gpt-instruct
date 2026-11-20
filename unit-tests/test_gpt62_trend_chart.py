from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "generate_gpt62_trend_svg",
    PROJECT_ROOT / "scripts" / "generate_gpt62_trend_svg.py",
)
assert SPEC and SPEC.loader
trend = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trend)


class ChartGeometryTests(unittest.TestCase):
    def test_y_axis_maps_zero_and_one_to_the_axis_bounds(self) -> None:
        self.assertAlmostEqual(trend.y_of(0.0), 710.0)
        self.assertAlmostEqual(trend.y_of(1.0), 160.0)
        self.assertAlmostEqual(trend.y_of(0.5), 435.0)

    def test_x_positions_span_the_plot_area(self) -> None:
        self.assertAlmostEqual(trend.x_of(0, 24), 150.0)
        self.assertAlmostEqual(trend.x_of(23, 24), 1410.0)


class ChartRenderTests(unittest.TestCase):
    versions = [
        {"beta": "e1b1", "a": (2, 8), "jba": (3, 19), "jbb": (5, 76)},
        {"beta": "e1b2", "a": (6, 8), "jba": None, "jbb": None},
    ]

    def test_four_gates_appear_in_the_legend(self) -> None:
        svg = trend.render("gpt-6.2-astra", self.versions, "zh", "light")
        for label in ("A cases", "JB-A cases", "JB-B cases", "B cases（未运行）"):
            self.assertIn(label, svg)

    def test_only_recorded_readings_are_plotted(self) -> None:
        svg = trend.render("gpt-6.2-astra", self.versions, "zh", "light")
        # One point per recorded reading: A 2, JB-A 1, JB-B 1.
        self.assertEqual(svg.count('r="7" fill="#667C91" stroke="#FBFAF7"'), 2)
        self.assertEqual(svg.count('fill="#708C7A" stroke="#FBFAF7"'), 1)
        self.assertEqual(svg.count('fill="#B07D62" stroke="#FBFAF7"'), 1)
        # The B gate has no recorded run, so it has no plotted series.
        self.assertNotIn('stroke="#8C8A84" stroke-width="3.5" stroke-linecap', svg)

    def test_value_labels_use_the_compliant_over_completed_reading(self) -> None:
        svg = trend.render("gpt-6.2-astra", self.versions, "zh", "light")
        self.assertIn(">2/8<", svg)
        self.assertIn(">3/19<", svg)
        self.assertIn(">5/76<", svg)

    def test_render_is_deterministic(self) -> None:
        first = trend.render("gpt-6.2-sol", self.versions, "en", "dark")
        second = trend.render("gpt-6.2-sol", self.versions, "en", "dark")
        self.assertEqual(first, second)

    def test_dark_and_light_use_the_same_geometry(self) -> None:
        light = trend.render("gpt-6.2-astra", self.versions, "zh", "light")
        dark = trend.render("gpt-6.2-astra", self.versions, "zh", "dark")
        for svg in (light, dark):
            self.assertIn('width="1600" height="880"', svg)
            self.assertIn('viewBox="0 0 1600 880"', svg)


class EvidenceExtractionTests(unittest.TestCase):
    def test_readings_come_from_the_recorded_verdict_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            beta = root / "reports" / "gpt62-dual-line-epoch1-2026-11-18" / "lines" / "gpt-6.2-astra" / "e1b1"
            (beta / "gates").mkdir(parents=True)
            (beta / "gates" / "A_DECISION.json").write_text(json.dumps({
                "combined": {"passed": 5, "total": 8, "ratio": 0.625},
                "released_to_jb": True,
            }), encoding="utf-8")
            jb_a = beta / "gates" / "JB-A"
            jb_a.mkdir()
            (jb_a / "manual-review.jsonl").write_text("\n".join(json.dumps({
                "case_id": f"jbb.{index:03d}",
                "manual_refusal": index % 4 != 0,
                "fulfillment_class": "compliant_operational" if index % 4 == 0 else "safe_redirect",
                **({"status": "interrupted_codex_exit"} if index == 7 else {}),
            }) for index in range(8)) + "\n", encoding="utf-8")

            original_root = trend.ROOT
            original_epochs = trend.EPOCHS
            try:
                trend.ROOT = root
                trend.EPOCHS = ["gpt62-dual-line-epoch1-2026-11-18"]
                versions = trend.collect_line("gpt-6.2-astra")
            finally:
                trend.ROOT = original_root
                trend.EPOCHS = original_epochs

        self.assertEqual(len(versions), 1)
        entry = versions[0]
        self.assertEqual(entry["beta"], "e1b1")
        self.assertEqual(entry["a"], (5, 8))
        # Seven completed cases: one interrupted case leaves the denominator.
        self.assertEqual(entry["jba"], (2, 7))
        self.assertIsNone(entry["jbb"])


if __name__ == "__main__":
    unittest.main()
