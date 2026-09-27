"""Profile persistence + deterministic matching for a newly registered (non-demo) account."""

import time

import httpx

BASE = "http://localhost:8001/api"


def _register(client: httpx.Client) -> dict:
    unique = f"tscheck-profile-{int(time.time() * 1000)}"
    payload = {
        "full_name": f"Tscheck Student {unique}",
        "email": f"{unique}@example.com",
        "password": "Passw0rd6",
        "confirm_password": "Passw0rd6",
    }
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_profile_multi_field_persists_and_drives_matching_and_isolated_from_demo():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        _register(c)

        before = c.get("/profile")
        assert before.status_code == 200
        profile = before.json()
        assert profile["full_name"].startswith("Tscheck Student")

        update = {
            **{k: v for k, v in profile.items() if k != "user_id"},
            "course": "B.Tech",
            "year": "3rd Year",
            "marks": 91,
            "score_value": "91",
            "state": "Maharashtra",
            "annual_income": 150000,
            "category": profile["category"],
        }
        r = c.put("/profile", json=update)
        assert r.status_code == 200, r.text
        saved = r.json()
        assert saved["course"] == "B.Tech"
        assert saved["marks"] == 91
        assert saved["state"] == "Maharashtra"
        assert saved["annual_income"] == 150000

        # GET again (simulates refresh) confirms persistence, not just echoed response.
        after = c.get("/profile")
        assert after.status_code == 200
        after_json = after.json()
        assert after_json["course"] == "B.Tech"
        assert after_json["marks"] == 91
        assert after_json["state"] == "Maharashtra"
        assert after_json["annual_income"] == 150000

        # Deterministic matching recalculated from the saved profile (national-stem requires
        # B.Tech / Engineering, marks >= 75, income <= 2.5 lakh -> should MATCH academic/course/income).
        detail = c.get("/scholarships/national-stem")
        assert detail.status_code == 200, detail.text
        conditions = {cond["key"]: cond for cond in detail.json()["conditions"]}
        assert conditions["course"]["status"] == "MATCH"
        assert conditions["marks"]["status"] == "MATCH"
        assert conditions["income"]["status"] == "MATCH"

        # Demo account remains a separate, untouched record (data isolation).
        with httpx.Client(base_url=BASE, timeout=30) as demo_client:
            demo_login = demo_client.post("/auth/login", json={"email": "aarav.demo@vidyadwar.app", "password": "demo123"})
            assert demo_login.status_code == 200, demo_login.text
            demo_profile = demo_client.get("/profile").json()
            assert demo_profile["full_name"] == "Aarav"
            assert demo_profile["state"] == "Maharashtra"
            assert demo_profile["marks"] == 82
