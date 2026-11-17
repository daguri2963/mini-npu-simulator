"""Behavior checks for the console simulator (standard-library unittest)."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main


class MiniNPUTests(unittest.TestCase):
    def test_mac_and_labels(self):
        cross = main.make_pattern(3, "Cross")
        x_pattern = main.make_pattern(3, "X")
        self.assertEqual(main.mac_2d(cross, cross), 5)
        self.assertEqual(main.mac_2d(cross, x_pattern), 1)
        self.assertEqual(main.mac_1d(main.flatten(cross), main.flatten(x_pattern)), 1)
        self.assertEqual(main.normalize_label("+"), "Cross")
        self.assertEqual(main.normalize_label("cross"), "Cross")
        self.assertEqual(main.normalize_label("x"), "X")
        self.assertEqual(main.decide(0.9, 0.8999999999999999), "UNDECIDED")

    def test_bad_console_row_is_retried(self):
        answers = ["0 1", "0 a 0", "0 1 0", "1 1 1", "0 1 0"]
        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=answers), contextlib.redirect_stdout(output):
            result = main.read_matrix("필터 A")
        self.assertEqual(result, main.make_pattern(3, "Cross"))
        self.assertEqual(output.getvalue().count("입력 형식 오류"), 2)

    def test_tie_policy_is_shared_by_both_modes(self):
        cross = main.make_pattern(3, "Cross")
        x_pattern = main.make_pattern(3, "X")
        zero = [[0] * 3 for _ in range(3)]
        console = io.StringIO()
        with mock.patch.object(main, "read_matrix", side_effect=[cross, x_pattern, zero]), \
                mock.patch.object(main, "print_performance"), contextlib.redirect_stdout(console):
            main.user_mode()
        self.assertIn("판정 불가 (UNDECIDED)", console.getvalue())

        json_output = io.StringIO()
        with contextlib.redirect_stdout(json_output):
            reason = main.analyze_case(
                "size_3_1", {"input": zero, "expected": "+"},
                {3: {"Cross": cross, "X": x_pattern}}, {})
        self.assertIn("UNDECIDED", reason)
        self.assertIn("FAIL", json_output.getvalue())

    def test_invalid_json_case_does_not_stop_next_case(self):
        document = {
            "filters": {"size_5": {
                "cross": main.make_pattern(5, "Cross"),
                "x": main.make_pattern(5, "X")}},
            "patterns": {
                "size_5_1": {"input": [[0] * 5 for _ in range(4)], "expected": "+"},
                "size_5_2": {"input": main.make_pattern(5, "X"), "expected": "x"},
            },
        }
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            with mock.patch.object(main, "print_performance"), contextlib.redirect_stdout(output):
                exit_code = main.json_mode(path)
        self.assertEqual(exit_code, 0)
        self.assertIn("size_5_1: 스키마/데이터 오류", output.getvalue())
        self.assertIn("총 테스트: 2개 | 통과: 1개 | 실패: 1개", output.getvalue())
        self.assertIn("실패 비율: 50.0%", output.getvalue())

    def test_benchmark_calls_each_mac_ten_times_without_io(self):
        pattern = main.make_pattern(5, "Cross")
        filter_matrix = main.make_pattern(5, "X")
        two_d = main.mac_2d
        one_d = main.mac_1d
        blocked = AssertionError("I/O must not run inside benchmark")
        with mock.patch.object(main, "mac_2d", wraps=two_d) as measured_2d, \
                mock.patch.object(main, "mac_1d", wraps=one_d) as measured_1d, \
                mock.patch("builtins.input", side_effect=blocked), \
                mock.patch("builtins.print", side_effect=blocked), \
                mock.patch.object(Path, "open", side_effect=blocked):
            elapsed = main.benchmark(pattern, filter_matrix)
        self.assertEqual(measured_2d.call_count, 10)
        self.assertEqual(measured_1d.call_count, 10)
        self.assertEqual(len(elapsed), 2)
        self.assertTrue(all(ms >= 0 for ms in elapsed))
        with self.assertRaisesRegex(ValueError, "최소 10회"):
            main.benchmark(pattern, filter_matrix, repeats=9)


if __name__ == "__main__":
    unittest.main()
