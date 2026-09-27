"""Broad scholarship catalog scale and source-type coverage for filters/search."""

import httpx

BASE = "http://localhost:8001/api"


def test_catalog_has_at_least_25_records_across_expected_sources():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        assert c.post("/auth/demo").status_code == 200
        r = c.get("/scholarships")
        assert r.status_code == 200, r.text
        rows = r.json()
        assert len(rows) >= 25, f"expected >=25 catalog records, got {len(rows)}"

        source_types = {row["scholarship"]["source_type"] for row in rows}
        # At least a meaningful subset of the documented source taxonomy must be present.
        expected_present = {"AICTE", "MahaDBT", "State Government", "Prototype"}
        assert expected_present.issubset(source_types), source_types

        ids = {row["scholarship"]["id"] for row in rows}
        assert "aicte-pragati" in ids
        assert "national-stem" in ids
        assert "maharashtra-support" in ids

        pragati = next(row for row in rows if row["scholarship"]["id"] == "aicte-pragati")
        assert pragati["scholarship"]["data_status"] == "Verified Official"
        # AICTE Pragati intentionally requires official verification for detailed criteria.
        assert pragati["overall_status"] == "REVIEW"
