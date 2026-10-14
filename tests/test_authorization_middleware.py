from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastmcp.exceptions import ToolError

from ipam_mcp.middleware.authorization import (
    EntraRoleAuthorizationMiddleware,
)


def _tool(name: str, tags: set[str]):
    """Create minimal FastMCP-like tool metadata."""
    tool = Mock()
    tool.name = name
    tool.tags = tags
    return tool


def _context(tool_name: str = "get_sites"):
    """Create the minimum context required by the middleware."""

    fastmcp = Mock()
    fastmcp.get_tool = AsyncMock()

    return SimpleNamespace(
        message=SimpleNamespace(name=tool_name),
        fastmcp_context=SimpleNamespace(
            fastmcp=fastmcp,
        ),
    )


# ---------------------------------------------------------------------------
# tools/list
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_local_mode_exposes_all_tools():
    middleware = EntraRoleAuthorizationMiddleware()

    tools = [
        _tool("get_sites", {"read"}),
        _tool("add_ip_address", {"write"}),
    ]

    call_next = AsyncMock(return_value=tools)

    with patch.dict(
        "os.environ",
        {"AUTH_MODE": "local"},
    ):
        result = await middleware.on_list_tools(
            _context(),
            call_next,
        )

    assert result == tools

@pytest.mark.asyncio
async def test_read_only_mode_hides_write_tools():
    middleware = EntraRoleAuthorizationMiddleware()

    read_tool = _tool("get_sites", {"read"})
    write_tool = _tool("add_ip_address", {"write"})

    call_next = AsyncMock(
        return_value=[
            read_tool,
            write_tool,
        ]
    )

    with patch.dict(
        "os.environ",
        {
            "AUTH_MODE": "local",
            "IPAM_READ_ONLY": "true",
        },
    ):
        result = await middleware.on_list_tools(
            _context(),
            call_next,
        )

    assert result == [read_tool]

@pytest.mark.asyncio
async def test_local_mode_cannot_bypass_read_only():
    middleware = EntraRoleAuthorizationMiddleware()

    context = _context("add_ip_address")

    context.fastmcp_context.fastmcp.get_tool.return_value = (
        _tool(
            "add_ip_address",
            {"write"},
        )
    )

    call_next = AsyncMock()

    with patch.dict(
        "os.environ",
        {
            "AUTH_MODE": "local",
            "IPAM_READ_ONLY": "true",
        },
    ):
        with pytest.raises(
            ToolError,
            match="Write operations are disabled",
        ):
            await middleware.on_call_tool(
                context,
                call_next,
            )

    call_next.assert_not_awaited()

@pytest.mark.asyncio
async def test_write_role_cannot_bypass_read_only():
    middleware = EntraRoleAuthorizationMiddleware()

    context = _context("add_ip_address")

    context.fastmcp_context.fastmcp.get_tool.return_value = (
        _tool(
            "add_ip_address",
            {"write"},
        )
    )

    call_next = AsyncMock()

    with (
        patch.dict(
            "os.environ",
            {
                "AUTH_MODE": "entra",
                "IPAM_READ_ONLY": "true",
            },
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_http_headers",
            return_value={},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_entra_roles",
            return_value={"IPAM.Write"},
        ),
    ):
        with pytest.raises(
            ToolError,
            match="Write operations are disabled",
        ):
            await middleware.on_call_tool(
                context,
                call_next,
            )

    call_next.assert_not_awaited()

@pytest.mark.asyncio
async def test_no_role_exposes_no_tools():
    middleware = EntraRoleAuthorizationMiddleware()

    tools = [
        _tool("get_sites", {"read"}),
        _tool("add_ip_address", {"write"}),
    ]

    call_next = AsyncMock(return_value=tools)

    with (
        patch.dict(
            "os.environ",
            {"AUTH_MODE": "entra"},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_http_headers",
            return_value={},
        ),
    ):
        result = await middleware.on_list_tools(
            _context(),
            call_next,
        )

    assert result == []


@pytest.mark.asyncio
async def test_read_role_exposes_read_tools_only():
    middleware = EntraRoleAuthorizationMiddleware()

    read_tool = _tool("get_sites", {"read"})
    write_tool = _tool("add_ip_address", {"write"})

    call_next = AsyncMock(
        return_value=[
            read_tool,
            write_tool,
        ]
    )

    with (
        patch.dict(
            "os.environ",
            {"AUTH_MODE": "entra"},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_http_headers",
            return_value={},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_entra_roles",
            return_value={"IPAM.Read"},
        ),
    ):
        result = await middleware.on_list_tools(
            _context(),
            call_next,
        )

    assert result == [read_tool]


@pytest.mark.asyncio
async def test_write_role_exposes_read_and_write_tools():
    middleware = EntraRoleAuthorizationMiddleware()

    read_tool = _tool("get_sites", {"read"})
    write_tool = _tool("add_ip_address", {"write"})

    call_next = AsyncMock(
        return_value=[
            read_tool,
            write_tool,
        ]
    )

    with (
        patch.dict(
            "os.environ",
            {"AUTH_MODE": "entra"},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_http_headers",
            return_value={},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_entra_roles",
            return_value={"IPAM.Write"},
        ),
    ):
        result = await middleware.on_list_tools(
            _context(),
            call_next,
        )

    assert result == [
        read_tool,
        write_tool,
    ]


@pytest.mark.asyncio
async def test_untagged_tool_is_hidden():
    middleware = EntraRoleAuthorizationMiddleware()

    tagged_tool = _tool("get_sites", {"read"})
    untagged_tool = _tool("internal_tool", set())

    call_next = AsyncMock(
        return_value=[
            tagged_tool,
            untagged_tool,
        ]
    )

    with (
        patch.dict(
            "os.environ",
            {"AUTH_MODE": "entra"},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_http_headers",
            return_value={},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_entra_roles",
            return_value={"IPAM.Write"},
        ),
    ):
        result = await middleware.on_list_tools(
            _context(),
            call_next,
        )

    assert result == [tagged_tool]


# ---------------------------------------------------------------------------
# tools/call
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_local_mode_allows_tool_execution():
    middleware = EntraRoleAuthorizationMiddleware()

    context = _context("add_ip_address")

    call_next = AsyncMock(
        return_value={"status": "success"}
    )

    with patch.dict(
        "os.environ",
        {"AUTH_MODE": "local"},
    ):
        result = await middleware.on_call_tool(
            context,
            call_next,
        )

    assert result == {"status": "success"}
    call_next.assert_awaited_once_with(context)


@pytest.mark.asyncio
async def test_read_role_can_execute_read_tool():
    middleware = EntraRoleAuthorizationMiddleware()

    context = _context("get_sites")
    context.fastmcp_context.fastmcp.get_tool.return_value = (
        _tool("get_sites", {"read"})
    )

    call_next = AsyncMock(
        return_value={"status": "success"}
    )

    with (
        patch.dict(
            "os.environ",
            {"AUTH_MODE": "entra"},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_http_headers",
            return_value={},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_entra_roles",
            return_value={"IPAM.Read"},
        ),
    ):
        result = await middleware.on_call_tool(
            context,
            call_next,
        )

    assert result == {"status": "success"}
    call_next.assert_awaited_once_with(context)


@pytest.mark.asyncio
async def test_read_role_cannot_execute_write_tool():
    middleware = EntraRoleAuthorizationMiddleware()

    context = _context("add_ip_address")

    context.fastmcp_context.fastmcp.get_tool.return_value = (
        _tool(
            "add_ip_address",
            {"write"},
        )
    )

    call_next = AsyncMock()

    with (
        patch.dict(
            "os.environ",
            {"AUTH_MODE": "entra"},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_http_headers",
            return_value={},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_entra_roles",
            return_value={"IPAM.Read"},
        ),
    ):
        with pytest.raises(
            ToolError,
            match="not authorized",
        ):
            await middleware.on_call_tool(
                context,
                call_next,
            )

    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_role_cannot_execute_tool():
    middleware = EntraRoleAuthorizationMiddleware()

    context = _context("get_sites")

    context.fastmcp_context.fastmcp.get_tool.return_value = (
        _tool(
            "get_sites",
            {"read"},
        )
    )

    call_next = AsyncMock()

    with (
        patch.dict(
            "os.environ",
            {"AUTH_MODE": "entra"},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_http_headers",
            return_value={},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_entra_roles",
            return_value=set(),
        ),
    ):
        with pytest.raises(ToolError):
            await middleware.on_call_tool(
                context,
                call_next,
            )

    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_write_role_can_execute_write_tool():
    middleware = EntraRoleAuthorizationMiddleware()

    context = _context("add_ip_address")

    context.fastmcp_context.fastmcp.get_tool.return_value = (
        _tool(
            "add_ip_address",
            {"write"},
        )
    )

    call_next = AsyncMock(
        return_value={"status": "success"}
    )

    with (
        patch.dict(
            "os.environ",
            {"AUTH_MODE": "entra"},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_http_headers",
            return_value={},
        ),
        patch(
            "ipam_mcp.middleware.authorization.get_entra_roles",
            return_value={"IPAM.Write"},
        ),
    ):
        result = await middleware.on_call_tool(
            context,
            call_next,
        )

    assert result == {"status": "success"}
    call_next.assert_awaited_once_with(context)