# Emporos product brief

Emporos is a Traveller-esque Cepheus campaign game with a substantial
page-based interface and an AI referee that does not own mechanics.

## Launch scope

1. Characters and crew.
2. Ships and shipboard operations.
3. Existing, uploaded, and generated sectors.
4. Travel, trade, encounters, and combat.
5. Uploaded adventures and sources with complete import coverage.
6. Source-grounded narration over engine-owned state.

Domain and KoDP-style polity play are later additions.

## Authority boundary

- PostgreSQL is authoritative for rules and campaign state.
- Application commands perform all mutations transactionally.
- Mechanical receipts retain rule and random-result provenance.
- AI receives a narrow scene packet after relevant state is queried.
- AI may narrate committed results and choose only offered NPC intentions.
- AI cannot write campaign state or resolve mechanics.

## Content promise

An uploaded source is not "ready" until every page or sector record has an
import status. Extracted facts retain source locations. Strict adventure play
must identify gaps instead of silently inventing consequential material.

