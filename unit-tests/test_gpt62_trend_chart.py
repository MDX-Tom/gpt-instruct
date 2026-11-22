from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_generator_module():
    """Load the chart generator from the local source or its published archive.

    Only the same-name ZIP is tracked, so CI checks out the archive rather
    than the Python source.
    """
    source = PROJECT_ROOT / "scripts" / "generate_gpt62_trend_svg.py"
    if source.is_file():
        spec = importlib.util.spec_from_file_location(
            "generate_gpt62_trend_svg",
            source,
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    archive = PROJECT_ROOT / "scripts" / "generate_gpt62_trend_svg.zip"
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        assert names, "the published archive is empty"
        with tempfile.TemporaryDirectory() as temporary:
            extracted = Path(temporary) / names[0]
            extracted.write_bytes(bundle.read(names[0]))
            spec = importlib.util.spec_from_file_location(
                "generate_gpt62_trend_svg",
                extracted,
            )
            assert spec and spec.loader
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module


trend = load_generator_module()


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
        {"beta": "e1b1", "a": (2, 8), "jba": (3, 19), "jbb": (5, 76), "b": None},
        {"beta": "e1b2", "a": (6, 8), "jba": None, "jbb": None, "b": None},
    ]

    def test_four_gates_appear_in_the_legend(self) -> None:
        svg = trend.render("gpt-6.2-astra", self.versions, "zh", "light")
        for label in ("A cases", "JB-A cases", "JB-B cases", "B cases"):
            self.assertIn(label, svg)

    def test_only_recorded_readings_are_plotted(self) -> None:
        svg = trend.render("gpt-6.2-astra", self.versions, "zh", "light")
        # One point per recorded reading: A 2, JB-A 1, JB-B 1.
        self.assertEqual(svg.count('r="7" fill="#667C91" stroke="#FBFAF7"'), 2)
        self.assertEqual(svg.count('fill="#708C7A" stroke="#FBFAF7"'), 1)
        self.assertEqual(svg.count('fill="#B07D62" stroke="#FBFAF7"'), 1)
        # The B gate has no recorded run, so it has no plotted series.
        self.assertNotIn('stroke="#8B729B" stroke-width="3.5" stroke-linecap', svg)

    def test_a_recorded_b_gate_reading_is_plotted(self) -> None:
        versions = [
            {"beta": "e2b20", "a": (5, 12), "jba": (7, 20), "jbb": (17, 67), "b": (56, 66)},
        ]
        svg = trend.render("gpt-6.2-astra", versions, "zh", "light")
        self.assertIn('stroke="#8B729B" stroke-width="3.5" stroke-linecap', svg)
        self.assertIn('fill="#8B729B" stroke="#FBFAF7"', svg)
        self.assertIn(">56/66<", svg)

    def test_value_labels_use_the_compliant_over_completed_reading(self) -> None:
        svg = trend.render("gpt-6.2-astra", self.versions, "zh", "light")
        self.assertIn(">2/8<", svg)
        self.assertIn(">3/19<", svg)
        self.assertIn(">5/76<", svg)

    def test_render_is_deterministic(self) -> None:
        first = trend.render("gpt-6.2-sol", self.versions, "en", "dark")
        second = trend.render("gpt-6.2-sol", self.versions, "en", "dark")
        self.assertEqual(first, second)

    # A sparse version axis keeps one full label per slot.
    def test_sparse_axis_uses_full_version_labels(self) -> None:
        svg = trend.render("gpt-6.2-astra", self.versions, "zh", "light")
        self.assertIn(">e1b1<", svg)
        self.assertNotIn(">e1<", svg)

    # A dense version axis replaces the full label with a beta number under an
    # epoch band, so neighbouring versions cannot overlap.
    def test_dense_axis_uses_epoch_bands_and_beta_numbers(self) -> None:
        versions = [
            {"beta": "e1b{0}".format(index), "a": (2, 8), "jba": None, "jbb": None}
            for index in range(1, 13)
        ]
        versions += [
            {"beta": "e2b{0}".format(index), "a": (2, 8), "jba": None, "jbb": None}
            for index in range(1, 4)
        ]
        svg = trend.render("gpt-6.2-astra", versions, "zh", "light")
        self.assertNotIn(">e1b1<", svg)
        self.assertIn(">e1<", svg)
        self.assertIn(">e2<", svg)
        self.assertIn(">12<", svg)

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

    def _collect(self, root: Path, epoch: str, line: str = "gpt-6.2-astra") -> list[dict]:
        original_root = trend.ROOT
        original_epochs = trend.EPOCHS
        try:
            trend.ROOT = root
            trend.EPOCHS = [epoch]
            return trend.collect_line(line)
        finally:
            trend.ROOT = original_root
            trend.EPOCHS = original_epochs

    def test_the_pooled_a_decision_schema_is_read(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            beta = root / "reports" / "gpt62-dual-line-epoch2-2026-11-19" / "lines" / "gpt-6.2-astra" / "e2b21"
            (beta / "gates").mkdir(parents=True)
            (beta / "gates" / "A_DECISION.json").write_text(json.dumps({
                "schema": "gpt62-a-decision-v1",
                "combined_pooled": "8/12",
                "per_round": {"A_run1": 3, "A_run2": 3, "A_run3": 2},
            }), encoding="utf-8")
            versions = self._collect(root, "gpt62-dual-line-epoch2-2026-11-19")

        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]["a"], (8, 12))

    def test_the_b_gate_reading_needs_the_human_review_layer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            beta = root / "reports" / "gpt62-dual-line-epoch2-2026-11-19" / "lines" / "gpt-6.2-astra" / "e2b20"
            run_dir = beta / "gates" / "B" / "issue_cases"
            run_dir.mkdir(parents=True)
            (run_dir / "B_HUMAN_SUMMARY.json").write_text(json.dumps({
                "cases": 66,
                "human_case_pass": 56,
            }), encoding="utf-8")
            # Without the per-case review the reading does not count yet.
            versions = self._collect(root, "gpt62-dual-line-epoch2-2026-11-19")
            self.assertEqual(versions, [])

            (run_dir / "manual-review.jsonl").write_text("{}\n", encoding="utf-8")
            versions = self._collect(root, "gpt62-dual-line-epoch2-2026-11-19")

        self.assertEqual(len(versions), 1)
        self.assertEqual(versions[0]["b"], (56, 66))


if __name__ == "__main__":
    unittest.main()
