from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module
from app.auth import User


main_module.user_for_session = lambda token: User(
    -1, "test-user", "test@emporos.invalid", "Test User"
)
main_module.can_access_campaign = lambda user_id, campaign_id: True

client = TestClient(app)


def test_cockpit_pages_serve():
    for path, marker in (("/", 'id="mapWrap"'), ("/market", "THE EXCHANGE"), ("/battle", "THE FIELD DESK")):
        response = client.get(path)
        assert response.status_code == 200
        assert marker in response.text


def test_registry_console_still_lives_at_command():
    response = client.get("/command")
    assert response.status_code == 200
    assert "CAMPAIGN REGISTRY" in response.text.upper() or "campaign" in response.text


def test_pulse_unknown_campaign_is_404():
    response = client.get("/api/campaigns/00000000-0000-4000-8000-000000000000/pulse")
    assert response.status_code == 404


def test_journey_cancel_requires_planning_state(monkeypatch):
    def boom(**kwargs):
        raise ValueError("Only a jump order still in planning can be stood down; this one is underway")
    monkeypatch.setattr(main_module, "cancel_jump", boom)
    response = client.post(
        "/campaigns/campaign/journeys/journey/cancel",
        data={"idempotency_key": "cancel-guard-test"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert "still in planning" in response.json()["detail"]
