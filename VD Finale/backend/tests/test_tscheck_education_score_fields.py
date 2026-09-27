"""Education level / academic score type persistence and no-unsafe-conversion behavior.

Covers:
- Class 10/12 -> Grade score type accepted and persisted.
- Undergraduate Degree -> CGPA on a 10-point scale, decimal value persisted and survives a
  fresh GET (simulated refresh / re-login).
- A CGPA profile checked against the percentage-based national-stem rule returns REVIEW with
  an explicit "no official conversion formula" explanation and no numeric percentage conversion.
"""

import time

import httpx

BASE = "http://localhost:8001/api"


def _register(client: httpx.Client) -> dict:
    unique = f"tscheck-edu-{int(time.time() * 1000)}"
    payload = {
        "full_name": f"Tscheck Edu {unique}",
        "email": f"{unique}@example.com",
        "password": "Passw0rd6",
        "confirm_password": "Passw0rd6",
    }
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


def test_class10_grade_score_persists():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        _register(c)
        profile = c.get("/profile").json()

        update = {**{k: v for k, v in profile.items() if k != "user_id"}}
        update["education_level"] = "Class 10"
        update["score_type"] = "Grade"
        update["score_value"] = "A1"
        update["score_scale"] = "Not applicable"

        r = c.put("/profile", json=update)
        assert r.status_code == 200, r.text
        saved = r.json()
        assert saved["education_level"] == "Class 10"
        assert saved["score_type"] == "Grade"
        assert saved["score_value"] == "A1"

        after = c.get("/profile")
        assert after.status_code == 200
        after_json = after.json()
        assert after_json["education_level"] == "Class 10"
        assert after_json["score_type"] == "Grade"
        assert after_json["score_value"] == "A1"


def test_degree_cgpa_10point_scale_persists_and_survives_relogin():
    unique = f"tscheck-cgpa-{int(time.time() * 1000)}"
    email = f"{unique}@example.com"
    password = "Passw0rd6"
    with httpx.Client(base_url=BASE, timeout=30) as c:
        r = c.post("/auth/register", json={
            "full_name": f"Tscheck CGPA {unique}",
            "email": email,
            "password": password,
            "confirm_password": password,
        })
        assert r.status_code == 200, r.text
        profile = c.get("/profile").json()

        update = {**{k: v for k, v in profile.items() if k != "user_id"}}
        update["education_level"] = "Undergraduate Degree"
        update["score_type"] = "CGPA"
        update["score_value"] = "8.6"
        update["score_scale"] = "10"

        r = c.put("/profile", json=update)
        assert r.status_code == 200, r.text
        saved = r.json()
        assert saved["score_type"] == "CGPA"
        assert saved["score_value"] == "8.6"
        assert saved["score_scale"] == "10"

    # Fresh client + login simulates logout/login persistence.
    with httpx.Client(base_url=BASE, timeout=30) as c2:
        login = c2.post("/auth/login", json={"email": email, "password": password})
        assert login.status_code == 200, login.text
        after = c2.get("/profile")
        assert after.status_code == 200
        after_json = after.json()
        assert after_json["score_type"] == "CGPA"
        assert after_json["score_value"] == "8.6"
        assert after_json["score_scale"] == "10"


def test_cgpa_profile_against_percentage_rule_returns_review_without_conversion():
    with httpx.Client(base_url=BASE, timeout=30) as c:
        _register(c)
        profile = c.get("/profile").json()

        update = {**{k: v for k, v in profile.items() if k != "user_id"}}
        update["course"] = "B.Tech"
        update["education_level"] = "Undergraduate Degree"
        update["score_type"] = "CGPA"
        update["score_value"] = "9.2"
        update["score_scale"] = "10"
        update["annual_income"] = 150000

        r = c.put("/profile", json=update)
        assert r.status_code == 200, r.text

        detail = c.get("/scholarships/national-stem")
        assert detail.status_code == 200, detail.text
        conditions = {cond["key"]: cond for cond in detail.json()["conditions"]}
        marks_condition = conditions["marks"]
        assert marks_condition["status"] == "REVIEW"
        explanation = marks_condition["explanation"].lower()
        assert "no official conversion formula is recorded" in explanation
        # No numeric percentage conversion should be attempted anywhere in the explanation.
        assert "converted to" not in explanation
