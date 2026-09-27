import time
import httpx


def test_register_creates_session_and_me_matches():
    unique = f"tscheck-register-{int(time.time() * 1000)}"
    email = f"{unique}@example.com"
    full_name = f"Tscheck Register {unique}"
    payload = {
        "full_name": full_name,
        "email": email,
        "password": "Passw0rd6",
        "confirm_password": "Passw0rd6",
    }
    with httpx.Client(base_url="http://localhost:8001", timeout=10) as c:
        r = c.post("/api/auth/register", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["user"]["full_name"] == full_name
        assert body["profile"]["full_name"] == full_name
        assert body.get("demo_mode") in (False, None)

        # cookie-based session should authenticate subsequent /auth/me
        r2 = c.get("/api/auth/me")
        assert r2.status_code == 200, r2.text
        me = r2.json()
        assert me["user"]["email"] == email
        assert me["profile"]["full_name"] == full_name


def test_register_rejects_mismatched_passwords():
    unique = f"tscheck-register-mismatch-{int(time.time() * 1000)}"
    email = f"{unique}@example.com"
    payload = {
        "full_name": f"Tscheck Mismatch {unique}",
        "email": email,
        "password": "Passw0rd6",
        "confirm_password": "Different9",
    }
    with httpx.Client(base_url="http://localhost:8001", timeout=10) as c:
        r = c.post("/api/auth/register", json=payload)
        assert r.status_code == 400, r.text
        assert "match" in r.json()["detail"].lower()
