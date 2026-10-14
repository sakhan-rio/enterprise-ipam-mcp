# Microsoft Entra ID Setup — Secure IPAM MCP Server

This guide records the **configuration used by this reference architecture**, including the manifest adjustment and the OAuth interoperability issues encountered when connecting different MCP clients. Replace all placeholders with values from your own tenant. The application uses **Azure App Service Easy Auth** for token validation and FastMCP middleware for tool-level authorization.

## 1. Registration layout

| Registration | Purpose | Required configuration |
| --- | --- | --- |
| MCP API/resource | Represents the protected FastMCP endpoint | Application ID URI, delegated `access_as_user` scope, `IPAM.Read` and `IPAM.Write` app roles |
| MCP client | Represents the OAuth client initiating sign-in | Public-client settings where applicable, redirect URI, delegated API permission, consent |

Separate client registrations are useful when clients have different callback requirements. They are **not inherently mandatory** for every deployment. Do not put real tenant IDs, client IDs, or endpoints in this public repository.

## 2. Configure the MCP API app registration

1. In **Microsoft Entra ID → App registrations**, create/select a **single-tenant** API registration (or choose another tenant model deliberately).
2. Under **Expose an API**, set an Application ID URI, for example `api://<MCP-API-CLIENT-ID>`.
3. Add a delegated scope named `access_as_user`. The resulting full scope is `api://<MCP-API-CLIENT-ID>/access_as_user`.
4. Under **App roles**, create user/group roles with values **`IPAM.Read`** and **`IPAM.Write`**. Assign users/groups via the associated **Enterprise Application → Users and groups**.
5. Configure access-token version as described below, then save.

The role values must match `ROLE_PERMISSIONS` in `src/ipam_mcp/utils/auth.py`:

```python
ROLE_PERMISSIONS = {
    "IPAM.Read": {"read"},
    "IPAM.Write": {"read", "write"},
}
```

### Manifest: request v2 access tokens

**This was an important implementation change**, not an optional documentation detail. Open the **MCP API registration → Manifest** and locate the access-token-version property.

In the **current Microsoft Entra app manifest**, set:

```json
"requestedAccessTokenVersion": 2
```

Some **older Azure AD manifest representations** show the corresponding property as:

```json
"accessTokenAcceptedVersion": 2
```

**Edit the property actually present in your portal/manifest format; do not insert both names blindly.** Microsoft documents `requestedAccessTokenVersion` as the current manifest property; `null` or `1` yields v1 tokens, while `2` yields v2 tokens. Verify the token `ver`, issuer, and audience after making changes. Reauthenticate the MCP client to acquire a fresh token. [Microsoft access-token reference](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens).

> Setting the token version does **not** fix every OAuth problem. Audience/resource mismatches, redirect URI errors, client permissions, and discovery failures must be diagnosed separately.

## 3. Configure Azure App Service Easy Auth

1. Deploy the FastMCP application to Azure App Service.
2. Under **Authentication**, add **Microsoft Entra ID** using the MCP API registration and correct tenant issuer.
3. Require authentication for the MCP endpoint; for an API, returning **401** for unauthenticated requests is usually more appropriate than browser redirection.
4. Review **Allowed token audiences** so Easy Auth accepts only the intended MCP API audience(s). Do not add arbitrary audiences to work around token errors.
5. Confirm the client/tenant access restrictions appropriate to your deployment.
6. Set `AUTH_MODE=entra` for this hosted, protected deployment.

After Easy Auth validates a request, the app can read trusted identity headers:

```text
X-MS-CLIENT-PRINCIPAL
X-MS-CLIENT-PRINCIPAL-ID
X-MS-CLIENT-PRINCIPAL-NAME
```

`get_entra_roles()` decodes the base64 JSON principal and extracts `roles` claims. `EntraRoleAuthorizationMiddleware` filters `tools/list` and separately authorizes `tools/call`. No recognized role means no tools; `IPAM_READ_ONLY=true` blocks writes even for `IPAM.Write`.

**Trust boundary:** never expose `AUTH_MODE=entra` behind a proxy that allows callers to forge these identity headers. Easy Auth must be the enforcing boundary, and direct bypass paths must be prevented.

**Health-check lesson:** enabling Easy Auth caused anonymous `/health` probes in the deployment pipeline to receive `401`. A successful deployment must use an authorized readiness probe or a narrowly scoped, intentionally public health endpoint; do not disable MCP authentication to make the pipeline pass.

## 4. MCP OAuth discovery and resource metadata

The deployed MCP resource must advertise its authorization server and scope. Use the protected-resource metadata mechanism supported by the installed MCP/FastMCP version; the standards-based path is `/.well-known/oauth-protected-resource` (including path-qualified variants where relevant).

Conceptual response (not a ready-to-deploy route implementation):

```json
{
  "resource": "https://mcp.example.com/ipam/mcp",
  "authorization_servers": [
    "https://login.microsoftonline.com/<TENANT-ID>/v2.0"
  ],
  "scopes_supported": [
    "api://<MCP-API-CLIENT-ID>/access_as_user"
  ]
}
```

Our original deployment also exposed custom discovery metadata at `/.well-known/mcp-oidc`. **Do not assume that this custom endpoint alone satisfies modern MCP protected-resource metadata discovery.** Verify the actual `401`/`WWW-Authenticate` behavior and metadata URL used by each client. The metadata `resource` identifier must be consistent with the resource the client requests. See [RFC 9728](https://www.rfc-editor.org/rfc/rfc9728.html) and the [MCP authorization specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization).

## 5. Configure OAuth client registrations

For each client registration that requires one:

1. Register the correct **redirect URI** (scheme, hostname, port, and path must match the client).
2. Enable the appropriate **public client** configuration for a desktop/CLI client; use authorization code + PKCE where supported.
3. Under **API permissions**, add delegated access to the MCP API's `access_as_user` scope and complete consent according to tenant policy.
4. Use that **client registration's client ID** in the MCP client configuration, not the MCP API's ID.
5. Keep secrets out of `mcp.json`, shell history, source control, and documentation.

For Claude Code, a working local callback pattern from testing was:

```text
http://localhost:8765/callback
```

Illustrative command (all deployment values are placeholders):

```bash
claude mcp add \
  --transport http \
  --scope local \
  --client-id "<CLAUDE-CLIENT-ID>" \
  --callback-port 8765 \
  ipam \
  "https://mcp.example.com/ipam/mcp"
```

This command demonstrates the OAuth portion only. Downstream IPAM credentials must also be configured using the client guide and handled securely. See [Claude Code](claude-code.md) and [GitHub Copilot](github-copilot.md).

## 6. Claude Code OAuth resource mismatch — observed finding

During our integration, Claude Code generated an authorization request with:

```text
resource=https://mcp.example.com/ipam/mcp
scope=api://<MCP-API-CLIENT-ID>/access_as_user offline_access
redirect_uri=http://localhost:8765/callback
```

The **full MCP endpoint** was used as the OAuth `resource`, not merely the App Service origin. The existing Entra API registration/identifier configuration did not initially accept the resource request. After aligning the recognized resource identifier and client registration configuration, Claude Code authentication succeeded.

**Do not blindly replace the API Application ID URI or add a second manifest property.** Check the exact request, the registered resource identifiers, the issued token's `aud`, and Easy Auth's allowed audiences as one consistent set. A workaround for one client is not necessarily required by another.

This is why a client that works in VS Code/GitHub Copilot may fail in Claude Code even when the same MCP endpoint and API scope are used.

## 7. Troubleshooting from implementation

| Symptom | Check / resolution |
| --- | --- |
| OAuth discovery returns 404 | Verify the tenant-specific issuer and actual discovery URL. A failed URL such as `login.microsoftonline.com/.well-known/.../<tenant>/v2.0` is not interchangeable with `login.microsoftonline.com/<tenant>/v2.0/.well-known/openid-configuration`. Confirm the URL used by the client. |
| Redirect or authorization fails quickly | Capture the browser authorization URL before redirect; inspect `client_id`, `redirect_uri`, `scope`, `resource`, `response_type`, `code_challenge_method`. |
| Token version warning or unexpected token `ver` | Check the **API** manifest's `requestedAccessTokenVersion` (or legacy `accessTokenAcceptedVersion`) and obtain a fresh token. |
| Resource/audience mismatch | Compare the OAuth `resource`, registered API identifier(s), token `aud`, and App Service allowed audiences. |
| OAuth works but zero tools appear | Verify Easy Auth principal headers and current `roles` claims; no recognized role intentionally yields zero tools. |
| Write tools missing despite `IPAM.Write` | Check token freshness and `IPAM_READ_ONLY`. Role reassignment typically requires reauthentication/token refresh, **not** an App Service restart. |
| Local server shows zero tools | Use `AUTH_MODE=local` only for loopback development; `entra` mode expects trusted Easy Auth identity headers. |
| Deployment health probe returns 401 | Use an authenticated readiness check or explicitly designed public health endpoint; do not open the MCP endpoint. |

For debugging, never paste full bearer tokens, authorization codes, passwords, or real internal URLs into public issues or screenshots.

## 8. Validation checklist

- [ ] MCP API registration and Application ID URI configured
- [ ] `access_as_user` scope exposed and consented
- [ ] Access-token manifest property set appropriately and fresh v2 token verified
- [ ] `IPAM.Read` and `IPAM.Write` roles created and assigned
- [ ] Easy Auth protects the MCP endpoint and accepts only intended audiences
- [ ] Protected-resource metadata is reachable and consistent with the MCP resource URL
- [ ] OAuth client registration has correct redirect URI and delegated permission
- [ ] GitHub Copilot and/or Claude Code completes OAuth and discovers expected tools
- [ ] `IPAM.Read` cannot call write tools directly
- [ ] `IPAM_READ_ONLY` behavior tested independently of user roles
- [ ] Health/readiness checks work without weakening MCP authentication

## Official references

- [Microsoft Entra access tokens and token version](https://learn.microsoft.com/en-us/entra/identity-platform/access-tokens)
- [Microsoft Entra authentication for Azure App Service](https://learn.microsoft.com/en-us/azure/app-service/configure-authentication-provider-aad)
- [Azure App Service authentication overview](https://learn.microsoft.com/en-us/azure/app-service/app-service-authentication-overview)
- [OAuth protected resource metadata (RFC 9728)](https://www.rfc-editor.org/rfc/rfc9728.html)
- [MCP authorization specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization)
