import pytest
from starlette.websockets import WebSocketDisconnect


def _start_session(client, trainee) -> int:
    return client.post("/api/sessions", json={"module": "gowning"}, headers=trainee).json()["id"]


def _token(headers) -> str:
    return headers["Authorization"].removeprefix("Bearer ")


def test_trainer_receives_live_events(client, trainer, trainee):
    sid = _start_session(client, trainee)

    with client.websocket_connect(f"/ws/sessions/{sid}?token={_token(trainer)}") as ws:
        assert ws.receive_json()["type"] == "subscribed"

        client.post(f"/api/sessions/{sid}/events", json={"kind": "step", "step": "hand_disinfection"}, headers=trainee)
        message = ws.receive_json()
        assert message["type"] == "event"
        assert message["event"]["step"] == "hand_disinfection"

        client.post(f"/api/sessions/{sid}/finish", headers=trainee)
        finished = ws.receive_json()
        assert finished["type"] == "finished"
        assert finished["session"]["status"] == "completed"
        assert finished["session"]["passed"] is False  # most steps were skipped


@pytest.mark.parametrize("token", ["", "garbage"])
def test_websocket_requires_valid_token(client, trainee, token):
    sid = _start_session(client, trainee)
    with pytest.raises(WebSocketDisconnect), client.websocket_connect(f"/ws/sessions/{sid}?token={token}") as ws:
        ws.receive_json()


def test_websocket_respects_tenant_isolation(client, trainee, other_org_trainer):
    sid = _start_session(client, trainee)
    url = f"/ws/sessions/{sid}?token={_token(other_org_trainer)}"
    with pytest.raises(WebSocketDisconnect), client.websocket_connect(url) as ws:
        ws.receive_json()
