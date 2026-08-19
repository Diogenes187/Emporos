# Classic UI (the old Emporos look, on the SQL engine)

## What was added

- `app/classic.py` — a small router: JSON read endpoints (`GET /api/campaigns/{id}/full`
  exposing the full `CampaignReader.campaign()` projection, plus `/api/catalog/*`)
  and three static pages served at `/classic`, `/classic/market`, `/classic/battle`.
- `app/main.py` — two lines to include that router. Nothing else touched.
- `app/static/classic/index.html` — **the bridge**: campaign select/create, crew
  (with the full character-creation life-path wizard), ships, systems (sector
  import), journal, referee feed, jump planning.
- `app/static/classic/market.html` — **the exchange**: trading setup, market
  survey, broker quotes, buy/sell, purse.
- `app/static/classic/battle.html` — **the field desk**: encounters, personal
  combat runtime (initiative, stance/cover/move/aim, attacks, damage
  allocation, rounds).

The classic pages hold no game logic of their own: every mutation POSTs
`application/x-www-form-urlencoded` bodies to the *existing* form routes in
`app/main.py`, so the tenant-isolation middleware and idempotency/receipt
machinery all still apply. Reads come only from the projection endpoint.
The old Jinja pages still work unchanged — the classic UI sits alongside them.

## Offline bootstrap (also added)

`tools/import_foundation_rules.py` gained an `EMPOROS_OFFLINE_BOOTSTRAP=1`
mode: instead of fetching the OGN SRD website for cross-verification, it
renders the local `sources/cepheus-srd` markdown to HTML and verifies against
that (plus a small cached extract in `tools/offline_cache/` for the one
traveller-srd.com check). Handy when the SRD sites are unreachable. Without
the env var, behaviour is exactly as before.

## Running locally

```
pip install -r requirements.txt markdown
export EMPOROS_DATABASE_URL=postgresql://user:pass@localhost/emporos
python tools/bootstrap_database.py --dsn "$EMPOROS_DATABASE_URL"   # empty DB
uvicorn app.main:app --port 8080
# register at /register, then open /classic
```

## Known rough edges

- Draft-entry first term: the projection says term training is next but the
  engine wants a commission decision first (pre-existing; the old Jinja
  crew.html soft-locks the same way).
- `/logos/emporos_thumbnail_256.jpg` 404s (the `logos/` dir isn't in the repo).
- Referee turns need the AI provider env vars; errors surface in the feed.
- Space combat has full schema but no engine/routes yet, so no classic page.
