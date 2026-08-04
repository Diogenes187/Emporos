from pathlib import Path
import uuid

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import CampaignReader, summary_dict
from app.commands import acquire_ship, create_campaign, import_sector, initialize_character, place_ship, plan_jump, plot_jump, resolve_jump, run_jump, open_market, roll_purchase_price, prepare_trading, purchase_goods, roll_sale_price, sell_goods, refuel_ship, pay_ship_expense, assign_ship_crew, add_campaign_note, archive_play_session, pay_ship_crew, open_route_revenue, accept_freight_contract, deliver_freight_contract, book_route_passengers, board_route_passengers, revive_low_passenger, finalize_passenger_manifest, accept_postal_contract, deliver_postal_contract, quote_starship_charter, accept_starship_charter, complete_starship_charter, open_ship_mortgage, pay_ship_mortgage, ingest_campaign_source, review_campaign_source, send_referee_message, confirm_referee_action, create_encounter, add_encounter_participant, begin_personal_combat, initialize_personal_combat, begin_combat_turn, move_combatant, aim_combatant, complete_combat_turn, advance_combat_round, ready_combat_weapon, reload_combat_weapon, declare_combat_attack, resolve_combat_attack, apply_combat_damage, react_to_combat_attack, end_personal_combat, equip_actor_armor, unequip_actor_armor, purchase_personal_equipment, purchase_personal_ammunition, attempt_career_entry, resolve_career_entry_failure, apply_career_basic_training, apply_career_rank_zero_award, declare_career_anagathics, attempt_career_survival, resolve_career_rank_attempt, apply_career_term_training


ROOT = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=ROOT / "app" / "templates")

app = FastAPI(title="Emporos", version="0.1.0")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")
app.mount(
    "/logos",
    StaticFiles(directory=ROOT / "logos", check_dir=False),
    name="logos",
)


NAVIGATION = (
    ("dashboard", "Command"),
    ("crew", "Crew"),
    ("ship", "Ship"),
    ("sector", "Sector"),
    ("trade", "Trade"),
    ("journal", "Journal"),
    ("encounters", "Encounters"),
    ("library", "Library"),
)


PAGE_COPY = {
    "crew": ("Crew manifest", "Characters, assignments, health, skills, and relationships."),
    "ship": ("Ship operations", "Systems, fuel, cargo, maintenance, damage, and crew stations."),
    "trade": ("Exchange", "Held markets, freight, passengers, cargo, and audited transactions."),
    "encounters": ("Encounters", "Persistent participants, intentions, rounds, injuries, and outcomes."),
}

reader = CampaignReader()


def selected_campaign(campaign_id: str | None):
    return reader.campaign(campaign_id) if campaign_id else None


def page_context(request: Request, active: str, campaign=None, **values):
    return {
        "request": request,
        "navigation": NAVIGATION,
        "active": active,
        "campaign": campaign,
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
        "database": database,
    }


@app.get("/api/campaigns")
def campaign_list():
    return [summary_dict(item) for item in reader.campaigns()]


@app.get("/api/campaigns/{campaign_id}")
def campaign_overview(campaign_id: str):
    campaign = reader.campaign(campaign_id)
    if campaign is None:
        return {"detail": "Campaign not found"}
    return campaign


@app.post("/campaigns")
def campaign_create(
    name: str = Form(...),
    play_mode: str = Form("ai_refereed"),
    idempotency_key: str = Form(...),
):
    result = create_campaign(
        name=name,
        play_mode=play_mode,
        idempotency_key=idempotency_key,
    )
    return RedirectResponse(
        url=f"/?campaign={result.campaign_public_id}", status_code=303
    )


@app.post("/campaigns/{campaign_id}/characters")
def character_initialize(
    campaign_id: str,
    name: str = Form(...),
    idempotency_key: str = Form(...),
):
    try:
        initialize_character(
            campaign_public_id=campaign_id,
            name=name,
            idempotency_key=idempotency_key,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403,detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(
        url=f"/crew?campaign={campaign_id}", status_code=303
    )

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

@app.post("/campaigns/{campaign_id}/referee-turns")
def referee_turn(campaign_id:str,player_text:str=Form(...),idempotency_key:str=Form(...)):
    try:send_referee_message(campaign_public_id=campaign_id,player_text=player_text,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/?campaign={campaign_id}",status_code=303)

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

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/move")
def combat_move(campaign_id:str,encounter_id:str,actor_id:str,metres:float=Form(...),difficult_terrain:bool=Form(False),idempotency_key:str=Form(...)):
    try:move_combatant(encounter_public_id=encounter_id,actor_public_id=actor_id,metres=metres,difficult_terrain=difficult_terrain,idempotency_key=idempotency_key)
    except (ValueError,PermissionError,RuntimeError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/encounters?campaign={campaign_id}",status_code=303)

@app.post("/campaigns/{campaign_id}/encounters/{encounter_id}/turns/{actor_id}/aim")
def combat_aim(campaign_id:str,encounter_id:str,actor_id:str,target_actor_public_id:str=Form(...),idempotency_key:str=Form(...)):
    try:aim_combatant(encounter_public_id=encounter_id,actor_public_id=actor_id,target_actor_public_id=target_actor_public_id,idempotency_key=idempotency_key)
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
def combat_attack_declare(campaign_id:str,encounter_id:str,attacker_actor_public_id:str=Form(...),target_actor_public_id:str=Form(...),attack_selection:str=Form(...),target_has_cover:bool=Form(False),idempotency_key:str=Form(...)):
    try:
        item_rule_code,attack_profile_code,range_rule_code=attack_selection.split('||')
        declare_combat_attack(encounter_public_id=encounter_id,attacker_actor_public_id=attacker_actor_public_id,target_actor_public_id=target_actor_public_id,item_rule_code=item_rule_code,attack_profile_code=attack_profile_code,range_rule_code=range_rule_code,target_has_cover=target_has_cover,idempotency_key=idempotency_key)
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

@app.post("/campaigns/{campaign_id}/session-archives")
def session_archive(campaign_id:str,title:str=Form(...),transcript_text:str=Form(...),ai_memory_enabled:bool=Form(False),idempotency_key:str=Form(...)):
    try:archive_play_session(campaign_public_id=campaign_id,title=title,transcript_text=transcript_text,ai_memory_enabled=ai_memory_enabled,idempotency_key=idempotency_key)
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/journal?campaign={campaign_id}",status_code=303)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, campaign: str | None = None):
    current = selected_campaign(campaign)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=page_context(
            request, "dashboard", campaign=current,
            campaigns=reader.campaigns(),
            creation_key=str(uuid.uuid4()),
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


@app.get("/library", response_class=HTMLResponse)
def library(request: Request, campaign: str | None = None):
    current = selected_campaign(campaign)
    return templates.TemplateResponse(
        request=request,
        name="library.html",
        context=page_context(request, "library", campaign=current,creation_key=str(uuid.uuid4())),
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
