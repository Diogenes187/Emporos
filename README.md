# Emporos

Emporos is a self-contained, page-based Cepheus campaign game copied from the
Base Cepheus relational template and developed independently from it.

The Emporos engine and database own mechanics and campaign truth. AI is optional:
campaigns can use a human referee with no provider, a human referee with private
AI assistance, or an AI referee. Mechanics remain deterministic database
commands with audited receipts in every mode.

Current playable foundation:

- campaigns, characters, and ships;
- sector import, maps, travel, jumps, and misjumps;
- markets, audited accounts, cargo purchases, and cargo sales;
- relational mechanics and command receipts without stored JSON state blobs.
- provider-neutral AI calls, with DeepSeek configured as the economical default;
- page-accounted, spoiler-safe campaign source ingestion and private review.

AI configuration uses `EMPOROS_AI_PROVIDER`, `EMPOROS_AI_BASE_URL`,
`EMPOROS_AI_MODEL`, and `EMPOROS_AI_API_KEY`. For the default DeepSeek adapter,
`DEEPSEEK_API_KEY` may be used instead. Provider responses are transient; the
database stores relational outcomes and invocation hashes, not response blobs.

## Local MCP server

Run `python mcp_server.py` as a stdio MCP server after supplying
`EMPOROS_DATABASE_URL` (or `BASE_CEPHEUS_DATABASE_URL`). The user's MCP client
owns its model choice, API account, and model costs; this server makes no model
calls. Its initial safe surface reports connection status, lists owned campaign
identities and operating modes, and describes the deterministic gameplay tool
schemas. With the user's explicit authorization, it also exposes current
campaign snapshots, verified private source search, external referee narration,
and execution of the existing allowlisted gameplay commands. The connected AI
cannot issue arbitrary SQL: engine validation and command receipts remain the
only mutation path. MCP transport JSON is never stored as a parallel game-state
model.

Base Cepheus is a template only. Emporos does not import or execute code from
the Base Cepheus directory.
