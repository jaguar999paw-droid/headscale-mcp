# headscale-mcp

An [MCP](https://modelcontextprotocol.io) server that lets AI assistants manage a self-hosted [Headscale](https://github.com/juanfont/headscale) control plane through natural language — list nodes, issue pre-auth keys, approve routes, and more.

## Features

| Category | Tools |
|---|---|
| **Health** | `headscale_health` |
| **Users** | `list_users`, `create_user`, `delete_user` |
| **Nodes** | `list_nodes`, `delete_node`, `expire_node`, `move_node` |
| **Pre-auth keys** | `list_preauthkeys`, `create_preauthkey`, `expire_preauthkey` |
| **Routes** | `list_routes`, `enable_route`, `disable_route` |
| **API keys** | `list_apikeys`, `create_apikey` |
| **DERP** | `get_derp_map` |

## Quick start

### 1. Clone and configure

```bash
git clone https://github.com/jaguar999paw-droid/headscale-mcp
cd headscale-mcp
cp .env.example .env
```

Edit `.env` and fill in your values (see [Environment variables](#environment-variables) below).

Generate a `HEADSCALE_API_KEY` once Headscale is running:

```bash
docker exec -it headscale headscale apikeys create
```

### 2. Configure Headscale

```bash
cp headscale-config/config.yaml.example headscale-config/config.yaml
```

Edit `headscale-config/config.yaml` — at minimum set `server_url` to your domain or public IP.

### 3. Start the stack

```bash
docker compose up -d
```

Services:

| Service | Purpose | Required |
|---|---|---|
| `headscale` | control plane | Yes |
| `headscale-mcp` | this MCP server | Yes |
| `caddy` | TLS reverse proxy (LAN) | Optional |
| `cloudflared` | Cloudflare Tunnel | Optional |
| `duckdns` | Dynamic DNS updater | Optional |

Comment out optional services in `docker-compose.yml` if not needed.

### 4. Connect to Claude Desktop

**stdio (recommended — no network exposure):**

```json
{
  "mcpServers": {
    "headscale": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--network", "headscale-mcp_headscale_net",
        "-e", "HEADSCALE_URL=http://headscale:8080",
        "-e", "HEADSCALE_API_KEY=<your-api-key>",
        "headscale-mcp-headscale-mcp",
        "python3", "server.py", "--transport", "stdio"
      ]
    }
  }
}
```

**HTTP (if server is already running):**

```json
{
  "mcpServers": {
    "headscale": {
      "type": "streamable-http",
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer <your-MCP_AUTH_TOKEN>"
      }
    }
  }
}
```

## Architecture

```
Claude Desktop / any MCP client
        │  stdio or HTTP
        ▼
 headscale-mcp  (FastMCP, Python)
        │  REST  http://headscale:8080
        ▼
    Headscale   (control plane)
        │
   your nodes   (tailscale clients)
```

Optional ingress paths (choose one or both):

- **Caddy** — LAN TLS via ACME DNS challenge
- **Cloudflare Tunnel** — outbound-only; no open inbound ports required

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `HEADSCALE_URL` | Yes | Headscale API base URL (default: `http://headscale:8080`) |
| `HEADSCALE_API_KEY` | Yes | API key from `headscale apikeys create` |
| `MCP_AUTH_TOKEN` | Recommended | Bearer token protecting the MCP HTTP endpoint |
| `DUCKDNS_TOKEN` | Optional | DuckDNS API token for dynamic DNS |
| `DUCKDNS_SUBDOMAIN` | Optional | Your DuckDNS subdomain (without `.duckdns.org`) |
| `CLOUDFLARE_TUNNEL_TOKEN` | Optional | Token from Cloudflare Zero Trust tunnel |
| `TZ` | Optional | Container timezone (default: `UTC`) |

## Development

Run locally against an existing Headscale instance:

```bash
pip install -r requirements.txt
export HEADSCALE_URL=http://localhost:8085
export HEADSCALE_API_KEY=hskey-api-...
python server.py --transport stdio                          # Claude Desktop
python server.py --transport streamable_http --port 8000   # HTTP clients
```

## License

MIT
