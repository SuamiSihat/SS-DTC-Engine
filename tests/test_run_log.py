"""Unit tests for scripts/run_log.py token handling. Stdlib only.

Run: python -m unittest discover -s tests -v
"""
import pathlib, sys, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import run_log  # noqa: E402


class ParseTokens(unittest.TestCase):
    def test_suffixes_and_aliases(self):
        t = run_log.parse_tokens(["output=12.3k", "input=800", "cache-read=1.2m", "cache_write=1,500"], "app")
        self.assertEqual((t["output_tokens"], t["input_tokens"], t["cache_read_input_tokens"], t["cache_creation_input_tokens"]),
                         (12300, 800, 1200000, 1500))
        self.assertEqual(t["source"], "entered by hand (app)")

    def test_bad_values_exit(self):
        for bad in (["output=lots"], ["tokens=5"], ["output=0"]):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                run_log.parse_tokens(bad)


class Summary(unittest.TestCase):
    BASE = {"batch": "b", "workflow": "direction", "start": "2026-11-16T12:00:00+08:00", "raws": 1, "raw_seconds": 60,
            "steps": [], "videos": 1, "images": 0, "outputs": []}

    def test_not_recorded_says_how_to_fix(self):
        md = run_log.summary_md(dict(self.BASE, tokens=None))
        self.assertIn("run_log.py tokens b", md)

    def test_hand_entered_has_no_turns_line(self):
        md = run_log.summary_md(dict(self.BASE, tokens=run_log.parse_tokens(["output=1k"])))
        self.assertIn("Source: entered by hand", md)
        self.assertNotIn("Turns:", md)

    def test_old_auto_log_still_renders(self):
        tk = {"input_tokens": 1, "output_tokens": 2, "cache_creation_input_tokens": 3, "cache_read_input_tokens": 4,
              "turns": 5, "sessions": ["s"], "models": ["m"]}
        md = run_log.summary_md(dict(self.BASE, tokens=tk))
        self.assertIn("Turns: 5", md)
        self.assertIn("Source: Claude Code session logs", md)


if __name__ == "__main__":
    unittest.main()
