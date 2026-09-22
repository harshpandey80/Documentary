import unittest
from pathlib import Path
from docstudio.claims_ledger import ClaimsLedger, verify_all_claims_against_sources

class TestClaimsLedger(unittest.TestCase):
    def setUp(self):
        self.ledger_path = Path("claims.csv")
        self.sources_dir = Path("sources")

    def test_claims_csv_exists_and_loads(self):
        self.assertTrue(self.ledger_path.exists(), "claims.csv must exist in project root")
        ledger = ClaimsLedger(self.ledger_path)
        self.assertGreaterEqual(len(ledger.claims), 15, "Must have at least 15 verified claim entries")

        # Verify key claims exist
        clm1 = ledger.get_claim("CLM-001")
        self.assertIsNotNone(clm1)
        self.assertEqual(clm1.number_or_date, "10984")
        self.assertEqual(clm1.unit, "meters")
        self.assertTrue(clm1.graphic_worthy)
        self.assertTrue(len(clm1.human_anchor) > 10)

    def test_all_claims_verify_against_primary_sources(self):
        self.assertTrue(self.sources_dir.exists(), "sources/ directory must exist")
        res = verify_all_claims_against_sources(self.sources_dir, self.ledger_path)
        self.assertEqual(res["failed_count"], 0, f"Found unverified claims in ledger: {res['details']}")
        self.assertEqual(res["verified_count"], res["total_claims"])

    def test_narration_number_verification_blocking(self):
        ledger = ClaimsLedger(self.ledger_path)

        # Narration with verified numbers (10984, 1086, 32000)
        valid_script = (
            "Beneath the Pacific at 10,984 meters depth, ambient hydrostatic pressure "
            "exceeds 1,086 bar. The hydrophone recorded at 32,000 Hertz."
        )
        ok, unverified = ledger.verify_narration_text(valid_script, allow_unverified=False)
        self.assertTrue(ok)
        self.assertEqual(unverified, [])

        # Narration with invented / hallucinated number (e.g. 77,421 meters)
        hallucinated_script = (
            "Deep in the trench at 77,421 meters, secret probes recorded a signal."
        )
        ok, unverified = ledger.verify_narration_text(hallucinated_script, allow_unverified=False)
        self.assertFalse(ok)
        self.assertIn("77421", unverified)

        # Narration with unverified number but override enabled
        ok_override, _ = ledger.verify_narration_text(hallucinated_script, allow_unverified=True)
        self.assertTrue(ok_override)

    def test_hedges_and_legend_claims(self):
        ledger = ClaimsLedger(self.ledger_path)
        # Unhedged legend: King Harold arrow in eye at Hastings (CLM-035)
        unhedged_narration = "In 1066 at Hastings, King Harold was struck in the eye by an arrow and killed."
        ok, violations = ledger.verify_claims_and_hedges(unhedged_narration)
        self.assertFalse(ok)
        self.assertTrue(any("Unhedged claim" in v for v in violations))

        # Properly hedged legend
        hedged_narration = "In 1066 at Hastings, according to legend King Harold was struck in the eye by an arrow."
        ok_hedged, violations_hedged = ledger.verify_claims_and_hedges(hedged_narration)
        self.assertTrue(ok_hedged)
        self.assertEqual(violations_hedged, [])

    def test_absolute_words_verification(self):
        ledger = ClaimsLedger(self.ledger_path)
        # Unbacked absolute word "forever"
        unbacked_script = "The charter stripped royal power forever."
        ok, violations = ledger.verify_claims_and_hedges(unbacked_script)
        self.assertFalse(ok)
        self.assertTrue(any("forever" in v for v in violations))

        # Backed absolute word "largest ever" backed by CLM-028 (35.5 million sq km, absolute_ok=yes)
        backed_script = "Covering 35,500,000 square kilometers, it was the largest ever empire in history."
        ok_backed, violations_backed = ledger.verify_claims_and_hedges(backed_script)
        self.assertTrue(ok_backed)
        self.assertEqual(violations_backed, [])

    def test_overlay_label_policy(self):
        from docstudio.claims_ledger import verify_overlay_label

        # Banned sensationalist words
        ok, err = verify_overlay_label("CLASSIFIED: TOP SECRET")
        self.assertFalse(ok)
        self.assertIn("CLASSIFIED", err)

        ok, err = verify_overlay_label("BREAKING HISTORY")
        self.assertFalse(ok)
        self.assertIn("BREAKING", err)

        ok, err = verify_overlay_label("UNSEALED DOSSIER")
        self.assertFalse(ok)
        self.assertIn("UNSEALED", err)

        # Fabricated sources
        ok, err = verify_overlay_label("THE LONDON TIMES | WAR EDITION")
        self.assertFalse(ok)

        ok, err = verify_overlay_label("FLEET INTEL | 1588")
        self.assertFalse(ok)

        # Valid approved labels
        ok, err = verify_overlay_label("ILLUSTRATION // ARTIST DEPICTION")
        self.assertTrue(ok)

        ok, err = verify_overlay_label("REPLICA // MODERN SAILING SHIP")
        self.assertTrue(ok)

        ok, err = verify_overlay_label("RECREATION // ROMAN LEGION MARCH")
        self.assertTrue(ok)

        ok, err = verify_overlay_label("43 AD // RICHBOROUGH")
        self.assertTrue(ok)

        manifest = {"assets": [{"source": "THE NATIONAL ARCHIVES", "license": "Open Government Licence"}]}
        ok, err = verify_overlay_label("ARCHIVAL // THE NATIONAL ARCHIVES", license_manifest=manifest)
        self.assertTrue(ok)

if __name__ == "__main__":
    unittest.main()

