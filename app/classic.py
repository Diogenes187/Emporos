"""Classic Emporos UI: JSON read endpoints + static page serving.

The classic UI (app/static/classic/*.html) recreates the original Emporos
"bridge" look. It reads campaign state from the JSON endpoints below and
performs every mutation by POSTing application/x-www-form-urlencoded bodies
to the existing form routes in app.main — so the global tenant-isolation
middleware continues to inspect every request exactly as before.
"""

from __future__ import annotations

import datetime
import decimal
import json
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from .database import CampaignReader

ROOT = Path(__file__).resolve().parent
CLASSIC_DIR = ROOT / "static" / "classic"

router = APIRouter()
_reader = CampaignReader()


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def _json_response(payload: Any) -> Response:
    return Response(
        content=json.dumps(_jsonable(payload)),
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/api/campaigns/{campaign_id}/full")
def campaign_full(campaign_id: str) -> Response:
    campaign = _reader.campaign(campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Unknown campaign")
    return _json_response(campaign)


@router.get("/api/campaigns/{campaign_id}/pulse")
def campaign_pulse(campaign_id: str) -> Response:
    pulse = _reader.pulse(campaign_id)
    if pulse is None:
        raise HTTPException(status_code=404, detail="Unknown campaign")
    return _json_response(pulse)


@router.get("/api/catalog/ship-classes")
def catalog_ship_classes() -> Response:
    return _json_response(_reader.ship_classes())


@router.get("/api/catalog/social-rules")
def catalog_social_rules() -> Response:
    return _json_response(_reader.social_rules())


@router.get("/api/catalog/field-rules")
def catalog_field_rules() -> Response:
    return _json_response(_reader.field_rules())


def _classic_page(name: str) -> FileResponse:
    path = CLASSIC_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Page not found")
    return FileResponse(path, headers={"Cache-Control": "no-store"})


@router.get("/classic")
def classic_index() -> FileResponse:
    return _classic_page("index.html")


@router.get("/classic/market")
def classic_market() -> FileResponse:
    return _classic_page("market.html")


@router.get("/classic/battle")
def classic_battle() -> FileResponse:
    return _classic_page("battle.html")
