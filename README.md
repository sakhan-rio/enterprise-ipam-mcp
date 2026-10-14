# Secure IPAM MCP Server

A security-focused **Model Context Protocol (MCP)** reference implementation for **EfficientIP SOLIDserver**, built with **Python, FastMCP, Microsoft Entra ID, and OpenTelemetry**.

The project demonstrates how an existing enterprise REST API can be exposed to AI assistants while adding enterprise authentication, per-user tool authorization, downstream credential isolation, audit logging, and observability.

> This is a reference implementation for learning and architecture exploration. Review and adapt security, identity, networking, and operational controls before production use.

## Why This Project?

Connecting an enterprise REST API to MCP is relatively straightforward. The more interesting challenge is preserving enterprise security boundaries around it.

This project focuses on:

- authenticating users to a remote MCP server;
- authorizing different users for different MCP tools;
- enforcing authorization at both tool discovery and execution;
- separating MCP identity from downstream SOLIDserver credentials;
- disabling writes independently of user permissions;
- auditing and tracing tool activity without exposing credentials.

## Architecture

![Secure IPAM MCP Server reference architecture](https://raw.githubusercontent.com/sakhan-rio/enterprise-ipam-mcp/main/docs/images/architecture.png)

The architecture separates four concerns:

- **Authentication** - Microsoft Entra ID and Azure App Service Easy Auth
- **Authorization** - `IPAM.Read` / `IPAM.Write` with enforcement at `tools/list` and `tools/call`
- **Downstream authentication** - separate SOLIDserver credentials
- **Observability** - Application Insights audit logging and OpenTelemetry/Arize tool tracing

See [Architecture](docs/architecture.md) for the detailed design.

## Key Features

- FastMCP remote server using Streamable HTTP
- EfficientIP SOLIDserver REST API integration
- Microsoft Entra ID authentication through Azure App Service Easy Auth
- Entra App Role based authorization
- `read` and `write` tool classification
- fail-closed authorization
- deployment-level read-only mode
- separate downstream SOLIDserver authentication
- structured audit logging
- OpenTelemetry tool tracing
- optional Application Insights and Arize integrations
- local development mode without requiring Entra ID
- automated tests for client, tool, and authorization behavior

## Security Model

| Role | Tool access |
| --- | --- |
| `IPAM.Read` | Read tools |
| `IPAM.Write` | Read + write tools |

Authorization is enforced twice:

```text
                    tools/list              tools/call
IPAM.Read           Read visible            Read allowed
                    Write hidden             Write denied

IPAM.Write          Read + write visible    Read + write allowed

No valid role       No tools                Calls denied
```

Tool discovery is not treated as the security boundary.

An independent deployment policy can disable writes globally:

```env
IPAM_READ_ONLY=true
```

When enabled, write tools are hidden and direct write calls are rejected even for `IPAM.Write` users.

## MCP Tools

The server currently exposes **14 IPAM tools**.

### Read

`get_sites`, `get_site_info`, `get_subnets`, `get_subnet_info`, `subnet_exists`, `get_list_of_ips`, `get_ip_info`, `get_free_ips`, `get_free_address_list`, `get_used_address_list`, `get_ip_pools`, `get_pool_info`

### Write

`add_ip_address`, `edit_ip_address`

Tool responses expose focused, agent-friendly data instead of complete vendor API payloads.

## Quick Start

### Requirements

- Python 3.11+
- access to an EfficientIP SOLIDserver instance
- valid SOLIDserver credentials
- an MCP-compatible client

Microsoft Entra ID is not required for local development.

### Install

```bash
git clone <repository-url>
cd enterprise-ipam-mcp

python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Create local configuration:

```bash
cp .env.example .env
```

Example:

```env
SOLIDSERVER_URL=https://your-solidserver.example.com
AUTH_MODE=local
IPAM_READ_ONLY=true
SOLIDSERVER_VERIFY_SSL=true
```

Do not store SOLIDserver usernames or passwords in `.env`.

### Run

```bash
uvicorn ipam_mcp.server:app \
  --app-dir src \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

MCP endpoint:

```text
http://127.0.0.1:8000/ipam/mcp
```

`AUTH_MODE=local` bypasses Entra RBAC only. SOLIDserver authentication and `IPAM_READ_ONLY` remain enforced.

## Testing

```bash
pytest -v
```

Tests cover the SOLIDserver client, response formatting, write-result handling, Entra role mapping, discovery-time authorization, execution-time authorization, fail-closed behavior, local mode, and read-only enforcement.

Tests mock the SOLIDserver boundary and do not require a live IPAM environment.

## Documentation

| Guide | Description |
| --- | --- |
| [Architecture](docs/architecture.md) | Security boundaries and request flow |
| [Microsoft Entra Setup](docs/entra-setup.md) | OAuth, Easy Auth, scopes, App Roles and client configuration |
| [Observability](docs/observability.md) | Application Insights auditing and OpenTelemetry/Arize tracing |
| [VS Code + GitHub Copilot](docs/user-guides/github-copilot.md) | Connect and use the server with GitHub Copilot |
| [VS Code + Claude Code](docs/user-guides/claude-code.md) | Connect and use the server with Claude Code |

## Related Projects

Other community implementations include [solidserver-mcp](https://github.com/tphakala/solidserver-mcp), a Go-based MCP implementation covering broader DDI capabilities.

This project focuses on a complementary area: **enterprise identity, per-user MCP authorization, deployment policy, auditing, and OpenTelemetry-based observability around a remote SOLIDserver integration**.

## Security

Important considerations include least-privilege role assignments, execution-time authorization, read-only deployments where appropriate, TLS verification, credential protection, restricted downstream connectivity, and telemetry review.

See [Architecture](docs/architecture.md) and `SECURITY.md` for more detail.

## Vendor API

The integration uses the **EfficientIP SOLIDserver REST API**. This repository provides an MCP abstraction over vendor API operations and does not redistribute EfficientIP documentation or contain vendor credentials.

## Disclaimer

This is an independent reference implementation and is not an official project of EfficientIP, Microsoft, GitHub, Anthropic, Arize, or OpenAI.

Product names and trademarks belong to their respective owners. Example configuration, identifiers, network addresses, and test data are non-production examples.

## License

License information will be added before the first public release.
