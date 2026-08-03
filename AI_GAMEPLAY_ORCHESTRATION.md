# AI Gameplay Orchestration

`engine.orchestration.GameplayOrchestrator` is the supported AI-facing command boundary.

The host supplies the PostgreSQL connection, authenticated authority reference, idempotency key, and optional recorded-randomness source. An AI may select only an entry returned by `available_tools()` and provide that tool's declared gameplay arguments. It cannot supply authority, connection, or randomness parameters and cannot dispatch arbitrary functions.

The orchestrator does not interpret prose as mechanical state. It invokes the existing transactional command, returns its immutable result object, and leaves narration until after the command commits. Validation errors remain errors; the orchestration layer does not repair, override, or fabricate legal game state.

The initial registry exposes source-backed skill operations, Navigation, Steward service, and spacecraft journey departure and arrival. New commands must be added deliberately with tests after their underlying authority, receipt, and invariant contracts exist.
