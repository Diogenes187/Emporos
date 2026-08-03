from pathlib import Path
import uuid

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.database import CampaignReader, summary_dict
from app.commands import acquire_ship, create_campaign, import_sector, initialize_character, place_ship, plan_jump, plot_jump, resolve_jump, run_jump, open_market, roll_purchase_price, prepare_trading, purchase_goods, roll_sale_price, sell_goods, refuel_ship, pay_ship_expense, assign_ship_crew, add_campaign_note, archive_play_session, pay_ship_crew, open_route_revenue, accept_freight_contract, deliver_freight_contract


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
    try:run_jump(journey_public_id=journey_id,idempotency_key=idempotency_key,complete=transition=='arrive')
    except (ValueError,PermissionError) as exc:raise HTTPException(status_code=400,detail=str(exc)) from exc
    return RedirectResponse(url=f"/sector?campaign={campaign_id}",status_code=303)

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
        context=page_context(request, "library", campaign=current),
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
