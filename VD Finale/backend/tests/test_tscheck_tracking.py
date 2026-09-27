from pathlib import Path
import time

import httpx


BASE_URL = "http://localhost:8001"
ROOT = Path(__file__).parents[2]


def _registration_payload(label: str) -> dict[str, str]:
    unique = time.time_ns()
    return {
        "full_name": f"{label} {unique}",
        "email": f"{label.lower().replace(' ', '-')}-{unique}@example.com",
        "password": "Passw0rd6",
        "confirm_password": "Passw0rd6",
    }


def _tracking(client: httpx.Client) -> dict[str, dict]:
    response = client.get("/api/tracking")
    assert response.status_code == 200, response.text
    items = response.json()
    assert len(items) == len({item["scholarship_id"] for item in items})
    return {item["scholarship_id"]: item for item in items}


def test_event_driven_tracking_is_idempotent_monotonic_and_isolated():
    with httpx.Client(base_url=BASE_URL, timeout=30) as demo_client:
        assert demo_client.post("/api/auth/demo").status_code == 200
        demo_before = sorted(demo_client.get("/api/tracking").json(), key=lambda item: item["scholarship_id"])

    with httpx.Client(base_url=BASE_URL, timeout=30) as owner:
        register = owner.post("/api/auth/register", json=_registration_payload("Tracking Owner"))
        assert register.status_code == 200, register.text

        # A new user starts empty; the UI has a real empty state instead of an empty grid.
        assert _tracking(owner) == {}
        tracking_source = (ROOT / "frontend" / "src" / "pages" / "Workspace.tsx").read_text(encoding="utf-8")
        assert 'data-testid="tracking-empty-state"' in tracking_source
        assert "No scholarships are being tracked yet." in tracking_source

        # Opening one detail record repeatedly creates exactly one Discovered record.
        for _ in range(3):
            detail = owner.get("/api/scholarships/national-stem")
            assert detail.status_code == 200, detail.text
        records = _tracking(owner)
        assert list(records) == ["national-stem"]
        assert records["national-stem"]["stage"] == "Discovered"

        # A second scholarship creates one additional record, never a catalog-wide set.
        second = owner.get("/api/scholarships/maharashtra-support")
        assert second.status_code == 200, second.text
        records = _tracking(owner)
        assert set(records) == {"national-stem", "maharashtra-support"}

        # Running the existing conflict analysis promotes both selected records in place.
        conflict = owner.post(
            "/api/conflicts/analyze",
            json={"scholarship_ids": ["national-stem", "maharashtra-support"]},
        )
        assert conflict.status_code == 200, conflict.text
        records = _tracking(owner)
        assert len(records) == 2
        assert all(item["stage"] == "Compatibility Reviewed" for item in records.values())

        # An earlier automatic event cannot downgrade a later stage.
        assert owner.get("/api/scholarships/national-stem").status_code == 200
        assert _tracking(owner)["national-stem"]["stage"] == "Compatibility Reviewed"

        # The existing manual dropdown endpoint still updates the user's own record.
        manual = owner.patch("/api/tracking/national-stem", json={"stage": "Applied"})
        assert manual.status_code == 200, manual.text
        assert manual.json()["stage"] == "Applied"
        assert owner.get("/api/scholarships/national-stem").status_code == 200
        assert _tracking(owner)["national-stem"]["stage"] == "Applied"

        # Document completion promotes an already tracked scholarship without tracking the catalog.
        assert owner.get("/api/scholarships/future-tech-merit").status_code == 200
        documents = owner.get("/api/documents").json()
        by_name = {item["name"]: item for item in documents}
        pdf = b"%PDF-1.4\ntracking readiness test\n%%EOF"
        for name in ("Marksheet", "Bank Details"):
            upload = owner.post(
                f"/api/documents/{by_name[name]['id']}/upload",
                files={"file": (f"{name.lower().replace(' ', '-')}.pdf", pdf, "application/pdf")},
            )
            assert upload.status_code == 200, upload.text
        records = _tracking(owner)
        assert len(records) == 3
        assert records["future-tech-merit"]["stage"] == "Documents"
        assert records["national-stem"]["stage"] == "Applied"

        for name in ("Marksheet", "Bank Details"):
            assert owner.delete(f"/api/documents/{by_name[name]['id']}/file").status_code == 200
        assert _tracking(owner)["future-tech-merit"]["stage"] == "Documents"

        # Another session sees and changes only its own tracking record.
        with httpx.Client(base_url=BASE_URL, timeout=30) as other:
            other_register = other.post("/api/auth/register", json=_registration_payload("Tracking Other"))
            assert other_register.status_code == 200, other_register.text
            assert _tracking(other) == {}
            other_manual = other.patch("/api/tracking/national-stem", json={"stage": "Eligibility Checked"})
            assert other_manual.status_code == 200, other_manual.text
            assert _tracking(other)["national-stem"]["stage"] == "Eligibility Checked"
            assert _tracking(owner)["national-stem"]["stage"] == "Applied"

    with httpx.Client(base_url=BASE_URL, timeout=30) as demo_client:
        assert demo_client.post("/api/auth/demo").status_code == 200
        demo_after = sorted(demo_client.get("/api/tracking").json(), key=lambda item: item["scholarship_id"])
        assert demo_after == demo_before
