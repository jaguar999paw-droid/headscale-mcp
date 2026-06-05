"""
Headscale MCP Server
Provides MCP tools to manage a self-hosted Headscale control plane via HTTP API.
"""
import argparse
import os
import json
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ── Config from environment ──────────────────────────────────────────────────
HEADSCALE_URL   = os.environ.get("HEADSCALE_URL", "http://headscale:8080")
MCP_AUTH_TOKEN  = os.environ.get("MCP_AUTH_TOKEN", "")
# Headscale API key (set via `headscale apikeys create` then pass as env var)
HEADSCALE_API_KEY = os.environ.get("HEADSCALE_API_KEY", "")

mcp = FastMCP("headscale-mcp")

def hs_headers():
    h = {"Content-Type": "application/json"}
    if HEADSCALE_API_KEY:
        h["Authorization"] = f"Bearer {HEADSCALE_API_KEY}"
    return h

def hs_get(path: str) -> dict:
    with httpx.Client(base_url=HEADSCALE_URL, headers=hs_headers(), timeout=15) as c:
        r = c.get(path)
        r.raise_for_status()
        return r.json()

def hs_post(path: str, payload: dict = None) -> dict:
    with httpx.Client(base_url=HEADSCALE_URL, headers=hs_headers(), timeout=15) as c:
        r = c.post(path, json=payload or {})
        r.raise_for_status()
        return r.json()

def hs_delete(path: str) -> dict:
    with httpx.Client(base_url=HEADSCALE_URL, headers=hs_headers(), timeout=15) as c:
        r = c.delete(path)
        r.raise_for_status()
        return r.json() if r.content else {"status": "deleted"}

# ── Health ────────────────────────────────────────────────────────────────────

@mcp.tool()
def headscale_health() -> str:
    """Check if the Headscale server is healthy and reachable."""
    try:
        with httpx.Client(base_url=HEADSCALE_URL, timeout=10) as c:
            r = c.get("/health")
            return f"Headscale health: {r.status_code} — {r.text[:200]}"
    except Exception as e:
        return f"Headscale unreachable: {e}"

# ── Users ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_users() -> str:
    """List all Headscale users (namespaces)."""
    data = hs_get("/api/v1/user")
    users = data.get("users", [])
    if not users:
        return "No users found."
    return json.dumps(users, indent=2)

@mcp.tool()
def create_user(name: str) -> str:
    """Create a new Headscale user/namespace.

    Args:
        name: Username to create (alphanumeric, hyphens allowed)
    """
    data = hs_post("/api/v1/user", {"name": name})
    return json.dumps(data, indent=2)

@mcp.tool()
def delete_user(name: str) -> str:
    """Delete a Headscale user and all their nodes.

    Args:
        name: Username to delete
    """
    data = hs_delete(f"/api/v1/user/{name}")
    return json.dumps(data, indent=2)

# ── Nodes ─────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_nodes(user: str = "") -> str:
    """List all registered nodes. Optionally filter by user.

    Args:
        user: Optional username to filter nodes
    """
    path = "/api/v1/node"
    if user:
        path += f"?user={user}"
    data = hs_get(path)
    nodes = data.get("nodes", [])
    if not nodes:
        return "No nodes registered."
    summary = []
    for n in nodes:
        summary.append({
            "id": n.get("id"),
            "name": n.get("name"),
            "user": n.get("user", {}).get("name"),
            "ip": n.get("ipAddresses", []),
            "online": n.get("online"),
            "lastSeen": n.get("lastSeen"),
            "expiry": n.get("expiry"),
        })
    return json.dumps(summary, indent=2)

@mcp.tool()
def delete_node(node_id: str) -> str:
    """Remove a node from the tailnet.

    Args:
        node_id: Node ID to remove
    """
    data = hs_delete(f"/api/v1/node/{node_id}")
    return json.dumps(data, indent=2)

@mcp.tool()
def expire_node(node_id: str) -> str:
    """Force a node to re-authenticate.

    Args:
        node_id: Node ID to expire
    """
    data = hs_post(f"/api/v1/node/{node_id}/expire")
    return json.dumps(data, indent=2)

@mcp.tool()
def move_node(node_id: str, user: str) -> str:
    """Move a node to a different user namespace.

    Args:
        node_id: Node ID to move
        user: Target username
    """
    data = hs_post(f"/api/v1/node/{node_id}/user?user={user}")
    return json.dumps(data, indent=2)

# ── Pre-auth keys ─────────────────────────────────────────────────────────────

@mcp.tool()
def list_preauthkeys(user: str) -> str:
    """List pre-authentication keys for a user.

    Args:
        user: Username whose keys to list
    """
    data = hs_get(f"/api/v1/preauthkey?user={user}")
    return json.dumps(data.get("preAuthKeys", []), indent=2)

@mcp.tool()
def create_preauthkey(user: str, reusable: bool = False, ephemeral: bool = False, expiration_seconds: int = 86400) -> str:
    """Create a pre-authentication key for node registration.

    Args:
        user: Username to create key for
        reusable: Allow key to be used multiple times
        ephemeral: Create ephemeral (auto-deleting) nodes
        expiration_seconds: Key validity in seconds (default: 86400 = 1 day)
    """
    from datetime import datetime, timedelta, timezone
    expiry = (datetime.now(timezone.utc) + timedelta(seconds=expiration_seconds)).isoformat()
    payload = {
        "user": user,
        "reusable": reusable,
        "ephemeral": ephemeral,
        "expiration": expiry,
        "aclTags": []
    }
    data = hs_post("/api/v1/preauthkey", payload)
    return json.dumps(data, indent=2)

@mcp.tool()
def expire_preauthkey(user: str, key: str) -> str:
    """Expire (invalidate) a pre-authentication key.

    Args:
        user: Username the key belongs to
        key: The key string to expire
    """
    data = hs_post("/api/v1/preauthkey/expire", {"user": user, "key": key})
    return json.dumps(data, indent=2)

# ── Routes ────────────────────────────────────────────────────────────────────

@mcp.tool()
def list_routes() -> str:
    """List all advertised subnet routes across all nodes."""
    data = hs_get("/api/v1/routes")
    return json.dumps(data.get("routes", []), indent=2)

@mcp.tool()
def enable_route(route_id: str) -> str:
    """Enable an advertised subnet route.

    Args:
        route_id: Route ID to enable
    """
    data = hs_post(f"/api/v1/routes/{route_id}/enable")
    return json.dumps(data, indent=2)

@mcp.tool()
def disable_route(route_id: str) -> str:
    """Disable a subnet route.

    Args:
        route_id: Route ID to disable
    """
    data = hs_post(f"/api/v1/routes/{route_id}/disable")
    return json.dumps(data, indent=2)

# ── API Keys ──────────────────────────────────────────────────────────────────

@mcp.tool()
def list_apikeys() -> str:
    """List all Headscale API keys."""
    data = hs_get("/api/v1/apikey")
    return json.dumps(data.get("apiKeys", []), indent=2)

@mcp.tool()
def create_apikey(expiration_days: int = 90) -> str:
    """Create a new Headscale API key.

    Args:
        expiration_days: Days until the key expires (default: 90)
    """
    from datetime import datetime, timedelta, timezone
    expiry = (datetime.now(timezone.utc) + timedelta(days=expiration_days)).isoformat()
    data = hs_post("/api/v1/apikey", {"expiration": expiry})
    return json.dumps(data, indent=2)

# ── DERP map ──────────────────────────────────────────────────────────────────

@mcp.tool()
def get_derp_map() -> str:
    """Retrieve the current DERP relay map from Headscale."""
    data = hs_get("/api/v1/derp_map")
    return json.dumps(data, indent=2)

# ── Auth middleware ───────────────────────────────────────────────────────────

class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests without correct Bearer token."""
    async def dispatch(self, request: Request, call_next):
        if not MCP_AUTH_TOKEN:
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {MCP_AUTH_TOKEN}":
            return Response("Unauthorized", status_code=401)
        return await call_next(request)

# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Headscale MCP Server")
    parser.add_argument("--transport", choices=["stdio", "streamable_http"], default="stdio")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    if args.transport == "streamable_http":
        import uvicorn
        app = mcp.streamable_http_app()
        app.add_middleware(TokenAuthMiddleware)
        print(f"[headscale-mcp] HTTP transport on :{args.port}/mcp", flush=True)
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        print("[headscale-mcp] stdio transport", flush=True)
        mcp.run()
