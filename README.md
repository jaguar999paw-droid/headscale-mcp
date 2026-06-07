# headscale-mcp

> MCP server for programmatic management of a self-hosted [Headscale](https://github.com/juanfont/headscale) control plane.

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

---

## What it does

Headscale is a self-hosted implementation of the Tailscale control plane. This server exposes its REST API as structured tools — so you can manage your private mesh network programmatically without touching the Headscale CLI directly.

**Covered operations:**
- User (namespace) management — create, list, delete
- Node management — list, register, delete, move between users
- Pre-auth key lifecycle — create, list, revoke
- Subnet route control — enable/disable advertised routes
- DERP map inspection

## Quickstart

```bash
git clone https://github.com/jaguar999paw-droid/headscale-mcp.git
cd headscale-mcp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

export HEADSCALE_URL=https://your-headscale-host:8080
export HEADSCALE_API_KEY=your-api-key

python server.py --transport stdio
```

## Configuration

| Variable | Description |
|---|---|
| `HEADSCALE_URL` | Base URL of your Headscale instance |
| `HEADSCALE_API_KEY` | API key from `headscale apikeys create` |

## Stack

`Python` · `FastMCP` · `httpx` · `Headscale REST API`

---

MIT License
