import logging
import os

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware, MiddlewareContext

from ipam_mcp.utils.auth import (
    get_allowed_tags,
    get_entra_roles,
)


logger = logging.getLogger("ipam_mcp.audit")


def _is_local_mode() -> bool:
    """Return True when Entra authorization is disabled for local development."""
    return os.getenv("AUTH_MODE", "entra").strip().lower() == "local"

def _is_read_only() -> bool:
    """Return True when write operations are disabled globally."""
    return (
        os.getenv("IPAM_READ_ONLY", "false")
        .strip()
        .lower()
        in {"true", "1", "yes"}
    )

class EntraRoleAuthorizationMiddleware(Middleware):

    async def on_list_tools(
        self,
        context: MiddlewareContext,
        call_next,
    ):
        tools = await call_next(context)

        # Deployment-level safety control.
        # Write tools are never exposed when read-only mode is enabled.
        if _is_read_only():
            tools = [
                tool
                for tool in tools
                if "write" not in set(tool.tags or [])
            ]

        # Local development bypasses Entra RBAC only.
        if _is_local_mode():
            return tools

        headers = get_http_headers()

        roles = get_entra_roles(headers)
        allowed_tags = get_allowed_tags(roles)

        # Fail closed in Entra mode.
        if not allowed_tags:
            return []

        return [
            tool
            for tool in tools
            if set(tool.tags or []) & allowed_tags
        ]

    async def on_call_tool(
        self,
        context: MiddlewareContext,
        call_next,
    ):
        tool_name = context.message.name

        tool = await context.fastmcp_context.fastmcp.get_tool(
            tool_name
        )

        tool_tags = set(tool.tags or [])

        # Deployment-level read-only mode cannot be bypassed by
        # local mode or by an IPAM.Write role.
        if _is_read_only() and "write" in tool_tags:
            logger.warning(
                "IPAM MCP write operation blocked by read-only mode",
                extra={
                    "microsoft.custom_event.name":
                        "IPAMMCPAuthorization",
                    "mcp_tool": tool_name,
                    "tool_tags":
                        ",".join(sorted(tool_tags)),
                    "authorization": "denied",
                    "status": "rejected",
                    "reason": "read_only_mode",
                },
            )

            raise ToolError(
                "Write operations are disabled by server policy."
            )

        # Local mode bypasses Entra RBAC only.
        if _is_local_mode():
            return await call_next(context)

        headers = get_http_headers()

        roles = get_entra_roles(headers)
        allowed_tags = get_allowed_tags(roles)

        if not tool_tags & allowed_tags:

            entra_user_id = headers.get(
                "x-ms-client-principal-id",
                "",
            )

            entra_user = headers.get(
                "x-ms-client-principal-name",
                "",
            )

            reason = (
                "no_ipam_role"
                if not allowed_tags
                else "insufficient_role"
            )

            logger.warning(
                "IPAM MCP authorization denied",
                extra={
                    "microsoft.custom_event.name":
                        "IPAMMCPAuthorization",
                    "entra_user_id": entra_user_id,
                    "entra_user": entra_user,
                    "entra_roles":
                        ",".join(sorted(roles)),
                    "mcp_tool": tool_name,
                    "tool_tags":
                        ",".join(sorted(tool_tags)),
                    "authorization": "denied",
                    "status": "rejected",
                    "reason": reason,
                },
            )

            raise ToolError(
                "You are not authorized to use this tool."
            )

        return await call_next(context)