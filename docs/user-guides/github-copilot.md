# VS Code + GitHub Copilot Setup

This guide shows how to connect **VS Code + GitHub Copilot** to the
Secure IPAM MCP Server.

For server-side authentication and authorization details, see [Microsoft
Entra Setup](entra-setup.md).

## Prerequisites

You need:

-   VS Code with MCP support and GitHub Copilot available
-   access to the deployed MCP server
-   permission to authenticate to the MCP resource
-   valid SOLIDserver/IPAM credentials
-   an assigned MCP role where Entra authorization is enabled

The server exposes tools according to your assigned access:

-   `IPAM.Read` - read tools
-   `IPAM.Write` - read and write tools

A deployment may also enable `IPAM_READ_ONLY`, which hides write tools
regardless of user role.

## MCP Configuration

Configure the remote server in your VS Code MCP configuration.

Use VS Code input variables so the IPAM password is not stored directly
in `mcp.json`.

Example:

``` json
{
  "inputs": [
    {
      "id": "ipam-username",
      "type": "promptString",
      "description": "SOLIDserver/IPAM username"
    },
    {
      "id": "ipam-password",
      "type": "promptString",
      "description": "SOLIDserver/IPAM password",
      "password": true
    }
  ],
  "servers": {
    "ipam": {
      "type": "http",
      "url": "https://<YOUR-MCP-SERVER>/ipam/mcp",
      "headers": {
        "X-IPAM-Username": "${input:ipam-username}",
        "X-IPAM-Password": "${input:ipam-password}"
      }
    }
  }
}
```

Replace only:

``` text
<YOUR-MCP-SERVER>
```

with the hostname of your deployed MCP server.

Do not commit real usernames, passwords, access tokens, tenant-specific
URLs, or other environment-specific values to a public repository.

## Connect

1.  Save the MCP configuration.
2.  Start or reconnect the `ipam` MCP server from VS Code.
3.  Complete the Microsoft Entra sign-in when prompted.
4.  Enter your SOLIDserver/IPAM username and password when VS Code
    requests the configured inputs.
5.  Verify that the MCP server connects and tools are discovered.

The OAuth client details do not normally need to be placed in this
`mcp.json` example when the supported VS Code flow can complete
discovery/authentication using the server's published OAuth metadata.

## Verify Tool Access

After connection, confirm that the expected tools are visible.

Examples:

``` text
IPAM.Read  -> read tools only
IPAM.Write -> read and write tools
```

If write tools are missing even with `IPAM.Write`, check whether the
server has:

``` env
IPAM_READ_ONLY=true
```

## Example Usage

Try a read operation first, for example:

``` text
Use the IPAM MCP server to list the available IPAM sites.
```

Once read access is working, use write operations only in an environment
where you are authorized and the server allows writes.

## Troubleshooting

### No tools are discovered

Check:

-   the MCP server connection is authenticated;
-   your Entra identity has `IPAM.Read` or `IPAM.Write`;
-   your authentication session reflects the latest role assignment;
-   the configured MCP URL ends with `/ipam/mcp`.

### Missing IPAM username or password

The Entra sign-in authenticates you to the MCP server. It does **not**
replace downstream SOLIDserver authentication.

Ensure both headers are configured:

``` text
X-IPAM-Username
X-IPAM-Password
```

and reconnect so VS Code prompts for the values.

### Read tools work but write tools are unavailable

Check:

-   you have `IPAM.Write`;
-   the current authentication session contains the updated role;
-   the deployment is not running with `IPAM_READ_ONLY=true`.

### Authentication or OAuth discovery fails

Verify the server-side Entra/Easy Auth and OAuth metadata configuration
described in [Microsoft Entra Setup](entra-setup.md).

## Security Notes

-   Do not hard-code the IPAM password in `mcp.json`.
-   Prefer VS Code's password input prompt for the downstream password.
-   Do not commit environment-specific MCP configuration containing
    credentials.
-   Entra authentication and downstream SOLIDserver authentication are
    separate.

See [Architecture](../architecture.md) for the full security model.
