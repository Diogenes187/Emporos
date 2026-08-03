# Vessel-to-Personal Encounter Pattern

## Classification

**Ownership:** Cepheus Engine pattern
**Status:** Accepted architectural pattern  
**Accepted by:** Raymond  
**Date:** 2026-07-27

## Purpose

A conflict involving vessels may transition into a linked personal-scale
encounter. The personal encounter is mechanically complete, and its structured
outcomes alter control, crew, resources, components, and objectives in the
original vessel encounter.

This is a native Cepheus engine pattern for spacecraft encounters. Derived
products may adapt the same relational transition to their own vessel rules.

## Product Expressions

- Spacecraft may pursue, match velocity, dock or breach, fight through deck
  locations, and seize a bridge or engineering space.
- Viking ships may maneuver, grapple, come alongside, cross to the opposing
  deck, and seize or plunder the vessel.
- Roman ships may ram or grapple, deploy boarding equipment, land marines, and
  capture the enemy deck and officers.
- Sailing ships may chase, damage sails or rigging, come alongside, board, and
  take the quarterdeck, wheel, or magazine.

Each product owns its approach rules, hazards, terminology, combat procedures,
objectives, and vessel-control rules.

## Shared Pattern

```text
Vessel encounter
  -> boarding opportunity
  -> approach and attachment resolution
  -> access point established
  -> linked personal encounter created
  -> personal objectives and combat resolved
  -> structured outcomes returned
  -> vessel control and condition updated
  -> both encounters conclude or continue
```

## Required Relationships

The two encounters remain distinct but linked.

A boarding operation identifies:

- originating vessel encounter;
- attacking and defending vessels;
- boarding and defending parties;
- approach method;
- attachment or docking state;
- access point;
- personal encounter;
- operational objective;
- current boarding status;
- structured outcome.

## Boundary Between Scales

The vessel scale determines whether boarding is possible and how entry is
attempted.

The personal scale determines what individual boarders and defenders do after
entry, including movement, attacks, abilities, injury, surrender, sabotage, and
seizure of important locations.

Neither scale narratively overrides the other.

Examples:

- A successful docking action does not automatically capture the target.
- Winning a fight in one compartment does not automatically control the vessel.
- AI prose cannot create a breach, move a boarding party, destroy a component,
  or transfer ownership.
- Capturing an authoritative control location can produce a vessel-control
  command only when the product's rules permit it.

## State Passed Into the Personal Encounter

The transition supplies:

- participating actors and equipment;
- entry location and adjacent known locations;
- gravity, atmosphere, pressure, lighting, fire, water, smoke, or other hazards;
- defender awareness and surprise;
- vessel motion or damage conditions that affect personal action;
- boarding objective;
- retreat route and access status;
- source events and receipts.

## Outcomes Returned to the Vessel Encounter

Structured personal outcomes may include:

- access secured or repelled;
- compartment controlled or contested;
- crew injured, captured, displaced, or surrendered;
- command personnel captured or killed;
- component operated, disabled, repaired, or sabotaged;
- defenses opened or closed;
- vessel command authority changed;
- boarding party withdrawn or stranded;
- vessel surrendered, captured, scuttled, or released.

The product defines exactly which outcomes are legal and what is required to
produce them.

## Authority and AI

Players choose their characters' actions. A human referee or AI may choose legal
intentions for NPC-controlled boarders, defenders, and vessel crews.

The engine resolves:

- approach and attachment;
- access or breach;
- personal actions;
- damage and conditions;
- control of locations;
- component consequences;
- surrender and transfer of vessel control.

AI may narrate the committed results but cannot skip either mechanical scale.

## Source-Fidelity Rule

For Base Cepheus, every step uses the applicable Cepheus rules.
Where Cepheus supplies vessel approach, docking, equipment, personal combat,
environmental hazard, or damage procedures, those procedures govern.

If Cepheus does not define a required transition—such as the exact condition
for control of a captured bridge—the missing rule is entered in the Cepheus Rule
Decision Register and requires explicit agreement before implementation.

Future products follow their own governing sources and record their own
decisions. They inherit this workflow pattern, not Cepheus-specific mechanics.

## Acceptance Scenarios

1. A maneuvering target forces the boarder to resolve approach before access.
2. Failed docking leaves only source-legal alternatives such as external hull
   access where applicable.
3. Successful access creates a personal encounter at a real vessel location.
4. Boarders cannot appear in an unconnected compartment.
5. Personal damage changes actual persistent actors.
6. Sabotage changes a real vessel component through an engine command.
7. Capturing one location changes only the control permitted by product rules.
8. A repelled boarding party remains located and accounted for.
9. Retrying a boarding command does not duplicate actors or consume resources
   twice.
10. Narration rejection changes no approach, combat, or vessel outcome.
