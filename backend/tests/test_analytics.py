from .conftest import login


def test_overview(client, trainer):
    data = client.get("/api/analytics/overview", headers=trainer).json()
    assert data["trainees"] == 6
    assert data["completed_sessions"] > 0
    assert 0 <= data["pass_rate"] <= 100
    assert 0 <= data["average_score"] <= 100


def test_analytics_are_staff_only(client, trainee):
    for path in ("overview", "heatmap", "trainees", "warehouse"):
        assert client.get(f"/api/analytics/{path}", headers=trainee).status_code == 403


def test_heatmap(client, trainer):
    data = client.get("/api/analytics/heatmap?module=gowning", headers=trainer).json()
    step_codes = {s["code"] for s in data["steps"]}
    deviation_codes = {d["code"] for d in data["deviations"]}
    assert "skipped_step" in deviation_codes
    assert data["cells"]
    for cell in data["cells"]:
        assert cell["step"] in step_codes
        assert cell["deviation"] in deviation_codes
        assert cell["count"] > 0
    assert client.get("/api/analytics/heatmap?module=nope", headers=trainer).status_code == 404


def test_trainee_progress(client, trainer):
    rows = client.get("/api/analytics/trainees", headers=trainer).json()
    assert len(rows) == 6
    for row in rows:
        assert row["sessions"] >= 5
        assert row["passed_sessions"] <= row["sessions"]


def test_trainee_detail_access(client, trainer, trainee):
    me = client.get("/api/auth/me", headers=trainee).json()

    own = client.get(f"/api/analytics/trainees/{me['id']}", headers=trainee)
    assert own.status_code == 200
    assert own.json()["trainee"]["full_name"] == "Lukas Gruber"
    assert own.json()["sessions"]

    assert client.get(f"/api/analytics/trainees/{me['id']}", headers=trainer).status_code == 200

    sophie = login(client, "sophie@alpine.demo")
    assert client.get(f"/api/analytics/trainees/{me['id']}", headers=sophie).status_code == 404
    nordic = login(client, "trainer@nordic.demo")
    assert client.get(f"/api/analytics/trainees/{me['id']}", headers=nordic).status_code == 404


def test_etl_and_warehouse_report(client, admin, trainer):
    summary = client.post("/api/analytics/etl", headers=admin).json()
    assert summary["sessions"] > 0
    assert summary["events"] > 0

    report = client.get("/api/analytics/warehouse", headers=trainer).json()
    assert report["last_run"]["sessions"] == summary["sessions"]
    assert report["weekly"]
    assert {m["module"] for m in report["modules"]} == {"gowning", "aseptic_intervention"}
    assert len(report["top_deviations"]) <= 5

    # DuckDB results are filtered per organisation
    nordic_report = client.get("/api/analytics/warehouse", headers=login(client, "trainer@nordic.demo")).json()
    alpine_sessions = sum(w["sessions"] for w in report["weekly"])
    nordic_sessions = sum(w["sessions"] for w in nordic_report["weekly"])
    assert alpine_sessions + nordic_sessions <= summary["sessions"]
    assert alpine_sessions != nordic_sessions


def test_only_admin_runs_etl(client, trainer):
    assert client.post("/api/analytics/etl", headers=trainer).status_code == 403
