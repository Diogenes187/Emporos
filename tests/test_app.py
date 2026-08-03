from fastapi.testclient import TestClient

from app.main import app


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
