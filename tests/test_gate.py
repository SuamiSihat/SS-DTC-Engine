"""Smoke test for the brand gate (scripts/check_brand.py) and policy screen (scripts/policy_rules.py).

Run: python -m unittest discover -s tests -v
Stdlib only, so CI needs no installs. Uses the committed brands/<slug>/brand.json files.
"""
import json, pathlib, subprocess, sys, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import policy_rules  # noqa: E402


def gate(brand, lines, *extra):
    with tempfile.TemporaryDirectory() as d:
        tf = pathlib.Path(d) / "texts.txt"
        tf.write_text("\n".join(lines), encoding="utf-8")
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_brand.py"), "--brand", brand,
                            "--texts", str(tf), "--json", *extra],
                           capture_output=True, text=True, encoding="utf-8")
    return r.returncode, json.loads(r.stdout)


def levels(findings, level):
    return [f["msg"] for f in findings if f["level"] == level]


class CheckBrand(unittest.TestCase):
    def test_ssclinic_last_slot_blocks(self):
        code, out = gate("ssclinic", ["Slot terakhir minggu ini"])
        self.assertEqual(code, 1)
        self.assertTrue(any("slot terakhir" in m for m in levels(out, "BLOCK")))

    def test_neutral_line_passes(self):
        code, out = gate("drmitring", ["Jumpa doktor untuk pemeriksaan jika ada simptom"])
        self.assertEqual(code, 0, levels(out, "BLOCK"))

    def test_non_ad_brand_blocks(self):
        code, _ = gate("pertabi", ["Jumpa doktor untuk pemeriksaan jika ada simptom"])
        self.assertEqual(code, 1)

    def test_unknown_brand_blocks(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_brand.py"), "--brand", "no-such-brand"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 1)

    def test_doctor_led_service_cites_mmc_v2_2025(self):
        _, out = gate("ssclinic", ["Jumpa doktor untuk pemeriksaan jika ada simptom"], "--doctor", "Dr Test")
        self.assertTrue(any("MMC Guideline V2/2025" in m for m in levels(out, "REVIEW")))

    def test_every_brand_json_loads(self):
        for p in sorted((ROOT / "brands").glob("*/brand.json")):
            with self.subTest(brand=p.parent.name):
                b = json.loads(p.read_text(encoding="utf-8"))
                self.assertIn("gate", b)


class PolicyRules(unittest.TestCase):
    def ids(self, text, btype):
        return {rid for rid, _, _ in policy_rules.scan(text, btype)}

    def test_service_inducement(self):
        self.assertIn("inducement", self.ids("Diskaun 50% bulan ini", "service"))

    def test_service_rule_not_applied_to_products(self):
        self.assertNotIn("inducement", self.ids("Diskaun 50% bulan ini", "product"))

    def test_testimonial_flagged_for_both(self):
        self.assertIn("testimonial", self.ids("Testimoni pesakit kami", "service"))
        self.assertIn("testimonial", self.ids("Testimoni pelanggan kami", "product"))

    def test_rules_are_well_formed(self):
        for rule in policy_rules.RULES:
            self.assertEqual(len(rule), 4, rule)
            self.assertIn(rule[1], ("all", "service", "product"), rule)


if __name__ == "__main__":
    unittest.main()
