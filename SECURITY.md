# Security

## Security Model

This project demonstrates a security-focused architecture for exposing EfficientIP SOLIDserver operations through MCP.

The implementation separates:

- **MCP authentication** — Microsoft Entra ID and Azure App Service Easy Auth
- **MCP authorization** — `IPAM.Read` / `IPAM.Write` App Roles
- **Deployment policy** — optional global `IPAM_READ_ONLY` enforcement
- **Downstream authentication** — separate SOLIDserver credentials
- **Observability** — sanitized audit events and tool traces

For the complete design, see [Architecture](docs/architecture.md).

## Deployment Assumptions

When `AUTH_MODE=entra` is used, the application assumes it is running behind a correctly configured Azure App Service Easy Auth boundary.

The application consumes authenticated principal information supplied by that trusted boundary. Do not expose an Entra-mode deployment where clients can bypass the authentication layer or inject trusted identity headers directly.

For local development, use:

```env
AUTH_MODE=local
```

rather than simulating production identity headers.

## Authorization

Authorization is enforced during both:

```text
tools/list
tools/call
```

Missing or unrecognized roles fail closed.

Write operations can additionally be disabled for the entire deployment:

```env
IPAM_READ_ONLY=true
```

This restriction cannot be overridden by `IPAM.Write` or local development mode.

## Credential Handling

The MCP client supplies downstream SOLIDserver credentials separately from the Entra identity.

Do not:

- commit SOLIDserver credentials;
- store passwords in `.env`;
- hard-code credentials in client configuration;
- log passwords or OAuth tokens;
- export credentials through OpenTelemetry;
- commit real tenant/client IDs, internal URLs, or environment-specific configuration to a public fork.

Use environment-appropriate secret and credential management for production deployments.

## TLS

TLS verification should remain enabled for deployed environments.

For private enterprise certificate authorities, configure the appropriate CA bundle rather than disabling certificate verification.

Disabling verification should be limited to controlled development scenarios.

## Telemetry

Audit events and traces may contain identity information such as user identifiers, roles, and IPAM usernames.

Review:

- privacy requirements;
- data classification;
- retention;
- access controls;
- data residency;

before enabling telemetry in a real environment.

Passwords, bearer tokens, complete request headers, and downstream response payloads must not be exported.

See [Observability](docs/observability.md).

## Reporting a Vulnerability

Please do not disclose suspected security vulnerabilities through a public GitHub issue.

Use GitHub's private vulnerability reporting feature when enabled for this repository.

Include:

- affected component;
- reproduction steps;
- potential impact;
- relevant logs with credentials and sensitive values removed.

## Scope

This repository is a reference implementation and should not be considered a complete production security baseline.

Production deployments should independently review identity configuration, network controls, secrets management, authorization governance, telemetry, rate limiting, availability, and downstream SOLIDserver permissions.