# Sector and Persistent Map Audit

## Decision

Keep the current Emporos relational sector model. It correctly makes SQL the
authority for sectors, systems, hex coordinates, main worlds, UWPs, containment,
source hashes, source rows, and import receipts. Do not store a second mutable
map-state blob in SVG, XML, or JSON.

Replace only the current approximate HTML-dot renderer. The earlier Cepheus
game already contains a tested full-sector/subsector SVG renderer with true
Traveller hex geometry, subsector boundaries, labels, jump reach, ship markers,
and selected-hex highlighting. Its ideas can be copied into Emporos and adapted
to query the new PostgreSQL read model; Emporos must not import code from the
old project at runtime.

## Clear gaps

- The current page renders only the first 40 systems.
- Coordinates are percentage-positioned dots rather than a true 32x40 hex map.
- There is no full-sector/subsector view switch.
- Import accepts CSV/TSV with only Name, Hex, and UWP; common TravellerMap/T5
  fields such as subsector, bases, remarks, zone, PBG, and allegiance are not
  yet retained.
- There is no player-facing system/sector creation or revision workflow.

## Intended architecture

1. PostgreSQL remains canonical and revisioned.
2. A read-only renderer generates safe SVG/XML from SQL rows on request.
3. Links in the SVG select systems through ordinary Emporos URLs.
4. Optional SVG export is reproducible and disposable.
5. Sector editing writes normalized SQL through commands and receipts, then the
   SVG reflects the committed state.

This preserves the strong current system while recovering the older game's
better map experience.
