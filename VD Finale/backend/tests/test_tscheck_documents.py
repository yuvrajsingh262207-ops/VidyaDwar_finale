from pathlib import Path
import time

import httpx


BASE_URL = "http://localhost:8001"
MAX_UPLOAD_SIZE = 5 * 1024 * 1024
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
EXPECTED_DOCUMENTS = {
    "Marksheet",
    "Income Certificate",
    "Domicile Certificate",
    "Bank Details",
    "Category Certificate",
}


def _registration_payload(label: str) -> dict[str, str]:
    unique = time.time_ns()
    return {
        "full_name": f"{label} {unique}",
        "email": f"{label.lower().replace(' ', '-')}-{unique}@example.com",
        "password": "Passw0rd6",
        "confirm_password": "Passw0rd6",
    }


def test_document_vault_lifecycle_isolation_readiness_and_demo_compatibility():
    with httpx.Client(base_url=BASE_URL, timeout=30) as demo_client:
        assert demo_client.post("/api/auth/demo").status_code == 200
        demo_before = demo_client.get("/api/documents").json()

    files_before = set(UPLOAD_DIR.glob("*")) if UPLOAD_DIR.exists() else set()
    with httpx.Client(base_url=BASE_URL, timeout=30) as client:
        register = client.post("/api/auth/register", json=_registration_payload("Vault Owner"))
        assert register.status_code == 200, register.text

        documents = client.get("/api/documents").json()
        assert {item["name"] for item in documents} == EXPECTED_DOCUMENTS
        assert len(documents) == len(EXPECTED_DOCUMENTS)
        assert all(item["available"] is False for item in documents)
        assert all(item["has_file"] is False for item in documents)
        assert all(item["original_filename"] is None for item in documents)

        initial = client.get("/api/readiness").json()
        assert initial["documents_ready"] == 0
        assert initial["documents_total"] == len(EXPECTED_DOCUMENTS)
        assert initial["overall_status"] == "Action Required"

        income = next(item for item in documents if item["name"] == "Income Certificate")
        marksheet = next(item for item in documents if item["name"] == "Marksheet")
        pdf_content = b"%PDF-1.4\nVidyadwar vault test\n%%EOF"
        upload = client.post(
            f"/api/documents/{income['id']}/upload",
            files={"file": ("income-certificate.pdf", pdf_content, "application/pdf")},
        )
        assert upload.status_code == 200, upload.text
        uploaded = upload.json()
        assert uploaded["available"] is True
        assert uploaded["has_file"] is True
        assert uploaded["original_filename"] == "income-certificate.pdf"
        assert uploaded["mime_type"] == "application/pdf"
        assert uploaded["file_size"] == len(pdf_content)
        assert uploaded["uploaded_at"] is not None
        assert "stored_filename" not in uploaded
        assert len(uploaded["required_for"]) > 1

        files_after_upload = set(UPLOAD_DIR.glob("*"))
        first_physical_file = next(iter(files_after_upload - files_before))
        assert len(files_after_upload - files_before) == 1

        viewed = client.get(f"/api/documents/{income['id']}/file")
        assert viewed.status_code == 200
        assert viewed.content == pdf_content
        assert viewed.headers["content-type"].startswith("application/pdf")

        scholarships = client.get("/api/scholarships").json()
        reused_by = [item for item in scholarships if item["scholarship"]["id"] in income["required_for"]]
        assert len(reused_by) > 1
        assert all(item["documents_ready"] == 1 for item in reused_by)

        second_fetch = client.get("/api/documents").json()
        assert len(second_fetch) == len(EXPECTED_DOCUMENTS)
        assert len({item["id"] for item in second_fetch}) == len(EXPECTED_DOCUMENTS)

        with httpx.Client(base_url=BASE_URL, timeout=30) as other_client:
            other_register = other_client.post("/api/auth/register", json=_registration_payload("Other User"))
            assert other_register.status_code == 200, other_register.text
            assert other_client.get(f"/api/documents/{income['id']}/file").status_code == 404
            assert other_client.post(
                f"/api/documents/{income['id']}/upload",
                files={"file": ("other.pdf", pdf_content, "application/pdf")},
            ).status_code == 404
            assert other_client.delete(f"/api/documents/{income['id']}/file").status_code == 404

        unsupported = client.post(
            f"/api/documents/{marksheet['id']}/upload",
            files={"file": ("malware.exe", b"MZ-not-an-upload", "application/octet-stream")},
        )
        assert unsupported.status_code == 400
        assert "PDF" in unsupported.json()["detail"]

        oversized = b"%PDF-" + (b"0" * MAX_UPLOAD_SIZE)
        too_large = client.post(
            f"/api/documents/{marksheet['id']}/upload",
            files={"file": ("too-large.pdf", oversized, "application/pdf")},
        )
        assert too_large.status_code == 413
        assert "5 MB" in too_large.json()["detail"]

        png_content = b"\x89PNG\r\n\x1a\nreplacement"
        replace = client.post(
            f"/api/documents/{income['id']}/upload",
            files={"file": ("income-new.png", png_content, "image/png")},
        )
        assert replace.status_code == 200, replace.text
        assert replace.json()["original_filename"] == "income-new.png"
        assert replace.json()["mime_type"] == "image/png"
        files_after_replace = set(UPLOAD_DIR.glob("*"))
        assert first_physical_file not in files_after_replace
        assert len(files_after_replace - files_before) == 1
        assert client.get(f"/api/documents/{income['id']}/file").content == png_content

        marksheet_upload = client.post(
            f"/api/documents/{marksheet['id']}/upload",
            files={"file": ("marksheet.pdf", pdf_content, "application/pdf")},
        )
        assert marksheet_upload.status_code == 200, marksheet_upload.text
        two_ready = client.get("/api/readiness").json()
        assert two_ready["documents_ready"] == 2
        assert two_ready["documents_total"] == len(EXPECTED_DOCUMENTS)

        removed = client.delete(f"/api/documents/{income['id']}/file")
        assert removed.status_code == 200, removed.text
        assert removed.json()["available"] is False
        assert removed.json()["has_file"] is False
        assert removed.json()["original_filename"] is None
        assert client.get(f"/api/documents/{income['id']}/file").status_code == 404
        one_ready = client.get("/api/readiness").json()
        assert one_ready["documents_ready"] == 1
        assert one_ready["documents_total"] == len(EXPECTED_DOCUMENTS)

        second_remove = client.delete(f"/api/documents/{income['id']}/file")
        assert second_remove.status_code == 200
        assert len(client.get("/api/documents").json()) == len(EXPECTED_DOCUMENTS)

        cleanup = client.delete(f"/api/documents/{marksheet['id']}/file")
        assert cleanup.status_code == 200
        assert set(UPLOAD_DIR.glob("*")) == files_before

    with httpx.Client(base_url=BASE_URL, timeout=30) as demo_client:
        assert demo_client.post("/api/auth/demo").status_code == 200
        demo_after = demo_client.get("/api/documents").json()
        assert demo_after == demo_before
