from pathlib import Path
import re
import uuid

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import CampaignReader, summary_dict
from app.auth import (SESSION_COOKIE, accept_invitation, authenticate,
                      campaign_role, can_access_campaign, create_invitation,
                      create_session, grant_campaign_owner,
                      numeric_resources_belong_to_campaign, register,
                      resources_belong_to_campaign, revoke_session,
                      secure_cookie, user_for_session,local_mode,local_user)
from app.commands import acquire_ship, create_campaign, import_sector, initialize_character, place_ship, plan_jump, plot_jump, resolve_jump, run_jump, open_market, roll_purchase_price, prepare_trading, purchase_goods, roll_sale_price, sell_goods, refuel_ship, pay_ship_expense, assign_ship_crew, add_campaign_note, archive_play_session, pay_ship_crew, open_route_revenue, accept_freight_contract, deliver_freight_contract, book_route_passengers, board_route_passengers, revive_low_passenger, finalize_passenger_manifest, accept_postal_contract, deliver_postal_contract, quote_starship_charter, accept_starship_charter, complete_starship_charter, open_ship_mortgage, pay_ship_mortgage, ingest_campaign_source, review_campaign_source, send_referee_message, confirm_referee_action, create_encounter, add_encounter_participant, begin_personal_combat, initialize_personal_combat, begin_combat_turn, move_combatant, aim_combatant, complete_combat_turn, advance_combat_round, ready_combat_weapon, reload_combat_weapon, declare_combat_attack, resolve_combat_attack, apply_combat_damage, react_to_combat_attack, end_personal_combat, equip_actor_armor, unequip_actor_armor, purchase_personal_equipment, purchase_personal_ammunition, attempt_career_entry, resolve_career_entry_failure, apply_career_basic_training, apply_career_rank_zero_award, declare_career_anagathics, attempt_career_survival, resolve_career_rank_attempt, apply_career_term_training, complete_career_term, determine_career_reenlistment, decide_career_reenlistment, resolve_survival_mishap, determine_career_injury, apply_career_injury, resolve_career_medical_care, determine_injury_crisis_cost, resolve_injury_crisis, initialize_career_muster, roll_career_benefit, resolve_career_weapon_benefit, determine_career_aging, apply_career_aging, determine_aging_crisis_cost, resolve_aging_crisis, update_character_final_details, finish_character_creation, hasten_combatant, delay_combat_turn, resume_combat_turn, forfeit_combat_turn, change_combat_stance, set_combat_cover, apply_personal_fatigue, complete_personal_fatigue_rest, resolve_personal_unconscious_recovery, resolve_personal_mental_healing, determine_personal_first_aid, apply_determined_personal_first_aid, determine_personal_surgery, apply_determined_personal_surgery, determine_personal_medical_care, apply_determined_personal_medical_care, determine_personal_natural_healing, apply_determined_personal_natural_healing, spend_combat_action, aim_combatant_for_kill, resolve_combat_grapple, apply_combat_grapple_option, perform_combat_free_action, resolve_combat_coup_de_grace, start_combat_extended_action, progress_combat_extended_action, activate_self_psionic_power, recover_actor_psionic_strength, set_actor_telepathic_shield, send_psionic_thought, perform_streetwise_operation, attempt_bribe, resolve_bribe_consequence, perform_carousing_influence, gamble_against_house, perform_recon_operation, perform_survival_operation, perform_ship_transport_operation, perform_regulatory_operation, perform_basic_computer_operation, perform_device_operation, begin_leadership_coordination, allocate_leadership_coordination, assign_actor_language, decipher_language_specimen, train_actor_skill_week, assign_actor_species, check_for_starship_encounter, start_trade_work_week, complete_trade_work_week, consume_actor_armor_resources, set_battlefield_communication, apply_combat_initiative_support, move_combatant_in_flight, resolve_combatant_great_leap, set_social_attitude, attempt_social_influence, perform_animal_skill_operation, set_animal_reaction_context, resolve_animal_reaction, advance_environmental_exposure, resolve_competitive_gambling, resolve_liaison_negotiation, resolve_steward_service, set_battlefield_conditions, declare_combat_explosion, react_to_combat_explosion, resolve_combat_explosion, create_scene_snapshot, resolve_species_hive_mentality, resolve_species_naturally_curious, evaluate_species_low_light, resolve_ground_starship_volley, finalize_ground_starship_volley
from app.commands import select_social_content,create_patron_brief,authorize_extreme_range
from app.commands import cancel_jump
from app.commands import reroll_characteristics, arrange_characteristics, abandon_unfinished_character, delete_character
from app.commands import record_human_narration, request_gm_assistance
from app.commands import adventure_modules,create_adventure_module,key_adventure_location,enter_adventure_location,update_adventure_location_state,advance_adventure_exploration
from app.commands import begin_adventure_indexing,review_adventure_location_proposal


ROOT = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=ROOT / "app" / "templates")

app = FastAPI(title="Emporos", version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
app.mount(
    "/logos",
    StaticFiles(directory=ROOT / "logos", check_dir=False),
    name="logos",
)

from .classic import router as classic_router  # noqa: E402
from .cockpit import router as cockpit_router  # noqa: E402

app.include_router(classic_router)
app.include_router(cockpit_router)

PUBLIC_PATHS = {"/health", "/login", "/register"}
CAMPAIGN_PATH = re.compile(r"^/(?:api/)?campaigns/([^/]+)")
PUBLIC_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
    r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)
NUMERIC_PATH_RESOURCES = (
    (re.compile(r"/markets/(\d+)(?:/|$)"), "market_session_id"),
)


@app.middleware("http")
async def require_account_and_campaign_access(request: Request, call_next):
    path = request.url.path
    if path in PUBLIC_PATHS or path.startswith("/static/") or path.startswith("/logos/"):
        return await call_next(request)
    client_host = request.client.host if request.client else ""
    loopback = client_host in ("127.0.0.1", "::1", "localhost", "testclient")
    user = local_user() if local_mode() and loopback else user_for_session(
        request.cookies.get(SESSION_COOKIE)
    )
    if user is None:
        if path.startswith("/api/"):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        destination = path + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse(url=f"/login?next={destination}", status_code=303)
    request.state.user = user
    match = CAMPAIGN_PATH.match(path)
    campaign_id = match.group(1) if match else request.query_params.get("campaign")
    if campaign_id and not can_access_campaign(user.user_id, campaign_id):
        return JSONResponse({"detail": "Campaign not found"}, status_code=404)
    if campaign_id and PUBLIC_UUID.fullmatch(campaign_id):
        submitted = set(segment for segment in path.split("/") if PUBLIC_UUID.fullmatch(segment))
        numeric_submitted: dict[str, set[int]] = {}
        submitted.update(value for _, value in request.query_params.multi_items()
                         if PUBLIC_UUID.fullmatch(value))
        for key, value in request.query_params.multi_items():
            if value.isdecimal():
                numeric_submitted.setdefault(key, set()).add(int(value))
        if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded"):
            # Cache the bytes before parsing. Function middleware otherwise
            # consumes the form stream and downstream FastAPI handlers receive
            # an empty body.
            await request.body()
            form = await request.form()
            submitted.update(str(value) for _, value in form.multi_items()
                             if PUBLIC_UUID.fullmatch(str(value)))
            for key, value in form.multi_items():
                text = str(value)
                if text.isdecimal():
                    numeric_submitted.setdefault(key, set()).add(int(text))
        for pattern, key in NUMERIC_PATH_RESOURCES:
            path_match = pattern.search(path)
            if path_match:
                numeric_submitted.setdefault(key, set()).add(int(path_match.group(1)))
        submitted.discard(campaign_id)
        if not resources_belong_to_campaign(campaign_id, submitted):
            return JSONResponse({"detail": "Campaign resource not found"}, status_code=404)
        if not numeric_resources_belong_to_campaign(campaign_id, numeric_submitted):
            return JSONResponse({"detail": "Campaign resource not found"}, status_code=404)
    return await call_next(request)


NAVIGATION = (
    ("dashboard", "Command"),
    ("character-creation", "Character Creation"),
    ("crew", "Crew"),
    ("psionics", "Psionics"),
    ("ship", "Ship"),
    ("sector", "Sector"),
    ("trade", "Trade"),
    ("contacts", "Contacts"),
    ("operations", "Operations"),
    ("encounters", "Encounters"),
    ("journal", "Journal"),
    ("library", "Library"),
    ("info", "Information"),
)


PAGE_COPY = {
    "crew": ("Crew manifest", "Characters, assignments, health, skills, and relationships."),
    "ship": ("Ship operations", "Systems, fuel, cargo, maintenance, damage, and crew stations."),
    "trade": ("Exchange", "Held markets, freight, passengers, cargo, and audited transactions."),
    "encounters": ("Encounters", "Persistent participants, intentions, rounds, injuries, and outcomes."),
}

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/psionics/activate")
def psionic_activate(campaign_id:str,actor_id:str,power_rule_code:str=Form(...),variable_points:int=Form(0),idempotency_key:str=Form(...)):
    try:activate_self_psionic_power(actor_public_id=actor_id,power_rule_code=power_rule_code,variable_points=variable_points,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/psionics?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/psionics/recover")
def psionic_recover(campaign_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:recover_actor_psionic_strength(actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/psionics?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/psionics/shield")
def psionic_shield(campaign_id:str,actor_id:str,shield_raised:bool=Form(...),idempotency_key:str=Form(...)):
    try:set_actor_telepathic_shield(actor_public_id=actor_id,shield_raised=shield_raised,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/psionics?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/psionics/send-thought")
def psionic_send_thought(campaign_id:str,actor_id:str,target_actor_public_id:str=Form(...),range_rule_code:str=Form(...),sent_thought_content:str=Form(...),idempotency_key:str=Form(...)):
    try:send_psionic_thought(actor_public_id=actor_id,target_actor_public_id=target_actor_public_id,range_rule_code=range_rule_code,sent_thought_content=sent_thought_content,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/psionics?campaign={campaign_id}",status_code=303)

reader = CampaignReader()

@app.post("/campaigns/{campaign_id}/contacts/streetwise")
def contact_streetwise(campaign_id:str,actor_public_id:str=Form(...),operation_code:str=Form(...),objective_reference:str=Form(...),characteristic_rule_code:str=Form(...),difficulty_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:perform_streetwise_operation(actor_public_id=actor_public_id,operation_code=operation_code,objective_reference=objective_reference,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/contacts?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/contacts/bribery")
def contact_bribery(campaign_id:str,actor_public_id:str=Form(...),target_reference:str=Form(...),incident_reference:str=Form(...),offense_code:str=Form(...),law_level:int=Form(...),characteristic_rule_code:str=Form(...),offer_credits:int=Form(...),idempotency_key:str=Form(...)):
    try:attempt_bribe(actor_public_id=actor_public_id,target_reference=target_reference,incident_reference=incident_reference,offense_code=offense_code,law_level=law_level,characteristic_rule_code=characteristic_rule_code,offer_credits=offer_credits,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/contacts?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/contacts/bribery/consequence")
def contact_bribery_consequence(campaign_id:str,actor_public_id:str=Form(...),target_reference:str=Form(...),incident_reference:str=Form(...),idempotency_key:str=Form(...)):
    try:resolve_bribe_consequence(actor_public_id=actor_public_id,target_reference=target_reference,incident_reference=incident_reference,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/contacts?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/carousing")
def encounter_carousing(campaign_id:str,encounter_id:str,acting_actor_public_id:str=Form(...),target_actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:perform_carousing_influence(encounter_public_id=encounter_id,acting_actor_public_id=acting_actor_public_id,target_actor_public_id=target_actor_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/social-content")
def encounter_social_content(campaign_id:str,encounter_id:str,idempotency_key:str=Form(...)):
    try:select_social_content(encounter_public_id=encounter_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/patron-briefs")
def patron_brief_create(campaign_id:str,brief_code:str=Form(...),patron_name_reference:str=Form(...),role_reference:str=Form(...),reward_summary:str=Form(...),player_mission_summary:str=Form(...),requirement_reference:str=Form(...),truth_one:str=Form(...),truth_two:str=Form(...),objective_actor_role:str=Form(...),objective_kind:str=Form(...),objective_reference:str=Form(...),objective_priority:int=Form(...),idempotency_key:str=Form(...)):
    try:create_patron_brief(campaign_public_id=campaign_id,brief_code=brief_code,patron_name_reference=patron_name_reference,role_reference=role_reference,reward_summary=reward_summary,player_mission_summary=player_mission_summary,requirement_reference=requirement_reference,truth_one=truth_one,truth_two=truth_two,objective_actor_role=objective_actor_role,objective_kind=objective_kind,objective_reference=objective_reference,objective_priority=objective_priority,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/contacts?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/attitudes")
def encounter_attitude(campaign_id:str,encounter_id:str,actor_public_id:str=Form(...),attitude_code:str=Form(...),idempotency_key:str=Form(...)):
    try:set_social_attitude(encounter_public_id=encounter_id,actor_public_id=actor_public_id,attitude_code=attitude_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/influence")
def encounter_influence(campaign_id:str,encounter_id:str,acting_actor_public_id:str=Form(...),target_actor_public_id:str=Form(...),skill_rule_code:str=Form(...),characteristic_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:attempt_social_influence(encounter_public_id=encounter_id,acting_actor_public_id=acting_actor_public_id,target_actor_public_id=target_actor_public_id,skill_rule_code=skill_rule_code,characteristic_rule_code=characteristic_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/contacts/gambling")
def contact_gambling(campaign_id:str,actor_public_id:str=Form(...),characteristic_rule_code:str=Form(...),odds_code:str=Form(...),venue_reference:str=Form(...),game_reference:str=Form(...),bet_credits:int=Form(...),idempotency_key:str=Form(...)):
    try:gamble_against_house(actor_public_id=actor_public_id,characteristic_rule_code=characteristic_rule_code,odds_code=odds_code,venue_reference=venue_reference,game_reference=game_reference,bet_credits=bet_credits,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/contacts?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/contacts/competitive-gambling")
def contact_competitive_gambling(campaign_id:str,venue_reference:str=Form(...),game_reference:str=Form(...),pot_reference:str=Form(...),first_actor_public_id:str=Form(...),first_characteristic_rule_code:str=Form(...),first_cheating:bool=Form(False),second_actor_public_id:str=Form(...),second_characteristic_rule_code:str=Form(...),second_cheating:bool=Form(False),idempotency_key:str=Form(...)):
    try:resolve_competitive_gambling(venue_reference=venue_reference,game_reference=game_reference,pot_reference=pot_reference,first_actor_public_id=first_actor_public_id,first_characteristic_rule_code=first_characteristic_rule_code,first_cheating=first_cheating,second_actor_public_id=second_actor_public_id,second_characteristic_rule_code=second_characteristic_rule_code,second_cheating=second_cheating,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/contacts?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/contacts/liaison")
def contact_liaison(campaign_id:str,scene_reference:str=Form(...),subject_reference:str=Form(...),first_actor_public_id:str=Form(...),first_characteristic_rule_code:str=Form(...),second_actor_public_id:str=Form(...),second_characteristic_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:resolve_liaison_negotiation(scene_reference=scene_reference,subject_reference=subject_reference,first_actor_public_id=first_actor_public_id,first_characteristic_rule_code=first_characteristic_rule_code,second_actor_public_id=second_actor_public_id,second_characteristic_rule_code=second_characteristic_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/contacts?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/contacts/regulatory")
def contact_regulatory(campaign_id:str,actor_public_id:str=Form(...),operation_selection:str=Form(...),case_reference:str=Form(...),authority_reference:str=Form(...),law_level:int=Form(...),characteristic_rule_code:str=Form(...),illegal_material_present:bool=Form(False),idempotency_key:str=Form(...)):
    operation_code,skill_rule_code=operation_selection.split("||",1)
    try:perform_regulatory_operation(actor_public_id=actor_public_id,operation_code=operation_code,skill_rule_code=skill_rule_code,case_reference=case_reference,authority_reference=authority_reference,law_level=law_level,characteristic_rule_code=characteristic_rule_code,illegal_material_present=illegal_material_present,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/contacts?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/operations/recon")
def operation_recon(campaign_id:str,actor_public_id:str=Form(...),operation_code:str=Form(...),subject_reference:str=Form(...),characteristic_rule_code:str=Form(...),difficulty_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:perform_recon_operation(actor_public_id=actor_public_id,operation_code=operation_code,subject_reference=subject_reference,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/operations?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/operations/survival")
def operation_survival(campaign_id:str,actor_public_id:str=Form(...),operation_code:str=Form(...),objective_reference:str=Form(...),characteristic_rule_code:str=Form(...),difficulty_rule_code:str=Form(...),opportunity_available:bool=Form(False),idempotency_key:str=Form(...)):
    try:perform_survival_operation(actor_public_id=actor_public_id,operation_code=operation_code,objective_reference=objective_reference,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code,opportunity_available=opportunity_available,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/operations?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/operations/animals")
def animal_skill_operation(campaign_id:str,actor_public_id:str=Form(...),operation_code:str=Form(...),objective_reference:str=Form(...),characteristic_rule_code:str=Form(...),difficulty_rule_code:str=Form(...),subject_animal_public_id:str=Form(""),idempotency_key:str=Form(...)):
    try:perform_animal_skill_operation(actor_public_id=actor_public_id,operation_code=operation_code,objective_reference=objective_reference,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code,subject_animal_public_id=subject_animal_public_id or None,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/operations?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/operations/species/hive-mentality")
def species_hive_mentality(campaign_id:str,actor_public_id:str=Form(...),family_group_reference:str=Form(...),perceived_benefit:str=Form(...),difficulty_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:resolve_species_hive_mentality(actor_public_id=actor_public_id,family_group_reference=family_group_reference,perceived_benefit=perceived_benefit,difficulty_rule_code=difficulty_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/operations?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/operations/species/naturally-curious")
def species_naturally_curious(campaign_id:str,actor_public_id:str=Form(...),mystery_reference:str=Form(...),perceived_mystery:str=Form(...),difficulty_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:resolve_species_naturally_curious(actor_public_id=actor_public_id,mystery_reference=mystery_reference,perceived_mystery=perceived_mystery,difficulty_rule_code=difficulty_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/operations?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/operations/species/low-light")
def species_low_light(campaign_id:str,actor_public_id:str=Form(...),illumination_context:str=Form(...),human_visibility_metres:float=Form(...),idempotency_key:str=Form(...)):
    try:evaluate_species_low_light(actor_public_id=actor_public_id,illumination_context=illumination_context,human_visibility_metres=human_visibility_metres,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/operations?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/ground-starship-volleys")
def ground_starship_volley(campaign_id:str,target_ship_public_id:str=Form(...),target_range_code:str=Form(...),battery_public_id:str=Form(...),battery_quantity:int=Form(...),idempotency_key:str=Form(...)):
    try:resolve_ground_starship_volley(target_ship_public_id=target_ship_public_id,target_range_code=target_range_code,battery_public_id=battery_public_id,battery_quantity=battery_quantity,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/ship?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/ground-starship-volleys/finalize")
def ground_starship_volley_finalize(campaign_id:str,volley_command_public_id:str=Form(...),primary_attack_order:int=Form(...),idempotency_key:str=Form(...)):
    try:finalize_ground_starship_volley(volley_command_public_id=volley_command_public_id,primary_attack_order=primary_attack_order,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/ship?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/animal-context")
def animal_reaction_context(campaign_id:str,encounter_id:str,animal_actor_public_id:str=Form(...),animals_outnumber_characters:bool=Form(False),animal_has_surprise:bool=Form(False),animal_is_surprised:bool=Form(False),animal_bigger_than_character:bool=Form(False),attack_possible:bool=Form(False),idempotency_key:str=Form(...)):
    try:set_animal_reaction_context(encounter_public_id=encounter_id,animal_actor_public_id=animal_actor_public_id,animals_outnumber_characters=animals_outnumber_characters,animal_has_surprise=animal_has_surprise,animal_is_surprised=animal_is_surprised,animal_bigger_than_character=animal_bigger_than_character,attack_possible=attack_possible,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/animal-reaction")
def animal_reaction(campaign_id:str,encounter_id:str,animal_actor_public_id:str=Form(...),provocation_number:int=Form(...),idempotency_key:str=Form(...)):
    try:resolve_animal_reaction(encounter_public_id=encounter_id,animal_actor_public_id=animal_actor_public_id,provocation_number=provocation_number,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/operations/computer")
def operation_computer(campaign_id:str,actor_public_id:str=Form(...),operation_code:str=Form(...),target_reference:str=Form(...),idempotency_key:str=Form(...)):
    try:perform_basic_computer_operation(actor_public_id=actor_public_id,operation_code=operation_code,target_reference=target_reference,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/operations?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/operations/devices")
def operation_device(campaign_id:str,actor_public_id:str=Form(...),operation_code:str=Form(...),device_reference:str=Form(...),characteristic_rule_code:str=Form(...),difficulty_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:perform_device_operation(actor_public_id=actor_public_id,operation_code=operation_code,device_reference=device_reference,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/operations?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/leadership")
def leadership_begin(campaign_id:str,leader_actor_public_id:str=Form(...),goal_reference:str=Form(...),characteristic_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:begin_leadership_coordination(leader_actor_public_id=leader_actor_public_id,goal_reference=goal_reference,characteristic_rule_code=characteristic_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/leadership/{coordination_id}/allocations")
def leadership_allocate(campaign_id:str,coordination_id:str,recipient_actor_public_id:str=Form(...),points:int=Form(...),idempotency_key:str=Form(...)):
    try:allocate_leadership_coordination(coordination_public_id=coordination_id,recipient_actor_public_id=recipient_actor_public_id,points=points,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/languages")
def character_language_assign(campaign_id:str,actor_id:str,language_code:str=Form(...),proficiency_kind:str=Form(...),idempotency_key:str=Form(...)):
    try:assign_actor_language(actor_public_id=actor_id,language_code=language_code,proficiency_kind=proficiency_kind,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/skill-training")
def character_skill_training(campaign_id:str,actor_id:str,skill_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:train_actor_skill_week(actor_public_id=actor_id,skill_rule_code=skill_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/species")
def character_species_assign(campaign_id:str,actor_id:str,species_code:str=Form(...),idempotency_key:str=Form(...)):
    try:assign_actor_species(actor_public_id=actor_id,species_code=species_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/starship-encounter-checks")
def starship_encounter_check(campaign_id:str,region_context:str=Form(...),target_transponder_active:bool=Form(False),target_stealth_modifier:int=Form(0),idempotency_key:str=Form(...)):
    try:check_for_starship_encounter(campaign_public_id=campaign_id,region_context=region_context,target_transponder_active=target_transponder_active,target_stealth_modifier=target_stealth_modifier,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/sector?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/trade-work")
def trade_work_start(campaign_id:str,work_selection:str=Form(...),idempotency_key:str=Form(...)):
    actor_public_id,skill_rule_code,employer_account_public_id,worker_account_public_id=work_selection.split("||",3)
    try:start_trade_work_week(actor_public_id=actor_public_id,skill_rule_code=skill_rule_code,employer_account_public_id=employer_account_public_id,worker_account_public_id=worker_account_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/trade-work/{work_week_id}/complete")
def trade_work_complete(campaign_id:str,work_week_id:str,idempotency_key:str=Form(...)):
    try:complete_trade_work_week(work_week_public_id=work_week_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/operations/decipher-language")
def operation_decipher_language(campaign_id:str,actor_public_id:str=Form(...),specimen_reference:str=Form(...),specimen_medium:str=Form(...),characteristic_rule_code:str=Form(...),difficulty_rule_code:str=Form(...),language_code:str=Form(""),idempotency_key:str=Form(...)):
    try:decipher_language_specimen(actor_public_id=actor_public_id,specimen_reference=specimen_reference,specimen_medium=specimen_medium,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code,language_code=language_code or None,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/operations?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/ships/{ship_id}/transport-operations")
def ship_transport_operation(campaign_id:str,ship_id:str,actor_public_id:str=Form(...),operation_kind:str=Form(...),operation_reference:str=Form(...),challenging_conditions:bool=Form(False),characteristic_rule_code:str=Form(...),difficulty_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:perform_ship_transport_operation(actor_public_id=actor_public_id,ship_public_id=ship_id,operation_kind=operation_kind,operation_reference=operation_reference,challenging_conditions=challenging_conditions,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/ship?campaign={campaign_id}",status_code=303)


def selected_campaign(campaign_id: str | None):
    return reader.campaign(campaign_id) if campaign_id else None


def page_context(request: Request, active: str, campaign=None, **values):
    return {
        "request": request,
        "navigation": NAVIGATION,
        "active": active,
        "campaign": campaign,
        "current_user": getattr(request.state, "user", None),
        "campaign_role": (campaign_role(request.state.user.user_id, campaign["public_id"])
                          if campaign and getattr(request.state, "user", None) else None),
        "campaign_query": (
            f"?campaign={campaign['public_id']}" if campaign else ""
        ),
        **values,
    }


@app.get("/health")
def health():
    database = reader.status()
    return {
        "status": "ok" if database.get("connected") else "degraded",
        "product": "Emporos",
        "local_mode": local_mode(),
        "authentication_required": not local_mode(),
        "database": database,
    }


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str = "/"):
    return templates.TemplateResponse(request=request, name="login.html", context={
        "request": request, "next": next, "mode": "login", "error": None,
    })


@app.post("/login")
def login_submit(request: Request, email: str = Form(...), password: str = Form(...), next: str = Form("/")):
    user = authenticate(email, password)
    if user is None:
        return templates.TemplateResponse(request=request, name="login.html", context={
            "request": request, "next": next, "mode": "login",
            "error": "Email or password was not recognized.",
        }, status_code=400)
    destination = next if next.startswith("/") and not next.startswith("//") else "/"
    response = RedirectResponse(destination, status_code=303)
    response.set_cookie(SESSION_COOKIE, create_session(user.user_id), httponly=True,
                        secure=secure_cookie(), samesite="lax", max_age=30*24*60*60)
    return response


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={
        "request": request, "next": "/", "mode": "register", "error": None,
    })


@app.post("/register")
def register_submit(request: Request, email: str = Form(...), display_name: str = Form(...), password: str = Form(...)):
    try:
        user = register(email, display_name, password)
    except ValueError as exc:
        return templates.TemplateResponse(request=request, name="login.html", context={
            "request": request, "next": "/", "mode": "register", "error": str(exc),
        }, status_code=400)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(SESSION_COOKIE, create_session(user.user_id), httponly=True,
                        secure=secure_cookie(), samesite="lax", max_age=30*24*60*60)
    return response


@app.post("/logout")
def logout(request: Request):
    revoke_session(request.cookies.get(SESSION_COOKIE))
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.post("/campaigns/{campaign_id}/invitations")
def invitation_create(request: Request, campaign_id: str, email: str = Form(...)):
    try:
        token = create_invitation(campaign_id, request.state.user.user_id, email)
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/?campaign={campaign_id}&invite_created={token}", status_code=303)


@app.get("/join/{token}")
def invitation_accept(request: Request, token: str):
    try:
        campaign_id = accept_invitation(token, request.state.user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/?campaign={campaign_id}", status_code=303)


@app.get("/api/campaigns")
def campaign_list(request: Request):
    return [summary_dict(item) for item in reader.campaigns(user_id=request.state.user.user_id)]


@app.get("/api/campaigns/{campaign_id}")
def campaign_overview(campaign_id: str):
    campaign = reader.campaign(campaign_id)
    if campaign is None:
        return {"detail": "Campaign not found"}
    return campaign


@app.post("/campaigns")
def campaign_create(
    request: Request,
    name: str = Form(...),
    play_mode: str = Form("ai_refereed"),
    setting_choice: str = Form("ledger_reach"),
    idempotency_key: str = Form(...),
):
    result = create_campaign(
        name=name,
        play_mode=play_mode,
        setting_choice=setting_choice,
        idempotency_key=idempotency_key,
    )
    grant_campaign_owner(result.campaign_public_id, request.state.user.user_id)
    return RedirectResponse(
        url=f"/?campaign={result.campaign_public_id}", status_code=303
    )


@app.post("/campaigns/{campaign_id}/characters")
def character_initialize(
    campaign_id: str,
    idempotency_key: str = Form(""),
):
    command_key = idempotency_key.strip() or str(uuid.uuid4())
    try:
        initialize_character(
            campaign_public_id=campaign_id,
            idempotency_key=command_key,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403,detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(
        url=f"/character-creation?campaign={campaign_id}", status_code=303
    )


@app.post("/campaigns/{campaign_id}/characters/{actor_id}/reroll-characteristics")
def character_reroll(campaign_id: str, actor_id: str,
                     idempotency_key: str = Form("")):
    try:
        reroll_characteristics(
            actor_public_id=actor_id,
            idempotency_key=idempotency_key.strip() or str(uuid.uuid4()),
        )
    except (ValueError, PermissionError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/character-creation?campaign={campaign_id}", status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/arrange-characteristics")
def character_arrange(campaign_id:str,actor_id:str,source_characteristic_codes:list[str]=Form(...),idempotency_key:str=Form("")):
    try:arrange_characteristics(actor_public_id=actor_id,source_characteristic_codes=tuple(source_characteristic_codes),idempotency_key=idempotency_key.strip() or str(uuid.uuid4()))
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/character-creation?campaign={campaign_id}",status_code=303)


@app.post("/campaigns/{campaign_id}/characters/{actor_id}/discard")
def character_discard(campaign_id: str, actor_id: str,
                      idempotency_key: str = Form("")):
    try:
        abandon_unfinished_character(
            actor_public_id=actor_id,
            idempotency_key=idempotency_key.strip() or str(uuid.uuid4()),
        )
    except (ValueError, PermissionError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}", status_code=303)


@app.post("/campaigns/{campaign_id}/characters/{actor_id}/delete")
def character_delete(campaign_id: str, actor_id: str,
                     idempotency_key: str = Form("")):
    try:
        delete_character(
            actor_public_id=actor_id,
            idempotency_key=idempotency_key.strip() or str(uuid.uuid4()),
        )
    except (ValueError, PermissionError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}", status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-entry")
def character_career_entry(campaign_id:str,actor_id:str,career_selection:str=Form(...),idempotency_key:str=Form(...)):
    try:
        career_code,assignment_code=career_selection.split("||",1)
        attempt_career_entry(actor_public_id=actor_id,career_code=career_code,assignment_code=assignment_code or None,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/career-entry-fallbacks")
def character_career_fallback(campaign_id:str,attempt_command_public_id:str=Form(...),fallback_kind:str=Form(...),idempotency_key:str=Form(...)):
    try:resolve_career_entry_failure(attempt_command_public_id=attempt_command_public_id,fallback_kind=fallback_kind,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/basic-training")
def character_basic_training(campaign_id:str,actor_id:str,selected_roll_value:int|None=Form(None),specialization:list[str]=Form([]),idempotency_key:str=Form(...)):
    try:
        choices=dict(value.split("||",1) for value in specialization)
        apply_career_basic_training(actor_public_id=actor_id,selected_roll_value=selected_roll_value,cascade_specializations=choices,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/rank-zero-award")
def character_rank_zero_award(campaign_id:str,actor_id:str,cascade_specialization:str|None=Form(None),idempotency_key:str=Form(...)):
    try:apply_career_rank_zero_award(actor_public_id=actor_id,cascade_specialization=cascade_specialization,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/anagathics")
def character_anagathics(campaign_id:str,actor_id:str,uses_anagathics:bool=Form(...),idempotency_key:str=Form(...)):
    try:declare_career_anagathics(actor_public_id=actor_id,uses_anagathics=uses_anagathics,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-survival")
def character_career_survival(campaign_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:attempt_career_survival(actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-rank-attempt")
def character_career_rank_attempt(campaign_id:str,actor_id:str,attempt_kind:str=Form(...),decision:str=Form(...),cascade_specialization:str|None=Form(None),idempotency_key:str=Form(...)):
    try:resolve_career_rank_attempt(actor_public_id=actor_id,attempt_kind=attempt_kind,decision=decision,cascade_specialization=cascade_specialization,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-term-training")
def character_career_term_training(campaign_id:str,actor_id:str,training_table_code:str=Form(...),specialization:list[str]=Form([]),idempotency_key:str=Form(...)):
    try:
        choices=dict(value.split("||",1) for value in specialization)
        apply_career_term_training(actor_public_id=actor_id,training_table_code=training_table_code,cascade_specializations=choices,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-term-completion")
def character_career_term_completion(campaign_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:complete_career_term(actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-reenlistment")
def character_career_reenlistment(campaign_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:determine_career_reenlistment(actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-reenlistment-decision")
def character_career_reenlistment_decision(campaign_id:str,actor_id:str,decision:str=Form(...),idempotency_key:str=Form(...)):
    try:decide_career_reenlistment(actor_public_id=actor_id,decision=decision,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/survival-mishap")
def character_survival_mishap(campaign_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:resolve_survival_mishap(actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-injury")
def character_career_injury(campaign_id:str,actor_id:str,result_two_choice:str|None=Form(None),idempotency_key:str=Form(...)):
    try:determine_career_injury(actor_public_id=actor_id,result_two_choice=result_two_choice,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-injury-application")
def character_career_injury_application(campaign_id:str,actor_id:str,primary_characteristic_code:str=Form(...),other_reduction_mode:str|None=Form(None),other_characteristic_code:str|None=Form(None),idempotency_key:str=Form(...)):
    try:apply_career_injury(actor_public_id=actor_id,primary_characteristic_code=primary_characteristic_code,other_reduction_mode=other_reduction_mode,other_characteristic_code=other_characteristic_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-medical-care")
def character_career_medical_care(campaign_id:str,actor_id:str,decision:str=Form(...),strength_points:int=Form(0),dexterity_points:int=Form(0),endurance_points:int=Form(0),idempotency_key:str=Form(...)):
    points={code:value for code,value in (("characteristic.strength",strength_points),("characteristic.dexterity",dexterity_points),("characteristic.endurance",endurance_points)) if value>0}
    try:resolve_career_medical_care(actor_public_id=actor_id,decision=decision,restoration_points=points,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-muster")
def character_career_muster(campaign_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:initialize_career_muster(actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-benefit")
def character_career_benefit(campaign_id:str,actor_id:str,benefit_table_code:str=Form(...),idempotency_key:str=Form(...)):
    try:roll_career_benefit(actor_public_id=actor_id,benefit_table_code=benefit_table_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-weapon-benefit")
def character_career_weapon_benefit(campaign_id:str,actor_id:str,weapon_rule_code:str=Form(...),resolution_kind:str=Form(...),skill_rule_code:str=Form(""),idempotency_key:str=Form(...)):
    try:resolve_career_weapon_benefit(actor_public_id=actor_id,weapon_rule_code=weapon_rule_code,resolution_kind=resolution_kind,skill_rule_code=skill_rule_code or None,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-aging")
def character_career_aging(campaign_id:str,actor_id:str,aging_kind:str=Form("term"),idempotency_key:str=Form(...)):
    try:determine_career_aging(actor_public_id=actor_id,aging_kind=aging_kind,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/career-aging-application")
def character_career_aging_application(campaign_id:str,actor_id:str,physical_characteristic_codes:list[str]=Form(...),mental_characteristic_code:str=Form(""),idempotency_key:str=Form(...)):
    try:apply_career_aging(actor_public_id=actor_id,physical_characteristic_codes=tuple(physical_characteristic_codes),mental_characteristic_code=mental_characteristic_code or None,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/aging-crisis-cost")
def character_aging_crisis_cost(campaign_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:determine_aging_crisis_cost(actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/aging-crisis-resolution")
def character_aging_crisis_resolution(campaign_id:str,actor_id:str,resolution_kind:str=Form(...),idempotency_key:str=Form(...)):
    try:resolve_aging_crisis(actor_public_id=actor_id,resolution_kind=resolution_kind,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/final-details")
def character_final_details(campaign_id:str,actor_id:str,character_name:str=Form(...),gender_identity:str=Form(""),appearance:str=Form(""),personal_goals:list[str]=Form([]),idempotency_key:str=Form(...)):
    goals=tuple(goal.strip() for goal in personal_goals if goal.strip())
    try:update_character_final_details(actor_public_id=actor_id,character_name=character_name,gender_identity=gender_identity or None,appearance=appearance or None,personal_goals=goals,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/finish-creation")
def character_finish_creation(campaign_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:finish_character_creation(actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/environmental-exposure")
def character_environmental_exposure(campaign_id:str,actor_id:str,environment_kind:str=Form(...),elapsed_minutes:int=Form(...),protective_equipment_active:bool=Form(False),exposure_public_id:str=Form(""),end_exposure:bool=Form(False),idempotency_key:str=Form(...)):
    try:advance_environmental_exposure(actor_public_id=actor_id,environment_kind=environment_kind,elapsed_minutes=elapsed_minutes,protective_equipment_active=protective_equipment_active,exposure_public_id=exposure_public_id or None,end_exposure=end_exposure,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/fatigue")
def character_fatigue(campaign_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:apply_personal_fatigue(actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/fatigue-rest")
def character_fatigue_rest(campaign_id:str,actor_id:str,completed_hours:float=Form(...),idempotency_key:str=Form(...)):
    try:complete_personal_fatigue_rest(actor_public_id=actor_id,completed_hours=completed_hours,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/consciousness-recovery")
def character_consciousness_recovery(campaign_id:str,actor_id:str,minutes_elapsed:int=Form(...),idempotency_key:str=Form(...)):
    try:resolve_personal_unconscious_recovery(actor_public_id=actor_id,minutes_elapsed=minutes_elapsed,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/mental-healing")
def character_mental_healing(campaign_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:resolve_personal_mental_healing(actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/first-aid/determine")
def character_first_aid_determine(campaign_id:str,actor_id:str,doctor_actor_public_id:str=Form(...),damage_instance_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:determine_personal_first_aid(patient_actor_public_id=actor_id,doctor_actor_public_id=doctor_actor_public_id,damage_instance_public_id=damage_instance_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/first-aid/apply")
def character_first_aid_apply(campaign_id:str,actor_id:str,determination_command_public_id:str=Form(...),strength_points:int=Form(0),dexterity_points:int=Form(0),endurance_points:int=Form(0),idempotency_key:str=Form(...)):
    try:apply_determined_personal_first_aid(determination_command_public_id=determination_command_public_id,strength_points=strength_points,dexterity_points=dexterity_points,endurance_points=endurance_points,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/surgery/determine")
def character_surgery_determine(campaign_id:str,actor_id:str,doctor_actor_public_id:str=Form(...),first_aid_command_public_id:str=Form(...),medical_facility_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:determine_personal_surgery(patient_actor_public_id=actor_id,doctor_actor_public_id=doctor_actor_public_id,first_aid_command_public_id=first_aid_command_public_id,medical_facility_public_id=medical_facility_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/surgery/apply")
def character_surgery_apply(campaign_id:str,actor_id:str,determination_command_public_id:str=Form(...),strength_points:int=Form(0),dexterity_points:int=Form(0),endurance_points:int=Form(0),idempotency_key:str=Form(...)):
    try:apply_determined_personal_surgery(determination_command_public_id=determination_command_public_id,strength_points=strength_points,dexterity_points=dexterity_points,endurance_points=endurance_points,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/medical-care/determine")
def character_medical_care_determine(campaign_id:str,actor_id:str,doctor_actor_public_id:str=Form(...),medical_facility_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:determine_personal_medical_care(patient_actor_public_id=actor_id,doctor_actor_public_id=doctor_actor_public_id,medical_facility_public_id=medical_facility_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/medical-care/apply")
def character_medical_care_apply(campaign_id:str,actor_id:str,determination_command_public_id:str=Form(...),strength_points:int=Form(0),dexterity_points:int=Form(0),endurance_points:int=Form(0),idempotency_key:str=Form(...)):
    try:apply_determined_personal_medical_care(determination_command_public_id=determination_command_public_id,strength_points=strength_points,dexterity_points=dexterity_points,endurance_points=endurance_points,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/natural-healing/determine")
def character_natural_healing_determine(campaign_id:str,actor_id:str,lifestyle:str=Form(...),idempotency_key:str=Form(...)):
    try:determine_personal_natural_healing(actor_public_id=actor_id,lifestyle=lifestyle,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/natural-healing/apply")
def character_natural_healing_apply(campaign_id:str,actor_id:str,determination_command_public_id:str=Form(...),strength_points:int=Form(0),dexterity_points:int=Form(0),endurance_points:int=Form(0),idempotency_key:str=Form(...)):
    try:apply_determined_personal_natural_healing(determination_command_public_id=determination_command_public_id,strength_points=strength_points,dexterity_points=dexterity_points,endurance_points=endurance_points,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/injury-crisis-cost")
def character_injury_crisis_cost(campaign_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:determine_injury_crisis_cost(actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/injury-crisis-resolution")
def character_injury_crisis_resolution(campaign_id:str,actor_id:str,resolution_kind:str=Form(...),idempotency_key:str=Form(...)):
    try:resolve_injury_crisis(actor_public_id=actor_id,resolution_kind=resolution_kind,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/crew-assignments")
def crew_assign(campaign_id:str,actor_public_id:str=Form(...),ship_public_id:str=Form(...),ship_crew_position_id:int=Form(...),idempotency_key:str=Form(...)):
    try:assign_ship_crew(campaign_public_id=campaign_id,actor_public_id=actor_public_id,ship_public_id=ship_public_id,ship_crew_position_id=ship_crew_position_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)


@app.post("/campaigns/{campaign_id}/ships")
def ship_acquire(campaign_id: str,owner_actor_public_id: str=Form(...),
                 class_code: str=Form(...),name: str=Form(...),
                 registration_identifier: str=Form(""),idempotency_key: str=Form(...)):
    try:
        acquire_ship(campaign_public_id=campaign_id,
                     owner_actor_public_id=owner_actor_public_id,class_code=class_code,
                     name=name,registration_identifier=registration_identifier,
                     idempotency_key=idempotency_key)
    except PermissionError as exc: raise HTTPException(status_code=403,detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/ship?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/ships/{ship_id}/refuel")
def ship_refuel(campaign_id:str,ship_id:str,actor_public_id:str=Form(...),fuel_type_code:str=Form(...),tons:str=Form(...),idempotency_key:str=Form(...)):
    try:refuel_ship(campaign_public_id=campaign_id,actor_public_id=actor_public_id,ship_public_id=ship_id,fuel_type_code=fuel_type_code,tons=tons,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/ship?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/ships/{ship_id}/expenses")
def ship_expense(campaign_id:str,ship_id:str,actor_public_id:str=Form(...),operating_cost_code:str=Form(...),quantity:str=Form("1"),idempotency_key:str=Form(...)):
    try:pay_ship_expense(campaign_public_id=campaign_id,actor_public_id=actor_public_id,ship_public_id=ship_id,operating_cost_code=operating_cost_code,quantity=quantity,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/ship?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/ships/{ship_id}/payroll")
def ship_payroll(campaign_id:str,ship_id:str,payer_actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:pay_ship_crew(campaign_public_id=campaign_id,payer_actor_public_id=payer_actor_public_id,ship_public_id=ship_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/ship?campaign={campaign_id}",status_code=303)


@app.post("/campaigns/{campaign_id}/sectors")
async def sector_import(campaign_id: str,sector_name: str=Form(...),
                        sector_x: int=Form(0),sector_y: int=Form(0),
                        idempotency_key: str=Form(...),source: UploadFile=File(...)):
    content=await source.read(10_000_001)
    if len(content)>10_000_000: raise HTTPException(status_code=413,detail="Sector file exceeds 10 MB")
    try:
        import_sector(campaign_public_id=campaign_id,sector_name=sector_name,
                      sector_x=sector_x,sector_y=sector_y,
                      source_filename=source.filename or "sector.tab",content=content,
                      idempotency_key=idempotency_key)
    except PermissionError as exc: raise HTTPException(status_code=403,detail=str(exc)) from exc
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/sector?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/ships/{ship_id}/placement")
def ship_place(campaign_id:str,ship_id:str,system_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:place_ship(campaign_public_id=campaign_id,ship_public_id=ship_id,system_public_id=system_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/sector?campaign={campaign_id}&system={system_public_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/jumps")
def jump_plan(campaign_id:str,ship_public_id:str=Form(...),destination_system_public_id:str=Form(...),journey_name:str=Form(...),idempotency_key:str=Form(...)):
    try:plan_jump(campaign_public_id=campaign_id,ship_public_id=ship_public_id,destination_system_public_id=destination_system_public_id,journey_name=journey_name,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/sector?campaign={campaign_id}&system={destination_system_public_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/journeys/{journey_id}/navigation")
def journey_navigation(campaign_id:str,journey_id:str,actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:plot_jump(journey_public_id=journey_id,actor_public_id=actor_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/sector?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/journeys/{journey_id}/attempt")
def journey_attempt(campaign_id:str,journey_id:str,actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:resolve_jump(journey_public_id=journey_id,actor_public_id=actor_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/sector?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/journeys/{journey_id}/cancel")
def journey_cancel(campaign_id:str,journey_id:str,idempotency_key:str=Form(...)):
    try:cancel_jump(journey_public_id=journey_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/sector?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/journeys/{journey_id}/{transition}")
def journey_transition(campaign_id:str,journey_id:str,transition:str,idempotency_key:str=Form(...)):
    if transition not in ('depart','arrive'):raise HTTPException(status_code=404)
    try:result,destination=run_jump(journey_public_id=journey_id,idempotency_key=idempotency_key,complete=transition=='arrive')
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    suffix=f"&system={destination}" if destination else ""
    return RedirectResponse(url=f"/sector?campaign={campaign_id}{suffix}",status_code=303)

@app.post("/campaigns/{campaign_id}/markets")
def market_open(campaign_id:str,system_public_id:str=Form(...),market_name:str=Form(...),idempotency_key:str=Form(...)):
    try:open_market(campaign_public_id=campaign_id,system_public_id=system_public_id,market_name=market_name,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/route-revenue")
def route_revenue_open(campaign_id:str,ship_public_id:str=Form(...),destination_system_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:open_route_revenue(campaign_public_id=campaign_id,ship_public_id=ship_public_id,destination_system_public_id=destination_system_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/freight-contracts")
def freight_contract_accept(campaign_id:str,cycle_public_id:str=Form(...),journey_public_id:str=Form(...),accepted_tons:str=Form(...),idempotency_key:str=Form(...)):
    try:accept_freight_contract(cycle_public_id=cycle_public_id,journey_public_id=journey_public_id,accepted_tons=accepted_tons,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/freight-deliveries")
def freight_delivery(campaign_id:str,contract_public_id:str=Form(...),actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:deliver_freight_contract(contract_public_id=contract_public_id,actor_public_id=actor_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/passenger-bookings")
def passenger_booking(campaign_id:str,cycle_public_id:str=Form(...),journey_public_id:str=Form(...),passage_class:str=Form(...),passenger_count:int=Form(...),idempotency_key:str=Form(...)):
    try:book_route_passengers(cycle_public_id=cycle_public_id,journey_public_id=journey_public_id,passage_class=passage_class,passenger_count=passenger_count,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/passenger-boardings")
def passenger_boarding(campaign_id:str,journey_public_id:str=Form(...),actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:board_route_passengers(journey_public_id=journey_public_id,actor_public_id=actor_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/low-passenger-revivals")
def low_passenger_revival(campaign_id:str,journey_passage_id:int=Form(...),idempotency_key:str=Form(...)):
    try:revive_low_passenger(journey_passage_id=journey_passage_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/steward-services")
def steward_service(campaign_id:str,service_selection:str=Form(...),service_reference:str=Form(...),characteristic_rule_code:str=Form(...),difficulty_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    journey_public_id,steward_actor_public_id,passenger_actor_public_id,service_code=service_selection.split("||",3)
    try:resolve_steward_service(journey_public_id=journey_public_id,steward_actor_public_id=steward_actor_public_id,passenger_actor_public_id=passenger_actor_public_id,service_code=service_code,service_reference=service_reference,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/passenger-manifests")
def passenger_manifest(campaign_id:str,journey_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:finalize_passenger_manifest(journey_public_id=journey_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/postal-contracts")
def postal_contract_accept(campaign_id:str,journey_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:accept_postal_contract(journey_public_id=journey_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/postal-deliveries")
def postal_contract_delivery(campaign_id:str,contract_public_id:str=Form(...),actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:deliver_postal_contract(contract_public_id=contract_public_id,actor_public_id=actor_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/charter-quotes")
def charter_quote(campaign_id:str,ship_public_id:str=Form(...),billing_blocks:int=Form(...),idempotency_key:str=Form(...)):
    try:quote_starship_charter(campaign_public_id=campaign_id,ship_public_id=ship_public_id,billing_blocks=billing_blocks,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)
@app.post("/campaigns/{campaign_id}/charter-contracts")
def charter_accept(campaign_id:str,quote_public_id:str=Form(...),journey_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:accept_starship_charter(quote_public_id=quote_public_id,journey_public_id=journey_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)
@app.post("/campaigns/{campaign_id}/charter-completions")
def charter_complete(campaign_id:str,contract_public_id:str=Form(...),actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:complete_starship_charter(contract_public_id=contract_public_id,actor_public_id=actor_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/ships/{ship_id}/mortgages")
def mortgage_open(campaign_id:str,ship_id:str,actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:open_ship_mortgage(campaign_public_id=campaign_id,ship_public_id=ship_id,actor_public_id=actor_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/ship?campaign={campaign_id}",status_code=303)
@app.post("/campaigns/{campaign_id}/ships/{ship_id}/mortgage-payments")
def mortgage_pay(campaign_id:str,ship_id:str,actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:pay_ship_mortgage(ship_public_id=ship_id,actor_public_id=actor_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/ship?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/sources")
async def source_upload(campaign_id:str,title:str=Form(...),source_kind:str=Form(...),idempotency_key:str=Form(...),source:UploadFile=File(...)):
    content=await source.read()
    media_type=source.content_type or ('application/pdf' if (source.filename or '').lower().endswith('.pdf') else 'text/plain')
    try:ingest_campaign_source(campaign_public_id=campaign_id,title=title,source_kind=source_kind,original_filename=source.filename or 'source',media_type=media_type,content=content,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/library?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/sources/{document_id}/review")
def source_review(campaign_id:str,document_id:str,idempotency_key:str=Form(...)):
    try:review_campaign_source(document_public_id=document_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/library?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/adventures")
def adventure_create(campaign_id:str,name:str=Form(...),source_document_public_id:str=Form(""),idempotency_key:str=Form(...)):
    try:create_adventure_module(campaign_public_id=campaign_id,name=name,source_document_public_id=source_document_public_id or None,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/library?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/adventures/{module_id}/locations")
def adventure_key_location(campaign_id:str,module_id:str,location_key:str=Form(...),name:str=Form(...),keyed_description:str=Form(...),source_page_number:str=Form(""),occupants_initial:str=Form(""),treasure_initial:str=Form(""),idempotency_key:str=Form(...)):
    try:key_adventure_location(module_public_id=module_id,location_key=location_key,name=name,keyed_description=keyed_description,source_page_number=int(source_page_number) if source_page_number else None,occupants_initial=occupants_initial or None,treasure_initial=treasure_initial or None,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/library?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/adventures/{module_id}/advance")
def adventure_advance(campaign_id:str,module_id:str,turns:int=Form(1),rest:bool=Form(False),idempotency_key:str=Form(...)):
    try:advance_adventure_exploration(module_public_id=module_id,turns=turns,rest=rest,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/library?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/adventures/{module_id}/index")
def adventure_index_begin(campaign_id:str,module_id:str,idempotency_key:str=Form(...)):
    try:begin_adventure_indexing(module_public_id=module_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/library?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/adventure-proposals/{proposal_id}/review")
def adventure_proposal_review(campaign_id:str,proposal_id:str,decision:str=Form(...),review_note:str=Form(""),idempotency_key:str=Form(...)):
    try:review_adventure_location_proposal(proposal_public_id=proposal_id,decision=decision,review_note=review_note,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/library?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/adventure-locations/{location_id}/enter")
def adventure_enter(campaign_id:str,location_id:str,idempotency_key:str=Form(...)):
    try:enter_adventure_location(location_public_id=location_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/library?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/adventure-locations/{location_id}/state")
def adventure_state(campaign_id:str,location_id:str,occupant_status:str=Form(...),treasure_status:str=Form(...),alert_status:str=Form(...),current_note:str=Form(""),idempotency_key:str=Form(...)):
    try:update_adventure_location_state(location_public_id=location_id,occupant_status=occupant_status,treasure_status=treasure_status,alert_status=alert_status,current_note=current_note,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/library?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/referee-turns")
def referee_turn(campaign_id:str,player_text:str=Form(...),idempotency_key:str=Form(...),return_to:str=Form("")):
    try:send_referee_message(campaign_public_id=campaign_id,player_text=player_text,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    destination = "/play" if return_to == "play" else "/"
    return RedirectResponse(url=f"{destination}?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/gm-assistance")
def gm_assistance(request:Request,campaign_id:str,prompt_text:str=Form(...),idempotency_key:str=Form(...),return_to:str=Form("")):
    if campaign_role(request.state.user.user_id,campaign_id)!='owner':raise HTTPException(status_code=403,detail='Only the campaign owner can request private GM assistance')
    try:request_gm_assistance(campaign_public_id=campaign_id,prompt_text=prompt_text,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    destination="/play" if return_to=="play" else "/"
    return RedirectResponse(url=f"{destination}?campaign={campaign_id}",status_code=303)

@app.get("/api/campaigns/{campaign_id}/gm-assistance")
def gm_assistance_list(request:Request,campaign_id:str):
    if campaign_role(request.state.user.user_id,campaign_id)!='owner':raise HTTPException(status_code=403,detail='Private GM assistance belongs to the campaign owner')
    return reader.gm_assistance(campaign_id)

@app.post("/campaigns/{campaign_id}/referee-actions/{request_id}/confirm")
def referee_action_confirm(campaign_id:str,request_id:str,idempotency_key:str=Form(...)):
    try:confirm_referee_action(request_public_id=request_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError,TypeError,KeyError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters")
def encounter_create(campaign_id:str,encounter_type_code:str=Form(...),idempotency_key:str=Form(...)):
    try:create_encounter(campaign_public_id=campaign_id,encounter_type_code=encounter_type_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/participants")
def encounter_participant_add(campaign_id:str,encounter_id:str,actor_public_id:str=Form(...),participant_role:str=Form(...),side_code:str=Form(...),idempotency_key:str=Form(...)):
    try:add_encounter_participant(encounter_public_id=encounter_id,actor_public_id=actor_public_id,participant_role=participant_role,side_code=side_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/personal-combat")
def encounter_combat_begin(campaign_id:str,encounter_id:str,reason:str=Form(...),idempotency_key:str=Form(...)):
    try:begin_personal_combat(encounter_public_id=encounter_id,reason=reason,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/battlefield-conditions")
def combat_battlefield_conditions(campaign_id:str,encounter_id:str,light_code:str=Form(...),obscurant_code:str=Form(...),extreme_weather:bool=Form(False),gravity_code:str=Form(...),expected_version:int=Form(...),idempotency_key:str=Form(...)):
    try:set_battlefield_conditions(encounter_public_id=encounter_id,light_code=light_code,obscurant_code=obscurant_code,extreme_weather=extreme_weather,gravity_code=gravity_code,expected_version=expected_version,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/explosions")
def combat_explosion_declare(campaign_id:str,encounter_id:str,source_reference:str=Form(...),damage_dice:int=Form(...),damage_die_sides:int=Form(...),flat_damage:int=Form(0),target_actor_public_ids:list[str]=Form(...),idempotency_key:str=Form(...)):
    try:declare_combat_explosion(encounter_public_id=encounter_id,source_reference=source_reference,damage_dice=damage_dice,damage_die_sides=damage_die_sides,flat_damage=flat_damage,target_actor_public_ids=tuple(target_actor_public_ids),idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/explosions/{explosion_id}/reactions")
def combat_explosion_reaction(campaign_id:str,encounter_id:str,explosion_id:str,actor_public_id:str=Form(...),reaction_kind:str=Form(...),idempotency_key:str=Form(...)):
    try:react_to_combat_explosion(explosion_public_id=explosion_id,actor_public_id=actor_public_id,reaction_kind=reaction_kind,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/explosions/{explosion_id}/resolve")
def combat_explosion_resolve(campaign_id:str,encounter_id:str,explosion_id:str,idempotency_key:str=Form(...)):
    try:resolve_combat_explosion(explosion_public_id=explosion_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/personal-combat/initialize")
def encounter_combat_initialize(campaign_id:str,encounter_id:str,aware_actor_public_ids:list[str]=Form([]),starting_context_code:str=Form(...),light_condition:str=Form(...),starting_range_rule_code:str=Form(''),idempotency_key:str=Form(...)):
    try:initialize_personal_combat(encounter_public_id=encounter_id,aware_actor_public_ids=tuple(aware_actor_public_ids),starting_context_code=starting_context_code,light_condition=light_condition,starting_range_rule_code=starting_range_rule_code or None,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/begin")
def combat_turn_begin(campaign_id:str,encounter_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:begin_combat_turn(encounter_public_id=encounter_id,actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/hasten")
def combat_hasten(campaign_id:str,encounter_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:hasten_combatant(encounter_public_id=encounter_id,actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/delay")
def combat_delay(campaign_id:str,encounter_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:delay_combat_turn(encounter_public_id=encounter_id,actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/resume")
def combat_resume(campaign_id:str,encounter_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:resume_combat_turn(encounter_public_id=encounter_id,actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/forfeit")
def combat_forfeit(campaign_id:str,encounter_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:forfeit_combat_turn(encounter_public_id=encounter_id,actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/stance")
def combat_stance(campaign_id:str,encounter_id:str,actor_id:str,stance_code:str=Form(...),idempotency_key:str=Form(...)):
    try:change_combat_stance(encounter_public_id=encounter_id,actor_public_id=actor_id,stance_code=stance_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/cover")
def combat_cover(campaign_id:str,encounter_id:str,actor_id:str,cover_code:str=Form(""),idempotency_key:str=Form(...)):
    try:set_combat_cover(encounter_public_id=encounter_id,actor_public_id=actor_id,cover_code=cover_code or None,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/move")
def combat_move(campaign_id:str,encounter_id:str,actor_id:str,metres:float=Form(...),difficult_terrain:bool=Form(False),idempotency_key:str=Form(...)):
    try:move_combatant(encounter_public_id=encounter_id,actor_public_id=actor_id,metres=metres,difficult_terrain=difficult_terrain,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/communications")
def combat_communication(campaign_id:str,encounter_id:str,commander_actor_public_id:str=Form(...),member_actor_public_id:str=Form(...),method_code:str=Form(...),jammed:bool=Form(False),blocked:bool=Form(False),line_of_sight:bool=Form(False),smoke_or_aerosols:bool=Form(False),member_moving:bool=Form(False),idempotency_key:str=Form(...)):
    try:set_battlefield_communication(encounter_public_id=encounter_id,commander_actor_public_id=commander_actor_public_id,member_actor_public_id=member_actor_public_id,method_code=method_code,jammed=jammed,blocked=blocked,line_of_sight=line_of_sight,smoke_or_aerosols=smoke_or_aerosols,member_moving=member_moving,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/initiative-support")
def combat_initiative_support(campaign_id:str,encounter_id:str,actor_id:str,support_code:str=Form(...),characteristic_rule_code:str=Form(...),target_actor_public_id:str=Form(""),idempotency_key:str=Form(...)):
    try:apply_combat_initiative_support(encounter_public_id=encounter_id,commander_actor_public_id=actor_id,support_code=support_code,characteristic_rule_code=characteristic_rule_code,target_actor_public_id=target_actor_public_id or None,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/flight")
def combat_flight(campaign_id:str,encounter_id:str,actor_id:str,metres:float=Form(...),altitude_change_metres:float=Form(0),idempotency_key:str=Form(...)):
    try:move_combatant_in_flight(encounter_public_id=encounter_id,actor_public_id=actor_id,metres=metres,altitude_change_metres=altitude_change_metres,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/great-leap")
def combat_great_leap(campaign_id:str,encounter_id:str,actor_id:str,characteristic_rule_code:str=Form(...),difficulty_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:resolve_combatant_great_leap(encounter_public_id=encounter_id,actor_public_id=actor_id,characteristic_rule_code=characteristic_rule_code,difficulty_rule_code=difficulty_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/aim")
def combat_aim(campaign_id:str,encounter_id:str,actor_id:str,target_actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:aim_combatant(encounter_public_id=encounter_id,actor_public_id=actor_id,target_actor_public_id=target_actor_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/actions")
def combat_action_spend(campaign_id:str,encounter_id:str,actor_id:str,operation:str=Form(...),idempotency_key:str=Form(...)):
    try:spend_combat_action(encounter_public_id=encounter_id,actor_public_id=actor_id,operation=operation,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/kill-aim")
def combat_kill_aim(campaign_id:str,encounter_id:str,actor_id:str,target_actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:aim_combatant_for_kill(encounter_public_id=encounter_id,actor_public_id=actor_id,target_actor_public_id=target_actor_public_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/grapples")
def combat_grapple(campaign_id:str,encounter_id:str,challenger_actor_public_id:str=Form(...),opponent_actor_public_id:str=Form(...),challenger_characteristic_rule_code:str=Form(...),opponent_characteristic_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:resolve_combat_grapple(encounter_public_id=encounter_id,challenger_actor_public_id=challenger_actor_public_id,opponent_actor_public_id=opponent_actor_public_id,challenger_characteristic_rule_code=challenger_characteristic_rule_code,opponent_characteristic_rule_code=opponent_characteristic_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/grapples/{grapple_id}/options")
def combat_grapple_option(campaign_id:str,encounter_id:str,grapple_id:str,option_code:str=Form(...),continue_grapple:bool=Form(False),displacement_metres:float=Form(0),idempotency_key:str=Form(...)):
    try:apply_combat_grapple_option(grapple_public_id=grapple_id,option_code=option_code,continue_grapple=continue_grapple,displacement_metres=displacement_metres,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/free-actions")
def combat_free_action(campaign_id:str,encounter_id:str,actor_id:str,action_reference:str=Form(...),idempotency_key:str=Form(...)):
    try:perform_combat_free_action(encounter_public_id=encounter_id,actor_public_id=actor_id,action_reference=action_reference,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/coup-de-grace")
def combat_coup_de_grace(campaign_id:str,encounter_id:str,actor_id:str,target_actor_public_id:str=Form(...),weapon_rule_code:str=Form(...),delivery_kind:str=Form(...),idempotency_key:str=Form(...)):
    try:resolve_combat_coup_de_grace(encounter_public_id=encounter_id,actor_public_id=actor_id,target_actor_public_id=target_actor_public_id,weapon_rule_code=weapon_rule_code,delivery_kind=delivery_kind,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/extended-actions/start")
def combat_extended_start(campaign_id:str,encounter_id:str,actor_id:str,task_reference:str=Form(...),characteristic_rule_code:str=Form(...),skill_rule_code:str=Form(...),time_frame_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:start_combat_extended_action(encounter_public_id=encounter_id,actor_public_id=actor_id,task_reference=task_reference,characteristic_rule_code=characteristic_rule_code,skill_rule_code=skill_rule_code,time_frame_rule_code=time_frame_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/extended-actions/{operation}")
def combat_extended_progress(campaign_id:str,encounter_id:str,actor_id:str,operation:str,idempotency_key:str=Form(...)):
    if operation not in {"advance","abandon"}:raise HTTPException(status_code=400,detail="Unknown extended-action operation")
    try:progress_combat_extended_action(encounter_public_id=encounter_id,actor_public_id=actor_id,operation=operation,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/complete")
def combat_turn_complete(campaign_id:str,encounter_id:str,actor_id:str,idempotency_key:str=Form(...)):
    try:complete_combat_turn(encounter_public_id=encounter_id,actor_public_id=actor_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/rounds/advance")
def combat_round_advance(campaign_id:str,encounter_id:str,idempotency_key:str=Form(...)):
    try:advance_combat_round(encounter_public_id=encounter_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/attacks")
def combat_attack_declare(campaign_id:str,encounter_id:str,attacker_actor_public_id:str=Form(...),target_actor_public_id:str=Form(...),attack_selection:str=Form(...),target_has_cover:bool=Form(False),extreme_range_authorization_public_id:str=Form(""),idempotency_key:str=Form(...)):
    try:
        item_rule_code,attack_profile_code,range_rule_code=attack_selection.split('||')
        declare_combat_attack(encounter_public_id=encounter_id,attacker_actor_public_id=attacker_actor_public_id,target_actor_public_id=target_actor_public_id,item_rule_code=item_rule_code,attack_profile_code=attack_profile_code,range_rule_code=range_rule_code,target_has_cover=target_has_cover,extreme_range_authorization_public_id=extreme_range_authorization_public_id or None,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/extreme-range-authorizations")
def combat_extreme_range_authorize(campaign_id:str,encounter_id:str,attacker_actor_public_id:str=Form(...),target_actor_public_id:str=Form(...),weapon_selection:str=Form(...),rest_reference:str=Form(...),line_of_sight:bool=Form(False),idempotency_key:str=Form(...)):
    item_rule_code,attack_profile_code=weapon_selection.split("||",1)
    try:authorize_extreme_range(encounter_public_id=encounter_id,attacker_actor_public_id=attacker_actor_public_id,target_actor_public_id=target_actor_public_id,item_rule_code=item_rule_code,attack_profile_code=attack_profile_code,rest_reference=rest_reference,line_of_sight=line_of_sight,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/attacks/{attack_id}/resolve")
def combat_attack_resolve(campaign_id:str,encounter_id:str,attack_id:str,item_rule_code:str=Form(...),attack_profile_code:str=Form(...),range_rule_code:str=Form(...),target_actor_public_id:str=Form(...),armor_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:resolve_combat_attack(personal_attack_public_id=attack_id,item_rule_code=item_rule_code,attack_profile_code=attack_profile_code,range_rule_code=range_rule_code,target_actor_public_id=target_actor_public_id,armor_rule_code=armor_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/damage/{damage_id}/allocate")
def combat_damage_allocate(campaign_id:str,damage_id:str,strength_damage:int=Form(0),dexterity_damage:int=Form(0),endurance_damage:int=Form(0),idempotency_key:str=Form(...)):
    try:apply_combat_damage(damage_instance_public_id=damage_id,strength_damage=strength_damage,dexterity_damage=dexterity_damage,endurance_damage=endurance_damage,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/weapons/ready")
def combat_weapon_ready(campaign_id:str,encounter_id:str,actor_id:str,weapon_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:ready_combat_weapon(encounter_public_id=encounter_id,actor_public_id=actor_id,weapon_rule_code=weapon_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/weapons/reload")
def combat_weapon_reload(campaign_id:str,encounter_id:str,actor_id:str,weapon_rule_code:str=Form(...),ammunition_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:reload_combat_weapon(encounter_public_id=encounter_id,actor_public_id=actor_id,weapon_rule_code=weapon_rule_code,ammunition_rule_code=ammunition_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/attacks/{attack_id}/reactions")
def combat_attack_react(campaign_id:str,encounter_id:str,attack_id:str,actor_public_id:str=Form(...),reaction_kind:str=Form(...),idempotency_key:str=Form(...)):
    try:react_to_combat_attack(encounter_public_id=encounter_id,actor_public_id=actor_public_id,attack_trigger_reference=attack_id,reaction_kind=reaction_kind,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/resolve")
def combat_resolve(campaign_id:str,encounter_id:str,outcome_kind:str=Form(...),resolution_summary:str=Form(...),winning_side_code:str=Form(''),idempotency_key:str=Form(...)):
    try:end_personal_combat(encounter_public_id=encounter_id,outcome_kind=outcome_kind,resolution_summary=resolution_summary,winning_side_code=winning_side_code or None,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/armor/{item_id}/equip")
def character_armor_equip(campaign_id:str,actor_id:str,item_id:str,layer_order:int=Form(1),idempotency_key:str=Form(...)):
    try:equip_actor_armor(actor_public_id=actor_id,item_public_id=item_id,layer_order=layer_order,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/equipment-purchases")
def equipment_purchase(campaign_id:str,actor_public_id:str=Form(...),item_rule_code:str=Form(...),idempotency_key:str=Form(...)):
    try:purchase_personal_equipment(campaign_public_id=campaign_id,actor_public_id=actor_public_id,item_rule_code=item_rule_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/ammunition-purchases")
def ammunition_purchase(campaign_id:str,actor_public_id:str=Form(...),ammunition_rule_code:str=Form(...),reload_units:int=Form(1),idempotency_key:str=Form(...)):
    try:purchase_personal_ammunition(campaign_public_id=campaign_id,actor_public_id=actor_public_id,ammunition_rule_code=ammunition_rule_code,reload_units=reload_units,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/armor/{item_id}/unequip")
def character_armor_unequip(campaign_id:str,actor_id:str,item_id:str,idempotency_key:str=Form(...)):
    try:unequip_actor_armor(actor_public_id=actor_id,item_public_id=item_id,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/characters/{actor_id}/armor/{item_id}/usage")
def character_armor_usage(campaign_id:str,actor_id:str,item_id:str,laser_hits:int=Form(0),life_support_seconds_used:int=Form(0),idempotency_key:str=Form(...)):
    try:consume_actor_armor_resources(actor_public_id=actor_id,item_public_id=item_id,laser_hits=laser_hits,life_support_seconds_used=life_support_seconds_used,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/crew?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/markets/{market_session_id}/quotes")
def purchase_quote(campaign_id:str,market_session_id:int,actor_public_id:str=Form(...),trade_good_code:str=Form(...),idempotency_key:str=Form(...)):
    try:roll_purchase_price(actor_public_id=actor_public_id,market_session_id=market_session_id,trade_good_code=trade_good_code,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/trading-setup")
def trading_setup(campaign_id:str,actor_public_id:str=Form(...),ship_public_id:str=Form(...),opening_balance:int=Form(0),idempotency_key:str=Form(...)):
    try:prepare_trading(campaign_public_id=campaign_id,actor_public_id=actor_public_id,ship_public_id=ship_public_id,opening_balance=opening_balance,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/purchases")
def goods_purchase(campaign_id:str,actor_public_id:str=Form(...),ship_public_id:str=Form(...),stock_id:int=Form(...),broker_command_public_id:str=Form(...),quantity_tons:int=Form(...),idempotency_key:str=Form(...)):
    try:purchase_goods(campaign_public_id=campaign_id,actor_public_id=actor_public_id,ship_public_id=ship_public_id,stock_id=stock_id,broker_command_public_id=broker_command_public_id,quantity_tons=quantity_tons,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/sale-quotes")
def sale_quote(campaign_id:str,actor_public_id:str=Form(...),market_session_id:int=Form(...),trade_good_code:str=Form(...),idempotency_key:str=Form(...)):
    try:roll_sale_price(actor_public_id=actor_public_id,market_session_id=market_session_id,trade_good_code=trade_good_code,idempotency_key=idempotency_key)
    except ValueError as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/sales")
def goods_sale(campaign_id:str,actor_public_id:str=Form(...),ship_public_id:str=Form(...),lot_id:int=Form(...),market_session_id:int=Form(...),broker_command_public_id:str=Form(...),quantity_tons:int=Form(...),idempotency_key:str=Form(...)):
    try:sell_goods(campaign_public_id=campaign_id,actor_public_id=actor_public_id,ship_public_id=ship_public_id,lot_id=lot_id,market_session_id=market_session_id,broker_command_public_id=broker_command_public_id,quantity_tons=quantity_tons,idempotency_key=idempotency_key)
    except ValueError as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/trade?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/notes")
def note_add(campaign_id:str,title:str=Form(...),note_kind:str=Form(...),note_text:str=Form(...),ai_memory_enabled:bool=Form(False),idempotency_key:str=Form(...)):
    try:add_campaign_note(campaign_public_id=campaign_id,title=title,note_kind=note_kind,note_text=note_text,ai_memory_enabled=ai_memory_enabled,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/journal?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/scene-snapshots")
def scene_snapshot(campaign_id:str,template_code:str=Form(...),scene_reference:str=Form(...),slot_codes:list[str]=Form(...),fact_values:list[str]=Form(...),source_references:list[str]=Form(...),idempotency_key:str=Form(...)):
    try:create_scene_snapshot(campaign_public_id=campaign_id,template_code=template_code,scene_reference=scene_reference,slot_codes=tuple(slot_codes),fact_values=tuple(fact_values),source_references=tuple(source_references),idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/journal?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/session-archives")
def session_archive(campaign_id:str,title:str=Form(...),transcript_text:str=Form(...),ai_memory_enabled:bool=Form(False),idempotency_key:str=Form(...)):
    try:archive_play_session(campaign_public_id=campaign_id,title=title,transcript_text=transcript_text,ai_memory_enabled=ai_memory_enabled,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/journal?campaign={campaign_id}",status_code=303)


@app.get("/")
def cockpit_index():
    """The cockpit is the front door. The registry console lives at /command."""
    return FileResponse(
        ROOT / "app" / "static" / "cockpit" / "index.html",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/command", response_class=HTMLResponse)
def dashboard(request: Request, campaign: str | None = None, invite_created: str | None = None):
    current = selected_campaign(campaign)
    role=(campaign_role(request.state.user.user_id,current["public_id"]) if current else None)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=page_context(
            request, "dashboard", campaign=current,
            campaigns=reader.campaigns(user_id=request.state.user.user_id),
            creation_key=str(uuid.uuid4()),
            invite_created=invite_created,
            gm_assistance=(reader.gm_assistance(current["public_id"]) if current and current["play_mode"]=="ai_assisted" and role=="owner" else []),
        ),
    )


@app.get("/play", response_class=HTMLResponse)
def play(request: Request, campaign: str | None = None):
    if campaign is None:
        available = reader.campaigns(user_id=request.state.user.user_id)
        if available:
            return RedirectResponse(
                url=f"/play?campaign={available[0].public_id}", status_code=303
            )
    current = selected_campaign(campaign)
    role=(campaign_role(request.state.user.user_id,current["public_id"]) if current else None)
    return templates.TemplateResponse(
        request=request,
        name="play.html",
        context=page_context(
            request, "dashboard", campaign=current,
            creation_key=str(uuid.uuid4()),
            gm_assistance=(reader.gm_assistance(current["public_id"]) if current and current["play_mode"]=="ai_assisted" and role=="owner" else []),
        ),
    )


@app.get("/sector", response_class=HTMLResponse)
def sector(request: Request,campaign: str|None=None,system: str|None=None):
    current = selected_campaign(campaign)
    selected=next((item for item in (current or {}).get("systems",[]) if item["public_id"]==system),None)
    if selected is None and current and current["systems"]:selected=current["systems"][0]
    return templates.TemplateResponse(
        request=request,
        name="sector.html",
        context=page_context(request,"sector",campaign=current,selected_system=selected,creation_key=str(uuid.uuid4())),
    )


@app.get("/crew", response_class=HTMLResponse)
def crew(request: Request, campaign: str | None = None):
    current = selected_campaign(campaign)
    return templates.TemplateResponse(
        request=request,
        name="crew.html",
        context=page_context(
            request,"crew",campaign=current,
            creation_key=str(uuid.uuid4()),
        ),
    )

@app.get("/character-creation",response_class=HTMLResponse)
def character_creation(request:Request,campaign:str|None=None):
    current=selected_campaign(campaign)
    return templates.TemplateResponse(request=request,name="character_creation.html",context=page_context(request,"character-creation",campaign=current,creation_key=str(uuid.uuid4())))


@app.get("/library", response_class=HTMLResponse)
def library(request: Request, campaign: str | None = None):
    current = selected_campaign(campaign)
    modules = adventure_modules(campaign_public_id=current.public_id) if current else []
    return templates.TemplateResponse(
        request=request,
        name="library.html",
        context=page_context(request, "library", campaign=current,adventure_modules=modules,creation_key=str(uuid.uuid4())),
    )


@app.get("/ship", response_class=HTMLResponse)
def ship(request: Request,campaign: str|None=None):
    current=selected_campaign(campaign)
    return templates.TemplateResponse(request=request,name="ship.html",context=page_context(
        request,"ship",campaign=current,ship_classes=reader.ship_classes(),
        creation_key=str(uuid.uuid4()),
    ))

@app.get("/trade",response_class=HTMLResponse)
def trade(request:Request,campaign:str|None=None):
    current=selected_campaign(campaign)
    return templates.TemplateResponse(request=request,name="trade.html",context=page_context(request,"trade",campaign=current,creation_key=str(uuid.uuid4())))

@app.get("/journal",response_class=HTMLResponse)
def journal(request:Request,campaign:str|None=None):
    current=selected_campaign(campaign)
    return templates.TemplateResponse(request=request,name="journal.html",context=page_context(request,"journal",campaign=current,creation_key=str(uuid.uuid4())))

@app.get("/encounters",response_class=HTMLResponse)
def encounters(request:Request,campaign:str|None=None):
    current=selected_campaign(campaign)
    return templates.TemplateResponse(request=request,name="encounters.html",context=page_context(request,"encounters",campaign=current,creation_key=str(uuid.uuid4())))

@app.get("/psionics",response_class=HTMLResponse)
def psionics(request:Request,campaign:str|None=None):
    current=selected_campaign(campaign)
    return templates.TemplateResponse(request=request,name="psionics.html",context=page_context(request,"psionics",campaign=current,creation_key=str(uuid.uuid4())))

@app.get("/contacts",response_class=HTMLResponse)
def contacts(request:Request,campaign:str|None=None):
    current=selected_campaign(campaign)
    return templates.TemplateResponse(request=request,name="contacts.html",context=page_context(request,"contacts",campaign=current,social_rules=reader.social_rules(),creation_key=str(uuid.uuid4())))

@app.get("/operations",response_class=HTMLResponse)
def operations(request:Request,campaign:str|None=None):
    current=selected_campaign(campaign)
    return templates.TemplateResponse(request=request,name="operations.html",context=page_context(request,"operations",campaign=current,field_rules=reader.field_rules(),creation_key=str(uuid.uuid4())))

@app.get("/info",response_class=HTMLResponse)
def information(request:Request,campaign:str|None=None):
    current=selected_campaign(campaign)
    mcp_script=str((ROOT / "tools" / "run_emporos_mcp.ps1").resolve())
    powershell_path=str(Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"))
    return templates.TemplateResponse(request=request,name="info.html",context=page_context(
        request,"info",campaign=current,mcp_script=mcp_script,powershell_path=powershell_path,
    ))


@app.get("/{page_name}", response_class=HTMLResponse)
def product_page(request: Request, page_name: str, campaign: str | None = None):
    current = selected_campaign(campaign)
    if page_name not in PAGE_COPY:
        return templates.TemplateResponse(
            request=request,
            name="not_found.html",
            context=page_context(
                request, "", campaign=current, page_name=page_name
            ),
            status_code=404,
        )
    title, description = PAGE_COPY[page_name]
    return templates.TemplateResponse(
        request=request,
        name="product_page.html",
        context=page_context(
            request, page_name, campaign=current,
            title=title, description=description
        ),
    )
