from app.domain import MODULES

from .conftest import login

GOWNING_STEPS = [step.code for step in MODULES["gowning"].steps]


def _trainee_id(client, headers, email="lukas@alpine.demo") -> int:
    users = client.get("/api/users?role=trainee", headers=headers).json()
    return next(u["id"] for u in users if u["email"] == email)


def _start(client, headers, trainee_id=None, module="gowning") -> dict:
    body = {"module": module} if trainee_id is None else {"module": module, "trainee_id": trainee_id}
    response = client.post("/api/sessions", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _send(client, headers, session_id, **event):
    return client.post(f"/api/sessions/{session_id}/events", json=event, headers=headers)


def test_modules_catalogue(client, trainee):
    modules = client.get("/api/modules", headers=trainee).json()
    assert {m["code"] for m in modules} == {"gowning", "aseptic_intervention"}
    gowning = next(m for m in modules if m["code"] == "gowning")
    assert [s["code"] for s in gowning["steps"]] == GOWNING_STEPS


def test_perfect_session_passes_and_gets_certificate(client, trainee):
    session = _start(client, trainee)
    assert session["status"] == "running"
    for step in GOWNING_STEPS:
        assert _send(client, trainee, session["id"], kind="step", step=step).status_code == 201

    result = client.post(f"/api/sessions/{session['id']}/finish", headers=trainee).json()
    assert result["status"] == "completed"
    assert result["score"] == 100
    assert result["passed"] is True
    assert result["certificate_code"]

    certificate = client.get(f"/api/certificates/verify/{result['certificate_code']}").json()
    assert certificate["valid"] is True
    assert certificate["trainee_name"] == "Lukas Gruber"
    assert certificate["organization_name"] == "Alpine Pharma GmbH"


def test_deviations_reduce_score_and_skipped_steps_fail(client, trainer):
    session = _start(client, trainer, trainee_id=_trainee_id(client, trainer))
    sid = session["id"]
    event = _send(client, trainer, sid, kind="deviation", step="coverall", deviation="touched_floor").json()
    assert event["severity"] == "major"
    assert event["penalty"] == 10
    for step in GOWNING_STEPS[:-1]:  # forgets the mirror check
        _send(client, trainer, sid, kind="step", step=step)

    result = client.post(f"/api/sessions/{sid}/finish", headers=trainer).json()
    assert result["score"] == 100 - 10 - 25
    assert result["passed"] is False
    assert result["certificate_code"] is None
    skipped = [e for e in result["events"] if e["deviation"] == "skipped_step"]
    assert [e["step"] for e in skipped] == ["mirror_check"]


def test_invalid_events_are_rejected(client, trainee):
    sid = _start(client, trainee)["id"]
    assert _send(client, trainee, sid, kind="step", step="not_a_step").status_code == 422
    assert _send(client, trainee, sid, kind="deviation", step="hood", deviation="made_up").status_code == 422
    assert _send(client, trainee, sid, kind="deviation", step="hood").status_code == 422
    assert _send(client, trainee, sid, kind="step", step="hood", deviation="touched_floor").status_code == 422
    # a deviation that exists, but not in this module
    assert _send(client, trainee, sid, kind="deviation", step="hood", deviation="first_air_blocked").status_code == 422


def test_unknown_module_is_rejected(client, trainee):
    assert client.post("/api/sessions", json={"module": "space_walk"}, headers=trainee).status_code == 422


def test_trainer_must_name_a_trainee_of_own_organisation(client, trainer, other_org_trainer):
    assert client.post("/api/sessions", json={"module": "gowning"}, headers=trainer).status_code == 422
    nordic_trainee = _trainee_id(client, other_org_trainer, "astrid@nordic.demo")
    response = client.post("/api/sessions", json={"module": "gowning", "trainee_id": nordic_trainee}, headers=trainer)
    assert response.status_code == 404


def test_completed_session_is_read_only(client, trainee):
    sid = _start(client, trainee)["id"]
    client.post(f"/api/sessions/{sid}/finish", headers=trainee)
    assert client.post(f"/api/sessions/{sid}/finish", headers=trainee).status_code == 409
    assert _send(client, trainee, sid, kind="step", step="hood").status_code == 409


def test_tenant_isolation(client, trainer, other_org_trainer):
    sid = _start(client, trainer, trainee_id=_trainee_id(client, trainer))["id"]
    assert client.get(f"/api/sessions/{sid}", headers=other_org_trainer).status_code == 404
    other_sessions = client.get("/api/sessions", headers=other_org_trainer).json()
    assert sid not in {s["id"] for s in other_sessions}


def test_trainee_sees_only_own_sessions(client, trainer):
    sophie = login(client, "sophie@alpine.demo")
    lukas_session = _start(client, trainer, trainee_id=_trainee_id(client, trainer))["id"]
    assert client.get(f"/api/sessions/{lukas_session}", headers=sophie).status_code == 404
    sessions = client.get("/api/sessions?limit=200", headers=sophie).json()
    assert sessions and {s["trainee_name"] for s in sessions} == {"Sophie Wagner"}


def test_session_list_filters(client, trainer):
    lukas = _trainee_id(client, trainer)
    _start(client, trainer, trainee_id=lukas)
    running = client.get("/api/sessions?status=running", headers=trainer).json()
    assert len(running) == 1
    assert running[0]["trainee_id"] == lukas
    by_trainee = client.get(f"/api/sessions?trainee_id={lukas}", headers=trainer).json()
    assert {s["trainee_id"] for s in by_trainee} == {lukas}


def test_simulated_session_runs_to_the_end(client, trainer):
    lukas = _trainee_id(client, trainer)
    body = {"module": "aseptic_intervention", "trainee_id": lukas, "skill": 1.0}
    response = client.post("/api/sessions/simulate", json=body, headers=trainer)
    assert response.status_code == 201
    sid = response.json()["id"]

    # The test client waits for background tasks; with skill 1.0 the trainee makes no mistakes.
    detail = client.get(f"/api/sessions/{sid}", headers=trainer).json()
    assert detail["status"] == "completed"
    assert detail["score"] == 100
    assert len(detail["events"]) == len(MODULES["aseptic_intervention"].steps)


def test_trainee_cannot_start_simulation(client, trainee):
    body = {"module": "gowning", "trainee_id": 1}
    assert client.post("/api/sessions/simulate", json=body, headers=trainee).status_code == 403


def test_certificates_list(client, trainer, trainee):
    own = client.get("/api/certificates", headers=trainee).json()
    assert {c["trainee_name"] for c in own} <= {"Lukas Gruber"}
    lukas = _trainee_id(client, trainer)
    filtered = client.get(f"/api/certificates?trainee_id={lukas}", headers=trainer).json()
    assert {c["trainee_id"] for c in filtered} <= {lukas}
    assert client.get("/api/certificates/verify/unknown").status_code == 404
