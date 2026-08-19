# The Emporos Cockpit

The dark single-screen bridge — map, tabs, story feed — is the front door of
the application, served at `/`. It is a fresh build in this repository,
written against this engine's own routes and projection; nothing was copied
from any other codebase.

## What serves it

- `app/static/cockpit/index.html` — the bridge: header strip, interactive SVG
  hex chart (pan, zoom, click a world for its survey dossier, Set Course,
  ◈ Jump runs the whole order — navigation, drive, fuel, clock), tabs
  (Crew / Ships / Worlds / Journal), full lifepath wizard, story feed with
  drag grip and Enter-to-send.
- `app/static/cockpit/market.html` — The Exchange, at `/market`.
- `app/static/cockpit/battle.html` — The Field Desk, at `/battle`.
- `app/cockpit.py` — the router. `app/main.py` includes it and serves the
  cockpit at `/`; the old Jinja registry console moved to `/command`
  (all 161 form wrappers intact, reachable from the 🛠 Console pill).

Reads come only from `/api/campaigns/{id}/full` (app/classic.py). Every
mutation POSTs urlencoded bodies to the existing form routes in `app/main.py`,
so tenant isolation, idempotency, and receipts apply unchanged.

## Map notes

The chart renders client-side from the projection's systems list: Traveller
even-column offset hex grid (32×40), subsector letters, world discs colored
by hydrographics, starport code, UWP line, gold jump-range shading around the
active ship, gold ring on the ship's hex. Click a ship card in the Ships tab
to make it the active ship. `◎ My ship` recentres; the map auto-centres on
first load.

## Standing down a jump order

Migration `0578_journey_cancellation.sql` plus
`cancel_jump_journey_command` (engine/travel_planning.py) add the missing
verb: `POST /campaigns/{id}/journeys/{jid}/cancel`. Only a journey still in
**planning** can be stood down — once the drive is resolved the outcome
stands, so a rolled misjump cannot be dodged by cancelling. Fuel was only
reserved at planning; cancellation releases the reservation, relieves the
crew commitments, and writes a receipt like every other command. The
cockpit offers ✕ Stand down on the journey card and inside the ◈ Jump
modal.

## Live refresh

`GET /api/campaigns/{id}/pulse` returns a cheap change signature (latest
referee message, journey/ship/actor versions, clock day). The cockpit polls
it every 4 seconds and refetches the full projection only when the token
moves, so two open windows stay in step within a few seconds without
websocket infrastructure.
