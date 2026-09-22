import tempfile
from pathlib import Path
from docstudio.claims_ledger import ClaimsLedger

def test_claims_ledger_json_ingest_and_provenance():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = ClaimsLedger(ledger_path=None)
        research_claims = {
            "claims": [
                {
                    "claim_id": "C001",
                    "claim": "Flight 19 departed with 5 TBM Avenger torpedo bombers.",
                    "number_or_date": "5",
                    "unit": "aircraft",
                    "verification_status": "verified",
                    "sources": ["Naval History & Heritage Command"],
                },
                {
                    "claim_id": "C002",
                    "claim": "Some claim a UFO abducted the squadron off the coast.",
                    "number_or_date": "",
                    "verification_status": "disputed",
                    "sources": ["Tabloid accounts"],
                },
            ]
        }
        count = ledger.ingest_research_claims(research_claims)
        assert count == 2
        assert ledger.get_claim("C001") is not None
        assert "5" in ledger.number_index

        # Export to JSON
        json_path = Path(tmpdir) / "claims.json"
        ledger.export_json(json_path)
        assert json_path.exists()

        # Reload from JSON
        ledger2 = ClaimsLedger(ledger_path=json_path)
        assert len(ledger2.claims) == 2
        assert ledger2.get_claim("C001").number_or_date == "5"

        # Verify narration provenance
        valid_paras = [
            {"paragraph_id": "P1", "text": "A flight of 5 bombers took off from Fort Lauderdale.", "claim_ids": ["C001"]},
            {"paragraph_id": "P2", "text": "Sensationalists claimed allegedly that anomalous craft intervened.", "claim_ids": ["C002"]},
        ]
        ok, violations = ledger2.verify_narration_claim_provenance(valid_paras)
        assert ok is True
        assert violations == []

        # Disputed claim without uncertainty words should fail
        unhedged_disputed = [
            {"paragraph_id": "P3", "text": "A UFO abducted the squadron over the water.", "claim_ids": ["C002"]}
        ]
        ok2, violations2 = ledger2.verify_narration_claim_provenance(unhedged_disputed)
        assert ok2 is False
        assert any("DISPUTED" in v for v in violations2)
