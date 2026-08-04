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


def test_anagathics_declaration_dispatches_player_choice(monkeypatch):
    captured = {}
    monkeypatch.setattr(main_module,"declare_career_anagathics",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/characters/actor/anagathics",data={"uses_anagathics":"true","idempotency_key":"anagathics-test"},follow_redirects=False)
    assert response.status_code==303
    assert captured=={"actor_public_id":"actor","uses_anagathics":True,"idempotency_key":"anagathics-test"}


def test_career_survival_dispatches_engine_roll(monkeypatch):
    captured = {}
    monkeypatch.setattr(main_module,"attempt_career_survival",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/characters/actor/career-survival",data={"idempotency_key":"survival-test"},follow_redirects=False)
    assert response.status_code==303
    assert response.headers["location"]=="/crew?campaign=campaign"
    assert captured=={"actor_public_id":"actor","idempotency_key":"survival-test"}


def test_career_rank_attempt_dispatches_player_decision(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"resolve_career_rank_attempt",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/characters/actor/career-rank-attempt",data={"attempt_kind":"commission","decision":"attempt","cascade_specialization":"skill.slug-pistol","idempotency_key":"commission-test"},follow_redirects=False)
    assert response.status_code==303
    assert captured=={"actor_public_id":"actor","attempt_kind":"commission","decision":"attempt","cascade_specialization":"skill.slug-pistol","idempotency_key":"commission-test"}


def test_career_term_training_dispatches_keyed_specializations(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"apply_career_term_training",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/characters/actor/career-term-training",data={"training_table_code":"service","specialization":["skill.gun-combat||skill.slug-pistol","skill.melee-combat||skill.slashing-weapons","skill.vehicle||skill.wheeled-vehicle"],"idempotency_key":"term-training-test"},follow_redirects=False)
    assert response.status_code==303
    assert captured["training_table_code"]=="service"
    assert captured["cascade_specializations"]=={"skill.gun-combat":"skill.slug-pistol","skill.melee-combat":"skill.slashing-weapons","skill.vehicle":"skill.wheeled-vehicle"}


def test_career_term_completion_dispatches_engine_command(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"complete_career_term",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/characters/actor/career-term-completion",data={"idempotency_key":"term-complete-test"},follow_redirects=False)
    assert response.status_code==303
    assert captured=={"actor_public_id":"actor","idempotency_key":"term-complete-test"}


def test_reenlistment_roll_and_choice_dispatch_engine_commands(monkeypatch):
    rolled={};decided={}
    monkeypatch.setattr(main_module,"determine_career_reenlistment",lambda **kwargs:rolled.update(kwargs))
    monkeypatch.setattr(main_module,"decide_career_reenlistment",lambda **kwargs:decided.update(kwargs))
    roll=client.post("/campaigns/campaign/characters/actor/career-reenlistment",data={"idempotency_key":"reenlist-roll-test"},follow_redirects=False)
    choice=client.post("/campaigns/campaign/characters/actor/career-reenlistment-decision",data={"decision":"continue","idempotency_key":"reenlist-choice-test"},follow_redirects=False)
    assert roll.status_code==303 and choice.status_code==303
    assert rolled=={"actor_public_id":"actor","idempotency_key":"reenlist-roll-test"}
    assert decided=={"actor_public_id":"actor","decision":"continue","idempotency_key":"reenlist-choice-test"}


def test_survival_mishap_dispatches_engine_command(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"resolve_survival_mishap",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/characters/actor/survival-mishap",data={"idempotency_key":"mishap-test"},follow_redirects=False)
    assert response.status_code==303
    assert response.headers["location"]=="/crew?campaign=campaign"
    assert captured=={"actor_public_id":"actor","idempotency_key":"mishap-test"}


def test_career_injury_determination_dispatches_player_choice(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"determine_career_injury",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/characters/actor/career-injury",data={"result_two_choice":"roll_twice_lower","idempotency_key":"injury-roll-test"},follow_redirects=False)
    assert response.status_code==303
    assert captured=={"actor_public_id":"actor","result_two_choice":"roll_twice_lower","idempotency_key":"injury-roll-test"}


def test_career_injury_application_dispatches_allocation(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"apply_career_injury",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/characters/actor/career-injury-application",data={"primary_characteristic_code":"characteristic.endurance","other_reduction_mode":"one_other_four","other_characteristic_code":"characteristic.strength","idempotency_key":"injury-apply-test"},follow_redirects=False)
    assert response.status_code==303
    assert captured["primary_characteristic_code"]=="characteristic.endurance"
    assert captured["other_reduction_mode"]=="one_other_four"
    assert captured["other_characteristic_code"]=="characteristic.strength"


def test_medical_care_dispatches_positive_restoration_points(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"resolve_career_medical_care",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/characters/actor/career-medical-care",data={"decision":"purchase","strength_points":"0","dexterity_points":"2","endurance_points":"1","idempotency_key":"medical-care-test"},follow_redirects=False)
    assert response.status_code==303
    assert captured["restoration_points"]=={"characteristic.dexterity":2,"characteristic.endurance":1}


def test_injury_crisis_cost_and_resolution_dispatch(monkeypatch):
    priced={};resolved={}
    monkeypatch.setattr(main_module,"determine_injury_crisis_cost",lambda **kwargs:priced.update(kwargs))
    monkeypatch.setattr(main_module,"resolve_injury_crisis",lambda **kwargs:resolved.update(kwargs))
    price=client.post("/campaigns/campaign/characters/actor/injury-crisis-cost",data={"idempotency_key":"crisis-cost-test"},follow_redirects=False)
    resolution=client.post("/campaigns/campaign/characters/actor/injury-crisis-resolution",data={"resolution_kind":"pay","idempotency_key":"crisis-pay-test"},follow_redirects=False)
    assert price.status_code==303 and resolution.status_code==303
    assert priced=={"actor_public_id":"actor","idempotency_key":"crisis-cost-test"}
    assert resolved=={"actor_public_id":"actor","resolution_kind":"pay","idempotency_key":"crisis-pay-test"}


def test_career_muster_and_benefit_dispatch(monkeypatch):
    initialized={};rolled={};resolved={}
    monkeypatch.setattr(main_module,"initialize_career_muster",lambda **kwargs:initialized.update(kwargs))
    monkeypatch.setattr(main_module,"roll_career_benefit",lambda **kwargs:rolled.update(kwargs))
    monkeypatch.setattr(main_module,"resolve_career_weapon_benefit",lambda **kwargs:resolved.update(kwargs))
    muster=client.post("/campaigns/campaign/characters/actor/career-muster",data={"idempotency_key":"muster-test"},follow_redirects=False)
    benefit=client.post("/campaigns/campaign/characters/actor/career-benefit",data={"benefit_table_code":"material","idempotency_key":"benefit-test"},follow_redirects=False)
    weapon=client.post("/campaigns/campaign/characters/actor/career-weapon-benefit",data={"weapon_rule_code":"equipment.weapon.auto-pistol","resolution_kind":"skill","skill_rule_code":"skill.slug-pistol","idempotency_key":"weapon-test"},follow_redirects=False)
    assert muster.status_code==303 and benefit.status_code==303 and weapon.status_code==303
    assert initialized=={"actor_public_id":"actor","idempotency_key":"muster-test"}
    assert rolled=={"actor_public_id":"actor","benefit_table_code":"material","idempotency_key":"benefit-test"}
    assert resolved=={"actor_public_id":"actor","weapon_rule_code":"equipment.weapon.auto-pistol","resolution_kind":"skill","skill_rule_code":"skill.slug-pistol","idempotency_key":"weapon-test"}


def test_career_aging_workflow_dispatch(monkeypatch):
    rolled={};applied={};priced={};resolved={}
    monkeypatch.setattr(main_module,"determine_career_aging",lambda **kwargs:rolled.update(kwargs))
    monkeypatch.setattr(main_module,"apply_career_aging",lambda **kwargs:applied.update(kwargs))
    monkeypatch.setattr(main_module,"determine_aging_crisis_cost",lambda **kwargs:priced.update(kwargs))
    monkeypatch.setattr(main_module,"resolve_aging_crisis",lambda **kwargs:resolved.update(kwargs))
    aging=client.post("/campaigns/campaign/characters/actor/career-aging",data={"aging_kind":"anagathic_stopping_shock","idempotency_key":"aging-test"},follow_redirects=False)
    allocation=client.post("/campaigns/campaign/characters/actor/career-aging-application",data={"physical_characteristic_codes":["characteristic.strength","characteristic.dexterity"],"mental_characteristic_code":"characteristic.education","idempotency_key":"aging-apply-test"},follow_redirects=False)
    cost=client.post("/campaigns/campaign/characters/actor/aging-crisis-cost",data={"idempotency_key":"aging-cost-test"},follow_redirects=False)
    resolution=client.post("/campaigns/campaign/characters/actor/aging-crisis-resolution",data={"resolution_kind":"pay","idempotency_key":"aging-pay-test"},follow_redirects=False)
    assert all(response.status_code==303 for response in (aging,allocation,cost,resolution))
    assert rolled=={"actor_public_id":"actor","aging_kind":"anagathic_stopping_shock","idempotency_key":"aging-test"}
    assert applied=={"actor_public_id":"actor","physical_characteristic_codes":("characteristic.strength","characteristic.dexterity"),"mental_characteristic_code":"characteristic.education","idempotency_key":"aging-apply-test"}
    assert priced=={"actor_public_id":"actor","idempotency_key":"aging-cost-test"}
    assert resolved=={"actor_public_id":"actor","resolution_kind":"pay","idempotency_key":"aging-pay-test"}
