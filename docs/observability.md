# Observability

This guide documents the observability implemented by the Secure IPAM
MCP Server. It focuses on two complementary paths:

-   **Azure Application Insights** for structured audit and operational
    events.
-   **OpenTelemetry / Arize** for MCP tool execution traces.

Observability is intentionally separate from authentication and
authorization. A telemetry backend should not become part of the
authorization decision or the downstream SOLIDserver request path.

## Runtime Flow

``` text
MCP Tool Invocation
        |
        v
UserInfoMiddleware
        |
        +---- Structured audit event ----> Azure Application Insights
        |
        +---- OpenTelemetry TOOL span ----> Arize / OTLP
        |
        v
MCP Tool
        |
        v
SOLIDserver
```

## Telemetry Configuration

Telemetry is initialized when the MCP server starts.

Application Insights is enabled when:

``` env
APPLICATIONINSIGHTS_CONNECTION_STRING=<connection-string>
```

Arize tracing is enabled when both are present:

``` env
ARIZE_API_KEY=<api-key>
ARIZE_SPACE_ID=<space-id>
```

Optional Arize settings:

``` env
ARIZE_PROJECT_NAME=ipam-mcp-server
ARIZE_OTLP_ENDPOINT=https://otlp.arize.com/v1/traces
```

If only one of `ARIZE_API_KEY` or `ARIZE_SPACE_ID` is configured, Arize
tracing is disabled and the application emits a warning rather than
starting with a partially configured exporter.

The observability integrations are optional. The MCP server can run
without either backend.

## Application Insights Audit Events

The audit logger is:

``` text
ipam_mcp.audit
```

Azure Monitor OpenTelemetry is configured to export this logger to
Application Insights.

Tool invocation events use the custom event name:

``` text
IPAMMCPToolInvocation
```

Authorization denials use:

``` text
IPAMMCPAuthorization
```

### Tool Invocation Audit Data

Depending on the outcome, audit events can include:

``` text
entra_user_id
entra_user
entra_roles
ipam_username
mcp_tool
status
duration_ms
reason
```

The status is one of:

``` text
success
failure
rejected
```

`rejected` is used when the request is blocked before normal tool
execution, for example when required IPAM credentials are missing.

Authorization middleware can additionally record reasons such as:

``` text
no_ipam_role
insufficient_role
read_only_mode
```

## Determining Tool Success Correctly

A key implementation detail is that a completed MCP call does **not**
necessarily mean the downstream IPAM operation succeeded.

A tool can return a valid FastMCP result such as:

``` json
{
  "status": "error",
  "error": "Downstream operation failed"
}
```

without raising a Python exception.

The audit middleware therefore inspects:

``` python
result.structured_content
```

and reads:

``` text
structured_content.status
```

The audit result is determined from the tool result:

``` text
status == "success"  -> audit success
anything else        -> audit failure
```

This prevents downstream SOLIDserver failures from being incorrectly
recorded as successful MCP operations.

Unexpected Python exceptions are separately recorded as failures and
then re-raised so normal FastMCP error handling continues.

## OpenTelemetry Tool Spans

Each executed MCP tool is wrapped in an OpenTelemetry span named:

``` text
mcp.tool.<tool-name>
```

For example:

``` text
mcp.tool.get_sites
mcp.tool.add_ip_address
```

The span is marked as an OpenInference tool span:

``` text
openinference.span.kind = TOOL
```

Current span attributes can include:

``` text
tool.name
enduser.id
enduser.name
mcp.entra.roles
mcp.tool.status
mcp.tool.duration_ms
```

Span status is set to `OK` for successful tool results and `ERROR` for
failed tool results.

Identity attributes should be reviewed against the privacy and
governance requirements of the deployment before telemetry is exported
externally.

## Arize Export

Arize receives traces through the OTLP HTTP exporter.

The default trace endpoint is:

``` text
https://otlp.arize.com/v1/traces
```

Authentication headers are populated from:

``` text
ARIZE_API_KEY
ARIZE_SPACE_ID
```

A custom span processor restricts the Arize export to spans that:

1.  have a name beginning with `mcp.tool.`; and
2.  contain:

``` text
openinference.span.kind = TOOL
```

This avoids sending unrelated application spans through the
Arize-specific processor and keeps the integration focused on MCP tool
observability.

If Application Insights is configured at the same time, Azure Monitor
remains responsible for the audit/operational telemetry while the
additional span processor exports the selected tool traces to Arize.

## Sensitive Data Rules

The observability implementation handles identity information for audit
purposes, but credentials and request payloads must remain outside
telemetry.

### Allowed audit context

Depending on organizational requirements:

``` text
Entra user ID
Entra username
Entra roles
IPAM username
MCP tool name
status
duration
failure/rejection reason
```

### Never record

``` text
IPAM password
OAuth bearer/access token
Authorization header
complete request headers
SOLIDserver credential headers
complete downstream response payload
secrets or API keys
```

The IPAM password is read by middleware only so it can be placed in the
invocation context for downstream authentication. It is not added to the
audit event or OpenTelemetry span.

For a public or reusable deployment, review whether `enduser.name`,
`enduser.id`, and `ipam_username` should be exported at all. Identity
telemetry should follow the deployment's privacy, retention, and
data-governance requirements.

## Authorization Audit Events

Authorization is enforced separately from the tool invocation audit.

When a tool call is denied, the authorization middleware records context
including:

``` text
entra_user_id
entra_user
entra_roles
mcp_tool
tool_tags
authorization=denied
status=rejected
reason
```

This allows operators to distinguish:

``` text
authentication/authorization rejection
```

from:

``` text
authorized tool execution that later failed
```

The distinction is important when investigating access problems.

## Missing IPAM Credentials

The downstream IPAM credentials are checked during `tools/call`, not
during MCP initialization or `tools/list`.

If either credential is missing, the invocation is rejected with:

``` text
reason=missing_ipam_credentials
status=rejected
```

This allows MCP discovery to work independently of downstream
credentials while still ensuring that SOLIDserver calls cannot proceed
without them.

## Validation

After configuring Application Insights, invoke a read tool and verify
that an `IPAMMCPToolInvocation` event is available with the expected:

``` text
user
roles
tool
status
duration
```

Then validate a controlled failure, such as invalid downstream
credentials, and confirm that the resulting event is recorded as:

``` text
status=failure
```

rather than `success`.

For authorization testing, use a read-only role to attempt a write tool
and confirm an `IPAMMCPAuthorization` event with:

``` text
authorization=denied
status=rejected
```

For Arize, invoke a tool and verify that a span named:

``` text
mcp.tool.<tool-name>
```

appears with:

``` text
openinference.span.kind=TOOL
```

and the expected status and duration attributes.

## Troubleshooting

### Application Insights has no audit events

Check:

-   `APPLICATIONINSIGHTS_CONNECTION_STRING` is configured;
-   `configure_telemetry()` runs during server startup;
-   the `ipam_mcp.audit` logger is enabled at `INFO`;
-   the tool is actually being invoked;
-   Azure Monitor export/network access is available.

### Arize has no tool traces

Check:

-   both `ARIZE_API_KEY` and `ARIZE_SPACE_ID` are configured;
-   `ARIZE_OTLP_ENDPOINT` is correct if overridden;
-   outbound connectivity to the OTLP endpoint is available;
-   the span name begins with `mcp.tool.`;
-   `openinference.span.kind` is set to `TOOL`.

### Failed IPAM operations appear successful

Verify that the MCP tool returns a structured result containing:

``` json
{
  "status": "error"
}
```

and that the middleware is reading `result.structured_content.status`.

Do not determine audit success solely from the absence of an exception.

### Role denial is not visible as a tool failure

Authorization rejection is intentionally emitted as an
`IPAMMCPAuthorization` audit event rather than a completed tool
invocation. Query the authorization event stream when investigating
access denials.

## Design Summary

Application Insights and Arize serve different purposes in this
implementation:

  Concern                           Destination
  --------------------------------- ------------------------------
  Tool audit / operational events   Application Insights
  Authorization denials             Application Insights
  MCP tool execution traces         Arize via OpenTelemetry/OTLP

The key implementation rule is that observability must describe what
happened without becoming part of the security decision and without
exposing the credentials used to perform the operation.

See also:

-   [Architecture](architecture.md)
-   [Microsoft Entra Setup](entra-setup.md)
