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
    for path in ("/", "/crew", "/psionics", "/contacts", "/operations", "/ship", "/sector", "/trade", "/journal", "/encounters", "/library"):
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


def test_selected_campaign_dashboard_renders_live_campaign():
    campaigns=main_module.reader.campaigns()
    if not campaigns:
        return
    response=client.get(f"/?campaign={campaigns[0].public_id}")
    assert response.status_code==200
    assert campaigns[0].name in response.text
    assert "No campaign selected" not in response.text


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


def test_final_details_and_character_completion_dispatch(monkeypatch):
    details={};finished={}
    monkeypatch.setattr(main_module,"update_character_final_details",lambda **kwargs:details.update(kwargs))
    monkeypatch.setattr(main_module,"finish_character_creation",lambda **kwargs:finished.update(kwargs))
    saved=client.post("/campaigns/campaign/characters/actor/final-details",data={"character_name":"Sera Venn","gender_identity":"woman","appearance":"Weathered flight coat","personal_goals":["Find the survey vessel","","Earn command"],"idempotency_key":"details-test"},follow_redirects=False)
    completed=client.post("/campaigns/campaign/characters/actor/finish-creation",data={"idempotency_key":"finish-test"},follow_redirects=False)
    assert saved.status_code==303 and completed.status_code==303
    assert details=={"actor_public_id":"actor","character_name":"Sera Venn","gender_identity":"woman","appearance":"Weathered flight coat","personal_goals":("Find the survey vessel","Earn command"),"idempotency_key":"details-test"}
    assert finished=={"actor_public_id":"actor","idempotency_key":"finish-test"}


def test_tactical_combat_controls_dispatch(monkeypatch):
    captured={name:{} for name in ("hasten","delay","resume","forfeit","stance","cover")}
    for name,function in (("hasten","hasten_combatant"),("delay","delay_combat_turn"),("resume","resume_combat_turn"),("forfeit","forfeit_combat_turn"),("stance","change_combat_stance"),("cover","set_combat_cover")):
        monkeypatch.setattr(main_module,function,lambda _name=name,**kwargs:captured[_name].update(kwargs))
    base="/campaigns/campaign/encounters/encounter/turns/actor"
    responses=[client.post(f"{base}/{action}",data={"idempotency_key":f"{action}-test",**({"stance_code":"prone"} if action=="stance" else {"cover_code":"one_half"} if action=="cover" else {})},follow_redirects=False) for action in captured]
    assert all(response.status_code==303 for response in responses)
    for action in ("hasten","delay","resume","forfeit"):
        assert captured[action]=={"encounter_public_id":"encounter","actor_public_id":"actor","idempotency_key":f"{action}-test"}
    assert captured["stance"]["stance_code"]=="prone"
    assert captured["cover"]["cover_code"]=="one_half"


def test_advanced_action_conversion_and_kill_aim_dispatch(monkeypatch):
    spent={};aimed={}
    monkeypatch.setattr(main_module,"spend_combat_action",lambda **kwargs:spent.update(kwargs))
    monkeypatch.setattr(main_module,"aim_combatant_for_kill",lambda **kwargs:aimed.update(kwargs))
    base="/campaigns/campaign/encounters/encounter/turns/actor"
    converted=client.post(f"{base}/actions",data={"operation":"convert_significant","idempotency_key":"convert-test"},follow_redirects=False)
    kill_aimed=client.post(f"{base}/kill-aim",data={"target_actor_public_id":"target","idempotency_key":"kill-aim-test"},follow_redirects=False)
    assert converted.status_code==303 and kill_aimed.status_code==303
    assert spent=={"encounter_public_id":"encounter","actor_public_id":"actor","operation":"convert_significant","idempotency_key":"convert-test"}
    assert aimed=={"encounter_public_id":"encounter","actor_public_id":"actor","target_actor_public_id":"target","idempotency_key":"kill-aim-test"}


def test_grapple_check_and_option_dispatch(monkeypatch):
    checked={};applied={}
    monkeypatch.setattr(main_module,"resolve_combat_grapple",lambda **kwargs:checked.update(kwargs))
    monkeypatch.setattr(main_module,"apply_combat_grapple_option",lambda **kwargs:applied.update(kwargs))
    base="/campaigns/campaign/encounters/encounter/grapples"
    check=client.post(base,data={"challenger_actor_public_id":"actor","opponent_actor_public_id":"target","challenger_characteristic_rule_code":"characteristic.dexterity","opponent_characteristic_rule_code":"characteristic.strength","idempotency_key":"grapple-check"},follow_redirects=False)
    option=client.post(f"{base}/grapple/options",data={"option_code":"damage","continue_grapple":"true","displacement_metres":"0","idempotency_key":"grapple-option"},follow_redirects=False)
    assert check.status_code==303 and option.status_code==303
    assert checked["challenger_characteristic_rule_code"]=="characteristic.dexterity"
    assert checked["opponent_actor_public_id"]=="target"
    assert applied=={"grapple_public_id":"grapple","option_code":"damage","continue_grapple":True,"displacement_metres":0.0,"idempotency_key":"grapple-option"}


def test_free_coup_and_extended_action_batch_dispatch(monkeypatch):
    free={};coup={};started={};progress=[]
    monkeypatch.setattr(main_module,"perform_combat_free_action",lambda **kwargs:free.update(kwargs))
    monkeypatch.setattr(main_module,"resolve_combat_coup_de_grace",lambda **kwargs:coup.update(kwargs))
    monkeypatch.setattr(main_module,"start_combat_extended_action",lambda **kwargs:started.update(kwargs))
    monkeypatch.setattr(main_module,"progress_combat_extended_action",lambda **kwargs:progress.append(kwargs))
    base="/campaigns/campaign/encounters/encounter/turns/actor"
    responses=[client.post(f"{base}/free-actions",data={"action_reference":"Drop pack","idempotency_key":"free"},follow_redirects=False),client.post(f"{base}/coup-de-grace",data={"target_actor_public_id":"target","weapon_rule_code":"weapon","delivery_kind":"melee","idempotency_key":"coup"},follow_redirects=False),client.post(f"{base}/extended-actions/start",data={"task_reference":"Repair relay","characteristic_rule_code":"characteristic.education","skill_rule_code":"skill.electronics","time_frame_rule_code":"time-frame.1-round","idempotency_key":"start"},follow_redirects=False),client.post(f"{base}/extended-actions/advance",data={"idempotency_key":"advance"},follow_redirects=False),client.post(f"{base}/extended-actions/abandon",data={"idempotency_key":"abandon"},follow_redirects=False)]
    assert all(response.status_code==303 for response in responses)
    assert free["action_reference"]=="Drop pack" and coup["delivery_kind"]=="melee"
    assert started["task_reference"]=="Repair relay"
    assert [item["operation"] for item in progress]==["advance","abandon"]


def test_psionics_page_controls_dispatch(monkeypatch):
    activated={};recovered={};shielded={}
    monkeypatch.setattr(main_module,"activate_self_psionic_power",lambda **kwargs:activated.update(kwargs))
    monkeypatch.setattr(main_module,"recover_actor_psionic_strength",lambda **kwargs:recovered.update(kwargs))
    monkeypatch.setattr(main_module,"set_actor_telepathic_shield",lambda **kwargs:shielded.update(kwargs))
    base="/campaigns/campaign/characters/actor/psionics"
    responses=[client.post(f"{base}/activate",data={"power_rule_code":"psionics.power.enhanced-strength","variable_points":"2","idempotency_key":"activate"},follow_redirects=False),client.post(f"{base}/recover",data={"idempotency_key":"recover"},follow_redirects=False),client.post(f"{base}/shield",data={"shield_raised":"false","idempotency_key":"shield"},follow_redirects=False)]
    assert all(response.status_code==303 for response in responses)
    assert activated["variable_points"]==2
    assert recovered=={"actor_public_id":"actor","idempotency_key":"recover"}
    assert shielded=={"actor_public_id":"actor","shield_raised":False,"idempotency_key":"shield"}


def test_send_thought_dispatches_authored_content(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"send_psionic_thought",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/characters/actor/psionics/send-thought",data={"target_actor_public_id":"target","range_rule_code":"psionics.range.short","sent_thought_content":"Meet me at the airlock.","idempotency_key":"send"},follow_redirects=False)
    assert response.status_code==303
    assert captured["sent_thought_content"]=="Meet me at the airlock."
    assert captured["target_actor_public_id"]=="target"


def test_contact_operations_dispatch_structured_inputs(monkeypatch):
    streetwise={};bribery={};consequence={}
    monkeypatch.setattr(main_module,"perform_streetwise_operation",lambda **kwargs:streetwise.update(kwargs))
    monkeypatch.setattr(main_module,"attempt_bribe",lambda **kwargs:bribery.update(kwargs))
    monkeypatch.setattr(main_module,"resolve_bribe_consequence",lambda **kwargs:consequence.update(kwargs))
    base="/campaigns/campaign/contacts"
    responses=[client.post(f"{base}/streetwise",data={"actor_public_id":"actor","operation_code":"find-information","objective_reference":"Dockside routes","characteristic_rule_code":"characteristic.social-standing","difficulty_rule_code":"difficulty.average","idempotency_key":"street"},follow_redirects=False),client.post(f"{base}/bribery",data={"actor_public_id":"actor","target_reference":"customs","incident_reference":"cargo","offense_code":"minor","law_level":"8","characteristic_rule_code":"characteristic.education","offer_credits":"200","idempotency_key":"bribe"},follow_redirects=False),client.post(f"{base}/bribery/consequence",data={"actor_public_id":"actor","target_reference":"customs","incident_reference":"cargo","idempotency_key":"consequence"},follow_redirects=False)]
    assert all(response.status_code==303 for response in responses)
    assert streetwise["operation_code"]=="find-information"
    assert bribery["law_level"]==8 and bribery["offer_credits"]==200
    assert consequence["incident_reference"]=="cargo"


def test_carousing_dispatches_from_encounter(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"perform_carousing_influence",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/encounters/encounter/carousing",data={"acting_actor_public_id":"carouser","target_actor_public_id":"local","idempotency_key":"carousing"},follow_redirects=False)
    assert response.status_code==303
    assert response.headers["location"]=="/encounters?campaign=campaign"
    assert captured=={"encounter_public_id":"encounter","acting_actor_public_id":"carouser","target_actor_public_id":"local","idempotency_key":"carousing"}


def test_house_gambling_dispatches_published_terms(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"gamble_against_house",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/contacts/gambling",data={"actor_public_id":"gambler","characteristic_rule_code":"characteristic.intelligence","odds_code":"high","venue_reference":"starport casino","game_reference":"cards","bet_credits":"30","idempotency_key":"gamble"},follow_redirects=False)
    assert response.status_code==303
    assert captured["bet_credits"]==30 and captured["odds_code"]=="high"


def test_field_operations_dispatch_player_context(monkeypatch):
    recon={};survival={}
    monkeypatch.setattr(main_module,"perform_recon_operation",lambda **kwargs:recon.update(kwargs))
    monkeypatch.setattr(main_module,"perform_survival_operation",lambda **kwargs:survival.update(kwargs))
    base="/campaigns/campaign/operations"
    observed=client.post(f"{base}/recon",data={"actor_public_id":"scout","operation_code":"spot-threat","subject_reference":"ridge line","characteristic_rule_code":"characteristic.intelligence","difficulty_rule_code":"difficulty.average","idempotency_key":"recon"},follow_redirects=False)
    survived=client.post(f"{base}/survival",data={"actor_public_id":"scout","operation_code":"locate-fresh-water","objective_reference":"water before dusk","characteristic_rule_code":"characteristic.endurance","difficulty_rule_code":"difficulty.difficult","opportunity_available":"false","idempotency_key":"survival"},follow_redirects=False)
    assert observed.status_code==303 and survived.status_code==303
    assert recon["operation_code"]=="spot-threat"
    assert survival["opportunity_available"] is False


def test_ship_transport_operation_dispatches_to_ship_page(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"perform_ship_transport_operation",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/ships/ship/transport-operations",data={"actor_public_id":"pilot","operation_kind":"operate-spacecraft","operation_reference":"rough atmospheric approach","challenging_conditions":"true","characteristic_rule_code":"characteristic.dexterity","difficulty_rule_code":"difficulty.difficult","idempotency_key":"transport"},follow_redirects=False)
    assert response.status_code==303
    assert response.headers["location"]=="/ship?campaign=campaign"
    assert captured["ship_public_id"]=="ship" and captured["challenging_conditions"] is True


def test_regulatory_technical_and_leadership_operations_dispatch(monkeypatch):
    regulatory={};computer={};device={};leadership={};allocation={}
    monkeypatch.setattr(main_module,"perform_regulatory_operation",lambda **kwargs:regulatory.update(kwargs))
    monkeypatch.setattr(main_module,"perform_basic_computer_operation",lambda **kwargs:computer.update(kwargs))
    monkeypatch.setattr(main_module,"perform_device_operation",lambda **kwargs:device.update(kwargs))
    monkeypatch.setattr(main_module,"begin_leadership_coordination",lambda **kwargs:leadership.update(kwargs))
    monkeypatch.setattr(main_module,"allocate_leadership_coordination",lambda **kwargs:allocation.update(kwargs))
    responses=[client.post("/campaigns/campaign/contacts/regulatory",data={"actor_public_id":"agent","operation_selection":"pass-ship-inspection||skill.legal","case_reference":"cargo-7","authority_reference":"port customs","law_level":"8","characteristic_rule_code":"characteristic.education","illegal_material_present":"true","idempotency_key":"reg"},follow_redirects=False),client.post("/campaigns/campaign/operations/computer",data={"actor_public_id":"tech","operation_code":"access-public-data","target_reference":"port directory","idempotency_key":"computer"},follow_redirects=False),client.post("/campaigns/campaign/operations/devices",data={"actor_public_id":"tech","operation_code":"pick-electronic-lock","device_reference":"warehouse door","characteristic_rule_code":"characteristic.education","difficulty_rule_code":"difficulty.average","idempotency_key":"device"},follow_redirects=False),client.post("/campaigns/campaign/leadership",data={"leader_actor_public_id":"captain","goal_reference":"secure the ship","characteristic_rule_code":"characteristic.social-standing","idempotency_key":"lead"},follow_redirects=False),client.post("/campaigns/campaign/leadership/coord/allocations",data={"recipient_actor_public_id":"pilot","points":"2","idempotency_key":"allocate"},follow_redirects=False)]
    assert all(response.status_code==303 for response in responses)
    assert regulatory["skill_rule_code"]=="skill.legal" and regulatory["illegal_material_present"] is True
    assert computer["target_reference"]=="port directory" and device["operation_code"]=="pick-electronic-lock"
    assert leadership["leader_actor_public_id"]=="captain" and allocation["points"]==2


def test_language_and_weekly_training_dispatch(monkeypatch):
    language={};decipher={};training={}
    monkeypatch.setattr(main_module,"assign_actor_language",lambda **kwargs:language.update(kwargs))
    monkeypatch.setattr(main_module,"decipher_language_specimen",lambda **kwargs:decipher.update(kwargs))
    monkeypatch.setattr(main_module,"train_actor_skill_week",lambda **kwargs:training.update(kwargs))
    responses=[client.post("/campaigns/campaign/characters/actor/languages",data={"language_code":"vilani","proficiency_kind":"additional","idempotency_key":"language"},follow_redirects=False),client.post("/campaigns/campaign/operations/decipher-language",data={"actor_public_id":"actor","specimen_reference":"obelisk-1","specimen_medium":"inscription","characteristic_rule_code":"characteristic.education","difficulty_rule_code":"difficulty.difficult","language_code":"","idempotency_key":"decipher"},follow_redirects=False),client.post("/campaigns/campaign/characters/actor/skill-training",data={"skill_rule_code":"skill.piloting","idempotency_key":"training"},follow_redirects=False)]
    assert all(response.status_code==303 for response in responses)
    assert language["proficiency_kind"]=="additional"
    assert decipher["language_code"] is None and training["skill_rule_code"]=="skill.piloting"


def test_species_starship_encounter_and_trade_work_dispatch(monkeypatch):
    species={};encounter={};started={};completed={}
    monkeypatch.setattr(main_module,"assign_actor_species",lambda **kwargs:species.update(kwargs))
    monkeypatch.setattr(main_module,"check_for_starship_encounter",lambda **kwargs:encounter.update(kwargs))
    monkeypatch.setattr(main_module,"start_trade_work_week",lambda **kwargs:started.update(kwargs))
    monkeypatch.setattr(main_module,"complete_trade_work_week",lambda **kwargs:completed.update(kwargs))
    responses=[client.post("/campaigns/campaign/characters/actor/species",data={"species_code":"human","idempotency_key":"species"},follow_redirects=False),client.post("/campaigns/campaign/starship-encounter-checks",data={"region_context":"near_planet","target_transponder_active":"true","target_stealth_modifier":"-1","idempotency_key":"encounter"},follow_redirects=False),client.post("/campaigns/campaign/trade-work",data={"work_selection":"actor||skill.mechanics||employer||worker","idempotency_key":"work"},follow_redirects=False),client.post("/campaigns/campaign/trade-work/week/complete",data={"idempotency_key":"finish"},follow_redirects=False)]
    assert all(response.status_code==303 for response in responses)
    assert species["species_code"]=="human"
    assert encounter["region_context"]=="near_planet" and encounter["target_transponder_active"] is True
    assert started["employer_account_public_id"]=="employer" and completed["work_week_public_id"]=="week"


def test_armor_resource_usage_dispatches_from_crew(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"consume_actor_armor_resources",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/characters/actor/armor/armor/usage",data={"laser_hits":"2","life_support_seconds_used":"60","idempotency_key":"armor-use"},follow_redirects=False)
    assert response.status_code==303
    assert captured=={"actor_public_id":"actor","item_public_id":"armor","laser_hits":2,"life_support_seconds_used":60,"idempotency_key":"armor-use"}


def test_encounter_communication_support_and_species_movement_dispatch(monkeypatch):
    communication={};support={};flight={};leap={}
    monkeypatch.setattr(main_module,"set_battlefield_communication",lambda **kwargs:communication.update(kwargs))
    monkeypatch.setattr(main_module,"apply_combat_initiative_support",lambda **kwargs:support.update(kwargs))
    monkeypatch.setattr(main_module,"move_combatant_in_flight",lambda **kwargs:flight.update(kwargs))
    monkeypatch.setattr(main_module,"resolve_combatant_great_leap",lambda **kwargs:leap.update(kwargs))
    base="/campaigns/campaign/encounters/encounter"
    responses=[client.post(f"{base}/communications",data={"commander_actor_public_id":"commander","member_actor_public_id":"ally","method_code":"voice","line_of_sight":"true","member_moving":"true","idempotency_key":"comms"},follow_redirects=False),client.post(f"{base}/turns/commander/initiative-support",data={"support_code":"leadership","characteristic_rule_code":"characteristic.social_standing","target_actor_public_id":"ally","idempotency_key":"support"},follow_redirects=False),client.post(f"{base}/turns/commander/flight",data={"metres":"4.5","altitude_change_metres":"1.5","idempotency_key":"flight"},follow_redirects=False),client.post(f"{base}/turns/commander/great-leap",data={"characteristic_rule_code":"characteristic.dexterity","difficulty_rule_code":"difficulty.average","idempotency_key":"leap"},follow_redirects=False)]
    assert all(response.status_code==303 for response in responses)
    assert communication["member_moving"] is True and communication["jammed"] is False
    assert support["target_actor_public_id"]=="ally" and support["support_code"]=="leadership"
    assert flight["metres"]==4.5 and flight["altitude_change_metres"]==1.5
    assert leap["difficulty_rule_code"]=="difficulty.average"


def test_social_attitude_and_influence_dispatch(monkeypatch):
    attitude={};influence={}
    monkeypatch.setattr(main_module,"set_social_attitude",lambda **kwargs:attitude.update(kwargs))
    monkeypatch.setattr(main_module,"attempt_social_influence",lambda **kwargs:influence.update(kwargs))
    base="/campaigns/campaign/encounters/encounter"
    responses=[client.post(f"{base}/attitudes",data={"actor_public_id":"npc","attitude_code":"unfriendly","idempotency_key":"attitude"},follow_redirects=False),client.post(f"{base}/influence",data={"acting_actor_public_id":"hero","target_actor_public_id":"npc","skill_rule_code":"skill.liaison","characteristic_rule_code":"characteristic.social-standing","idempotency_key":"influence"},follow_redirects=False)]
    assert all(response.status_code==303 for response in responses)
    assert attitude["attitude_code"]=="unfriendly"
    assert influence["skill_rule_code"]=="skill.liaison" and influence["target_actor_public_id"]=="npc"


def test_animal_operations_and_reaction_dispatch(monkeypatch):
    operation={};context={};reaction={}
    monkeypatch.setattr(main_module,"perform_animal_skill_operation",lambda **kwargs:operation.update(kwargs))
    monkeypatch.setattr(main_module,"set_animal_reaction_context",lambda **kwargs:context.update(kwargs))
    monkeypatch.setattr(main_module,"resolve_animal_reaction",lambda **kwargs:reaction.update(kwargs))
    base="/campaigns/campaign"
    responses=[client.post(f"{base}/operations/animals",data={"actor_public_id":"rider","operation_code":"maneuver-riding-animal","objective_reference":"cross ravine","characteristic_rule_code":"characteristic.dexterity","difficulty_rule_code":"difficulty.average","subject_animal_public_id":"mount","idempotency_key":"ride"},follow_redirects=False),client.post(f"{base}/encounters/encounter/animal-context",data={"animal_actor_public_id":"beast","animals_outnumber_characters":"true","attack_possible":"true","idempotency_key":"context"},follow_redirects=False),client.post(f"{base}/encounters/encounter/animal-reaction",data={"animal_actor_public_id":"beast","provocation_number":"2","idempotency_key":"reaction"},follow_redirects=False)]
    assert all(response.status_code==303 for response in responses)
    assert operation["subject_animal_public_id"]=="mount" and operation["operation_code"]=="maneuver-riding-animal"
    assert context["animals_outnumber_characters"] is True and context["animal_has_surprise"] is False
    assert reaction["provocation_number"]==2


def test_environmental_exposure_dispatch(monkeypatch):
    captured={}
    monkeypatch.setattr(main_module,"advance_environmental_exposure",lambda **kwargs:captured.update(kwargs))
    response=client.post("/campaigns/campaign/characters/actor/environmental-exposure",data={"environment_kind":"extreme_cold","elapsed_minutes":"30","protective_equipment_active":"true","exposure_public_id":"exposure","end_exposure":"true","idempotency_key":"cold"},follow_redirects=False)
    assert response.status_code==303
    assert captured=={"actor_public_id":"actor","environment_kind":"extreme_cold","elapsed_minutes":30,"protective_equipment_active":True,"exposure_public_id":"exposure","end_exposure":True,"idempotency_key":"cold"}


def test_competitive_gambling_and_liaison_dispatch(monkeypatch):
    gambling={};liaison={}
    monkeypatch.setattr(main_module,"resolve_competitive_gambling",lambda **kwargs:gambling.update(kwargs))
    monkeypatch.setattr(main_module,"resolve_liaison_negotiation",lambda **kwargs:liaison.update(kwargs))
    base="/campaigns/campaign/contacts"
    common={"first_actor_public_id":"one","first_characteristic_rule_code":"characteristic.intelligence","second_actor_public_id":"two","second_characteristic_rule_code":"characteristic.social-standing"}
    gambling_data={**common,"venue_reference":"club","game_reference":"cards","pot_reference":"Cr 100","first_cheating":"true","idempotency_key":"game"}
    liaison_data={**common,"scene_reference":"embassy","subject_reference":"landing rights","idempotency_key":"talk"}
    responses=[client.post(f"{base}/competitive-gambling",data=gambling_data,follow_redirects=False),client.post(f"{base}/liaison",data=liaison_data,follow_redirects=False)]
    assert all(response.status_code==303 for response in responses)
    assert gambling["first_cheating"] is True and gambling["second_cheating"] is False
    assert liaison["scene_reference"]=="embassy" and liaison["second_actor_public_id"]=="two"


def test_condition_and_recovery_controls_dispatch(monkeypatch):
    fatigue={};rest={};recovery={};mental={}
    monkeypatch.setattr(main_module,"apply_personal_fatigue",lambda **kwargs:fatigue.update(kwargs))
    monkeypatch.setattr(main_module,"complete_personal_fatigue_rest",lambda **kwargs:rest.update(kwargs))
    monkeypatch.setattr(main_module,"resolve_personal_unconscious_recovery",lambda **kwargs:recovery.update(kwargs))
    monkeypatch.setattr(main_module,"resolve_personal_mental_healing",lambda **kwargs:mental.update(kwargs))
    base="/campaigns/campaign/characters/actor"
    responses=[client.post(f"{base}/fatigue",data={"idempotency_key":"fatigue-test"},follow_redirects=False),client.post(f"{base}/fatigue-rest",data={"completed_hours":"3.5","idempotency_key":"rest-test"},follow_redirects=False),client.post(f"{base}/consciousness-recovery",data={"minutes_elapsed":"2","idempotency_key":"wake-test"},follow_redirects=False),client.post(f"{base}/mental-healing",data={"idempotency_key":"mental-test"},follow_redirects=False)]
    assert all(response.status_code==303 for response in responses)
    assert fatigue=={"actor_public_id":"actor","idempotency_key":"fatigue-test"}
    assert rest=={"actor_public_id":"actor","completed_hours":3.5,"idempotency_key":"rest-test"}
    assert recovery=={"actor_public_id":"actor","minutes_elapsed":2,"idempotency_key":"wake-test"}
    assert mental=={"actor_public_id":"actor","idempotency_key":"mental-test"}


def test_first_aid_roll_and_allocation_dispatch(monkeypatch):
    determined={};applied={}
    monkeypatch.setattr(main_module,"determine_personal_first_aid",lambda **kwargs:determined.update(kwargs))
    monkeypatch.setattr(main_module,"apply_determined_personal_first_aid",lambda **kwargs:applied.update(kwargs))
    base="/campaigns/campaign/characters/actor/first-aid"
    rolled=client.post(f"{base}/determine",data={"doctor_actor_public_id":"doctor","damage_instance_public_id":"damage","idempotency_key":"aid-roll"},follow_redirects=False)
    restored=client.post(f"{base}/apply",data={"determination_command_public_id":"determination","strength_points":"2","dexterity_points":"0","endurance_points":"3","idempotency_key":"aid-apply"},follow_redirects=False)
    assert rolled.status_code==303 and restored.status_code==303
    assert determined=={"patient_actor_public_id":"actor","doctor_actor_public_id":"doctor","damage_instance_public_id":"damage","idempotency_key":"aid-roll"}
    assert applied=={"determination_command_public_id":"determination","strength_points":2,"dexterity_points":0,"endurance_points":3,"idempotency_key":"aid-apply"}


def test_surgery_roll_and_signed_allocation_dispatch(monkeypatch):
    determined={};applied={}
    monkeypatch.setattr(main_module,"determine_personal_surgery",lambda **kwargs:determined.update(kwargs))
    monkeypatch.setattr(main_module,"apply_determined_personal_surgery",lambda **kwargs:applied.update(kwargs))
    base="/campaigns/campaign/characters/actor/surgery"
    rolled=client.post(f"{base}/determine",data={"doctor_actor_public_id":"doctor","first_aid_command_public_id":"first-aid","medical_facility_public_id":"sickbay","idempotency_key":"surgery-roll"},follow_redirects=False)
    allocated=client.post(f"{base}/apply",data={"determination_command_public_id":"determination","strength_points":"4","dexterity_points":"0","endurance_points":"0","idempotency_key":"surgery-apply"},follow_redirects=False)
    assert rolled.status_code==303 and allocated.status_code==303
    assert determined=={"patient_actor_public_id":"actor","doctor_actor_public_id":"doctor","first_aid_command_public_id":"first-aid","medical_facility_public_id":"sickbay","idempotency_key":"surgery-roll"}
    assert applied=={"determination_command_public_id":"determination","strength_points":4,"dexterity_points":0,"endurance_points":0,"idempotency_key":"surgery-apply"}


def test_daily_medical_care_plan_and_allocation_dispatch(monkeypatch):
    planned={};applied={}
    monkeypatch.setattr(main_module,"determine_personal_medical_care",lambda **kwargs:planned.update(kwargs))
    monkeypatch.setattr(main_module,"apply_determined_personal_medical_care",lambda **kwargs:applied.update(kwargs))
    base="/campaigns/campaign/characters/actor/medical-care"
    plan=client.post(f"{base}/determine",data={"doctor_actor_public_id":"doctor","medical_facility_public_id":"hospital","idempotency_key":"care-plan"},follow_redirects=False)
    allocation=client.post(f"{base}/apply",data={"determination_command_public_id":"determination","strength_points":"2","dexterity_points":"1","endurance_points":"0","idempotency_key":"care-apply"},follow_redirects=False)
    assert plan.status_code==303 and allocation.status_code==303
    assert planned=={"patient_actor_public_id":"actor","doctor_actor_public_id":"doctor","medical_facility_public_id":"hospital","idempotency_key":"care-plan"}
    assert applied=={"determination_command_public_id":"determination","strength_points":2,"dexterity_points":1,"endurance_points":0,"idempotency_key":"care-apply"}


def test_natural_healing_result_and_allocation_dispatch(monkeypatch):
    determined={};applied={}
    monkeypatch.setattr(main_module,"determine_personal_natural_healing",lambda **kwargs:determined.update(kwargs))
    monkeypatch.setattr(main_module,"apply_determined_personal_natural_healing",lambda **kwargs:applied.update(kwargs))
    base="/campaigns/campaign/characters/actor/natural-healing"
    result=client.post(f"{base}/determine",data={"lifestyle":"full_rest","idempotency_key":"heal-roll"},follow_redirects=False)
    allocation=client.post(f"{base}/apply",data={"determination_command_public_id":"determination","strength_points":"0","dexterity_points":"2","endurance_points":"0","idempotency_key":"heal-apply"},follow_redirects=False)
    assert result.status_code==303 and allocation.status_code==303
    assert determined=={"actor_public_id":"actor","lifestyle":"full_rest","idempotency_key":"heal-roll"}
    assert applied=={"determination_command_public_id":"determination","strength_points":0,"dexterity_points":2,"endurance_points":0,"idempotency_key":"heal-apply"}
