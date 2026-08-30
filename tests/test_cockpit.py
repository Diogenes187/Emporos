from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module
from app.auth import User
from tools.audit_template_routes import main as audit_template_routes


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


def test_external_referee_actions_have_an_honest_pending_state():
    for path in ("/", "/classic"):
        text = client.get(path).text
        assert "awaiting connected MCP referee" in text
        assert "Action queued for the connected MCP referee." in text
        assert "MCP Referee: Connected" in text
        assert "MCP Referee: Waiting" in text
        assert "MCP Referee: Offline" in text
        assert "MCP referee is offline; open or reconnect your desktop client" in text


def test_registry_console_still_lives_at_command():
    response = client.get("/command")
    assert response.status_code == 200
    assert "CAMPAIGN REGISTRY" in response.text.upper() or "campaign" in response.text


def test_cockpit_and_command_offer_the_same_setting_startup_choices():
    choices = ("ledger_reach", "generate_original", "import_own", "uncharted")
    for path in ("/", "/command"):
        text = client.get(path).text
        for choice in choices:
            assert f'value="{choice}"' in text


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


def test_every_server_rendered_post_form_matches_its_route_contract():
    assert audit_template_routes() == 0


def test_every_character_interface_keeps_completed_muster_benefits_visible():
    for path in ("/", "/classic"):
        assert "Muster benefits:" in client.get(path).text
