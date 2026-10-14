import logging
import time
from fastmcp.exceptions import McpError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from ipam_mcp.utils.auth import get_entra_roles

logger = logging.getLogger("ipam_mcp.audit")
tracer = trace.get_tracer(__name__)


class AuditMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        headers = get_http_headers()
        user_id = headers.get("x-ms-client-principal-id", "")
        roles = get_entra_roles(headers)
        username = headers.get("x-ipam-username", "")
        password = headers.get("x-ipam-password", "")
        tool_name = context.message.name
        if not username or not password:
            logger.warning("MCP tool rejected", extra={"mcp_tool": tool_name, "status": "rejected", "reason": "missing_ipam_credentials"})
            raise McpError(code=-32600, message="Missing IPAM username or password")

        await context.fastmcp_context.set_state("username", username)
        await context.fastmcp_context.set_state("password", password)
        started = time.perf_counter()
        with tracer.start_as_current_span(f"mcp.tool.{tool_name}") as span:
            span.set_attribute("openinference.span.kind", "TOOL")
            span.set_attribute("tool.name", tool_name)
            span.set_attribute("enduser.id", user_id)
            span.set_attribute("mcp.entra.roles", ",".join(sorted(roles)))
            try:
                result = await call_next(context)
                duration = round((time.perf_counter() - started) * 1000)
                content = getattr(result, "structured_content", None) or {}
                status = "success" if content.get("status") == "success" else "failure"
                span.set_attribute("mcp.tool.status", status)
                span.set_attribute("mcp.tool.duration_ms", duration)
                span.set_status(Status(StatusCode.OK if status == "success" else StatusCode.ERROR))
                logger.info("MCP tool completed", extra={"mcp_tool": tool_name, "status": status, "duration_ms": duration})
                return result
            except Exception:
                span.set_status(Status(StatusCode.ERROR))
                logger.exception("MCP tool failed", extra={"mcp_tool": tool_name, "status": "failure"})
                raise
