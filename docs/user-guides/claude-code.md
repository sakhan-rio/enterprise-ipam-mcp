# VS Code + Claude Code Setup

This guide shows how to connect **Claude Code running in VS Code** to
the Secure IPAM MCP Server.

Claude Code maintains its own MCP configuration. A server configured in
VS Code's `mcp.json` is not automatically available to Claude Code.

For the server-side OAuth configuration, see [Microsoft Entra
Setup](entra-setup.md).

## Prerequisites

You need:

-   Claude Code installed and available from the terminal
-   access to the deployed MCP server
-   an Entra OAuth client registration configured for Claude Code
-   the OAuth client ID
-   the registered local callback port
-   valid SOLIDserver/IPAM credentials
-   an assigned MCP role where Entra authorization is enabled

The server exposes tools according to your assigned access:

-   `IPAM.Read` - read tools
-   `IPAM.Write` - read and write tools

A deployment may additionally enforce `IPAM_READ_ONLY`.

## Set IPAM Credentials

Claude Code can pass HTTP headers when registering a remote MCP server.

For the tested setup, provide the downstream IPAM credentials through
environment variables rather than writing the actual values into the
command or project configuration.

For example:

``` bash
export IPAM_USERNAME="<your-ipam-username>"
export IPAM_PASSWORD="<your-ipam-password>"
```

How these variables are persisted is shell/environment specific. Avoid
committing credential values to repository files.

## Add the MCP Server

Use the Claude Code CLI:

``` bash
claude mcp add \
  --transport http \
  --scope local \
  --client-id "<CLAUDE-OAUTH-CLIENT-ID>" \
  --callback-port 8765 \
  --header "X-IPAM-Username: $IPAM_USERNAME" \
  --header "X-IPAM-Password: $IPAM_PASSWORD" \
  ipam \
  "https://<YOUR-MCP-SERVER>/ipam/mcp"
```

Replace:

``` text
<CLAUDE-OAUTH-CLIENT-ID>
<YOUR-MCP-SERVER>
```

with values from your own deployment.

`8765` is shown because the tested Claude configuration used:

``` text
http://localhost:8765/callback
```

The callback port must match the redirect URI configured on the
corresponding Entra client registration.

## Verify the Configuration

Run:

``` bash
claude mcp get ipam
```

A connected configuration should show values conceptually similar to:

``` text
Scope: Local
Status: Connected
Type: http
URL: https://<YOUR-MCP-SERVER>/ipam/mcp
OAuth: client_id configured, callback_port 8765
```

## Complete Entra Authentication

When Claude Code connects to the remote MCP server, complete the
browser-based Microsoft Entra sign-in.

The OAuth client registration used by Claude Code is separate from the
downstream SOLIDserver credentials.

Conceptually:

``` text
Claude Code
   |
   +-- Entra OAuth client ID -> authenticates to MCP server
   |
   +-- X-IPAM-Username
   +-- X-IPAM-Password       -> authenticate to SOLIDserver
```

## Verify Tool Access

After authentication, verify that Claude Code can discover the expected
tools.

Examples:

``` text
IPAM.Read  -> read tools only
IPAM.Write -> read and write tools
```

If the deployment has:

``` env
IPAM_READ_ONLY=true
```

write tools remain unavailable even to an `IPAM.Write` user.

## Example Usage

Start with a read operation:

``` text
Use the IPAM MCP server to list the available IPAM sites.
```

Confirm read access before testing any write operation.

## Important: Claude Code and VS Code MCP Configuration

Claude Code does not automatically consume the credentials or headers
configured for another VS Code MCP client.

For example, credentials defined in a VS Code `mcp.json` configuration
should not be assumed to become available to the Claude Code MCP
process.

For this implementation, Claude Code is configured independently
through:

``` text
claude mcp add
```

with the required HTTP headers supplied from the environment.

## OAuth Interoperability Note

During Entra integration, Claude Code generated an authorization request
containing an OAuth `resource` value corresponding to the full remote
MCP endpoint, conceptually:

``` text
resource=https://<YOUR-MCP-SERVER>/ipam/mcp
```

while requesting the delegated MCP API scope:

``` text
api://<MCP-API-CLIENT-ID>/access_as_user
```

The Entra configuration must recognize the resource identifier requested
by the client.

If authentication redirects fail, inspect the generated authorization
request and compare its:

``` text
client_id
redirect_uri
scope
resource
```

with the Entra API/client configuration.

The server-side setup and troubleshooting steps are documented in
[Microsoft Entra Setup](entra-setup.md).

## Troubleshooting

### `claude mcp add` reports a missing `name`

The command requires the MCP server name before the URL according to the
CLI syntax used above:

``` text
ipam
https://<YOUR-MCP-SERVER>/ipam/mcp
```

Use the complete command rather than supplying only the URL/options.

### OAuth redirect fails

Check:

-   `--client-id` matches the Claude OAuth client registration;
-   `--callback-port` matches the registered redirect URI;
-   the client registration is configured appropriately for the
    public-client flow;
-   the requested `resource` and delegated `scope` are recognized by
    Entra.

### MCP connects but tool calls report missing IPAM credentials

Check that the environment variables are populated in the shell from
which Claude Code is running:

``` bash
echo "$IPAM_USERNAME"
```

Avoid printing the password.

Then confirm the server registration includes:

``` text
X-IPAM-Username: $IPAM_USERNAME
X-IPAM-Password: $IPAM_PASSWORD
```

Reconnect Claude Code after correcting the environment.

### Credentials work in VS Code but not Claude Code

Treat the two clients as separate MCP configurations. Claude Code does
not automatically inherit the HTTP headers configured in VS Code's MCP
configuration.

### Read tools work but write tools are missing

Check:

-   your Entra identity has `IPAM.Write`;
-   you refreshed/re-authenticated after a role change;
-   the server is not configured with `IPAM_READ_ONLY=true`.

## Remove and Re-add the Server

If the local Claude MCP configuration needs to be recreated:

``` bash
claude mcp remove ipam -s local
```

Then run the `claude mcp add` command again.

## Security Notes

-   Do not put the actual IPAM password directly in the `claude mcp add`
    command.
-   Do not commit credential-bearing shell scripts or configuration.
-   Do not use an OAuth client secret for a public CLI client unless the
    client and identity architecture explicitly require and protect it.
-   Entra authentication and SOLIDserver authentication are separate
    security contexts.

See [Architecture](../architecture.md) for the full design.
