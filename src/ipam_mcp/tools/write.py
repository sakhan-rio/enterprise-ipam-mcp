from fastmcp import Context

from ipam_mcp.clients.solidserver import SolidServerClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_client(ctx: Context) -> SolidServerClient:
    """Create a SOLIDserver client using credentials from MCP state."""

    username = await ctx.get_state("username")
    password = await ctx.get_state("password")

    return SolidServerClient(
        username=username,
        password=password,
    )


def _build_ip_params(
    hostaddr: str,
    site_name: str,
    add_flag: str,
    name: str | None = None,
    mac_addr: str | None = None,
    ip_class_name: str | None = None,
    ip_class_parameters: str | None = None,
) -> dict:
    """Build parameters for a SOLIDserver IPv4 add/edit operation."""

    params = {
        "hostaddr": hostaddr,
        "site_name": site_name,
        "add_flag": add_flag,
        "validate_warnings": "accept",
    }

    if name:
        params["name"] = name

    if mac_addr:
        params["mac_addr"] = mac_addr

    if ip_class_name:
        params["ip_class_name"] = ip_class_name

    if ip_class_parameters:
        params["ip_class_parameters"] = ip_class_parameters

    return params


def _parse_ip_write_response(
    response,
    success_message: str,
) -> dict:
    """Convert a SOLIDserver ip_add response into an MCP-friendly result."""

    if not response.text:
        return {
            "status": "error",
            "error": "No data returned from SOLIDserver",
        }

    data = response.json()

    # SOLIDserver may return the result wrapped in a list.
    if isinstance(data, list):
        if not data:
            return {
                "status": "error",
                "error": "Empty response returned from SOLIDserver",
            }

        data = data[0]

    errno = str(data.get("errno", "0"))
    ret_oid = str(data.get("ret_oid", "0"))

    if errno != "0":
        return {
            "status": "error",
            "errno": errno,
            "message": data.get(
                "errmsg",
                data.get(
                    "msg",
                    "SOLIDserver operation failed",
                ),
            ),
        }

    if ret_oid == "0":
        return {
            "status": "error",
            "errno": errno,
            "message": data.get(
                "errmsg",
                data.get(
                    "msg",
                    "SOLIDserver operation did not return an object ID",
                ),
            ),
        }

    return {
        "status": "success",
        "ip_id": ret_oid,
        "message": data.get(
            "msg",
            success_message,
        ),
    }


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

def register_write_tools(mcp):

    @mcp.tool(tags={"write"})
    async def add_ip_address(
        ctx: Context,
        hostaddr: str,
        site_name: str,
        name: str | None = None,
        mac_addr: str | None = None,
        ip_class_name: str | None = None,
        ip_class_parameters: str | None = None,
    ) -> dict:
        """
        Add a new IPv4 address to SOLIDserver IPAM.

        Use this tool to register an IPv4 address that does not already
        exist in the specified IPAM site. The operation uses SOLIDserver's
        new-only behavior and will not modify an existing address.

        Args:
            hostaddr: IPv4 address to register.
            site_name: IPAM site or space where the address belongs.
            name: Optional hostname or label for the address.
            mac_addr: Optional MAC address associated with the IP.
            ip_class_name: Optional SOLIDserver IP class.
            ip_class_parameters: Optional parameters for the IP class.

        Returns:
            Result containing the operation status and created IP object ID.
        """

        client = await _get_client(ctx)

        params = _build_ip_params(
            hostaddr=hostaddr,
            site_name=site_name,
            add_flag="new_only",
            name=name,
            mac_addr=mac_addr,
            ip_class_name=ip_class_name,
            ip_class_parameters=ip_class_parameters,
        )

        response = client.post(
            "/rest/ip_add",
            params=params,
        )

        return _parse_ip_write_response(
            response,
            success_message="IP address successfully added",
        )

    @mcp.tool(tags={"write"})
    async def edit_ip_address(
        ctx: Context,
        hostaddr: str,
        site_name: str,
        name: str | None = None,
        mac_addr: str | None = None,
        ip_class_name: str | None = None,
        ip_class_parameters: str | None = None,
    ) -> dict:
        """
        Update metadata for an existing IPv4 address in SOLIDserver IPAM.

        Use this tool only when the IPv4 address already exists. The
        operation uses SOLIDserver's edit-only behavior and will not
        create a new address if the requested address does not exist.

        Args:
            hostaddr: Existing IPv4 address to update.
            site_name: IPAM site or space containing the address.
            name: Optional updated hostname or label.
            mac_addr: Optional updated MAC address.
            ip_class_name: Optional updated SOLIDserver IP class.
            ip_class_parameters: Optional updated IP class parameters.

        Returns:
            Result containing the operation status and updated IP object ID.
        """

        client = await _get_client(ctx)

        params = _build_ip_params(
            hostaddr=hostaddr,
            site_name=site_name,
            add_flag="edit_only",
            name=name,
            mac_addr=mac_addr,
            ip_class_name=ip_class_name,
            ip_class_parameters=ip_class_parameters,
        )

        response = client.post(
            "/rest/ip_add",
            params=params,
        )

        return _parse_ip_write_response(
            response,
            success_message="IP address successfully updated",
        )