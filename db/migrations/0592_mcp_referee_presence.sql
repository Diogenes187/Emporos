-- Operational presence for the user-owned desktop MCP process. This is not
-- game state: it records only connection identity and heartbeat timestamps.
CREATE TABLE sys_mcp_client_presence (
    process_session_id uuid PRIMARY KEY,
    authority_reference text NOT NULL CHECK (btrim(authority_reference)<>''),
    client_name text NOT NULL DEFAULT 'Desktop MCP Client'
        CHECK (btrim(client_name)<>''),
    client_version text,
    presence_status text NOT NULL DEFAULT 'connected'
        CHECK (presence_status IN ('connected','disconnected')),
    started_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    last_seen_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    disconnected_at timestamptz,
    CHECK (
        (presence_status='connected' AND disconnected_at IS NULL)
        OR
        (presence_status='disconnected' AND disconnected_at IS NOT NULL)
    )
);

CREATE INDEX sys_mcp_client_presence_authority_recent_idx
    ON sys_mcp_client_presence(authority_reference,last_seen_at DESC);
