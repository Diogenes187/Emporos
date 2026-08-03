# Emporos

Emporos is a self-contained, page-based Cepheus campaign game copied from the
Base Cepheus relational template and developed independently from it.

The Emporos engine and database own mechanics and campaign truth. The AI
referee narrates committed results, portrays characters, and proposes bounded
actions.

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

Base Cepheus is a template only. Emporos does not import or execute code from
the Base Cepheus directory.
