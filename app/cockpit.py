"""The Emporos cockpit: the dark single-screen bridge as the front door.

Serves the static cockpit pages (map, tabs, story feed; the Exchange; the
Field Desk). All reads come from the JSON projection endpoints in
app.classic; every mutation POSTs to the existing form routes in app.main,
so tenant isolation, idempotency, and receipts continue to apply unchanged.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from app.auth import local_mode

ROOT = Path(__file__).resolve().parent
COCKPIT_DIR = ROOT / "static" / "cockpit"

router = APIRouter()


def _page(name: str) -> FileResponse:
    path = COCKPIT_DIR / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Page not found")
    return FileResponse(path, headers={"Cache-Control": "no-store"})


@router.get("/api/whoami")
def whoami(request: Request) -> JSONResponse:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return JSONResponse({"display_name": user.display_name,"email":user.email,"local_mode":local_mode()})


@router.get("/market")
def cockpit_market() -> FileResponse:
    return _page("market.html")


@router.get("/battle")
def cockpit_battle() -> FileResponse:
    return _page("battle.html")
