from fastapi.testclient import TestClient

from app.main import app
import app.main as main_module


client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["product"] == "Emporos"
    assert response.json()["status"] in {"ok", "degraded"}


def test_campaign_api_returns_a_list():
    response = client.get("/api/campaigns")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_primary_pages_render():
    for path in ("/", "/crew", "/ship", "/sector", "/trade", "/journal", "/encounters", "/library"):
        response = client.get(path)
        assert response.status_code == 200
        assert "Emporos" in response.text


def test_library_keeps_source_review_private():
    response = client.get("/library")
    assert "Every page is accounted for" in response.text
    assert "PAGE TEXT" not in response.text


def test_unselected_dashboard_does_not_invent_a_location():
    response = client.get("/")
    assert "Select or create a campaign" in response.text
    assert "Regina Highport" not in response.text


def test_campaign_creation_form_has_stable_idempotency_key():
    response = client.get("/")
    assert 'name="idempotency_key"' in response.text
    assert 'action="/campaigns"' in response.text


def test_crew_requires_campaign_without_inventing_a_character():
    response = client.get("/crew")
    assert response.status_code == 200
    assert "Select a campaign first" in response.text
    assert "Elara Venn" not in response.text


def test_ship_requires_campaign_and_has_no_decorative_vessel():
    response=client.get("/ship")
    assert response.status_code == 200
    assert "Select a campaign first" in response.text
    assert "Far Horizon" not in response.text


def test_sector_requires_campaign_without_a_decorative_chart():
    response=client.get("/sector")
    assert response.status_code == 200
    assert "Select a campaign first" in response.text
    assert "Regina" not in response.text


def test_arrival_redirect_selects_committed_destination(monkeypatch):
    monkeypatch.setattr(main_module,"run_jump",lambda **kwargs:(object(),"destination-system"))
    response=client.post("/campaigns/campaign/journeys/journey/arrive",data={"idempotency_key":"arrival-test"},follow_redirects=False)
    assert response.status_code==303
    assert response.headers["location"]=="/sector?campaign=campaign&system=destination-system"


def test_equipment_purchase_dispatches_and_returns_to_crew(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        main_module,
        "purchase_personal_equipment",
        lambda **kwargs: captured.update(kwargs),
    )
    response = client.post(
        "/campaigns/campaign/equipment-purchases",
        data={
            "actor_public_id": "actor",
            "item_rule_code": "equipment.weapon.blade",
            "idempotency_key": "equipment-test",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/crew?campaign=campaign"
    assert captured["campaign_public_id"] == "campaign"
    assert captured["item_rule_code"] == "equipment.weapon.blade"


def test_ammunition_purchase_dispatches_and_returns_to_crew(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        main_module,
        "purchase_personal_ammunition",
        lambda **kwargs: captured.update(kwargs),
    )
    response = client.post(
        "/campaigns/campaign/ammunition-purchases",
        data={
            "actor_public_id": "actor",
            "ammunition_rule_code": "equipment.ammunition.auto-pistol.standard",
            "reload_units": "3",
            "idempotency_key": "ammunition-test",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/crew?campaign=campaign"
    assert captured["reload_units"] == 3


def test_career_entry_dispatches_selected_career_and_assignment(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        main_module,
        "attempt_career_entry",
        lambda **kwargs: captured.update(kwargs),
    )
    response = client.post(
        "/campaigns/campaign/characters/actor/career-entry",
        data={
            "career_selection": "navy||flight",
            "idempotency_key": "career-entry-test",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/crew?campaign=campaign"
    assert captured == {
        "actor_public_id": "actor",
        "career_code": "navy",
        "assignment_code": "flight",
        "idempotency_key": "career-entry-test",
    }


def test_failed_career_entry_fallback_dispatches_and_returns_to_crew(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        main_module,
        "resolve_career_entry_failure",
        lambda **kwargs: captured.update(kwargs),
    )
    response = client.post(
        "/campaigns/campaign/career-entry-fallbacks",
        data={
            "attempt_command_public_id": "attempt-command",
            "fallback_kind": "draft",
            "idempotency_key": "career-fallback-test",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/crew?campaign=campaign"
    assert captured == {
        "attempt_command_public_id": "attempt-command",
        "fallback_kind": "draft",
        "idempotency_key": "career-fallback-test",
    }


def test_basic_training_dispatches_specializations_and_returns_to_crew(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        main_module,
        "apply_career_basic_training",
        lambda **kwargs: captured.update(kwargs),
    )
    response = client.post(
        "/campaigns/campaign/characters/actor/basic-training",
        data={
            "specialization": [
                "skill.gun-combat||skill.slug-pistol",
                "skill.vehicle||skill.wheeled-vehicle",
            ],
            "idempotency_key": "basic-training-test",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/crew?campaign=campaign"
    assert captured == {
        "actor_public_id": "actor",
        "selected_roll_value": None,
        "cascade_specializations": {
            "skill.gun-combat": "skill.slug-pistol",
            "skill.vehicle": "skill.wheeled-vehicle",
        },
        "idempotency_key": "basic-training-test",
    }


def test_later_career_basic_training_dispatches_selected_service_result(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        main_module,
        "apply_career_basic_training",
        lambda **kwargs: captured.update(kwargs),
    )
    response = client.post(
        "/campaigns/campaign/characters/actor/basic-training",
        data={
            "selected_roll_value": "4",
            "idempotency_key": "later-basic-training-test",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert captured["selected_roll_value"] == 4
    assert captured["cascade_specializations"] == {}


def test_rank_zero_award_dispatches_specialization_and_returns_to_crew(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        main_module,
        "apply_career_rank_zero_award",
        lambda **kwargs: captured.update(kwargs),
    )
    response = client.post(
        "/campaigns/campaign/characters/actor/rank-zero-award",
        data={
            "cascade_specialization": "skill.slug-pistol",
            "idempotency_key": "rank-zero-test",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/crew?campaign=campaign"
    assert captured == {
        "actor_public_id": "actor",
        "cascade_specialization": "skill.slug-pistol",
        "idempotency_key": "rank-zero-test",
    }
