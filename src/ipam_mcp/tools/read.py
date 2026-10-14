import ipaddress

from fastmcp import Context

from ipam_mcp.clients.solidserver import SolidServerClient


# ---------------------------------------------------------------------------
# Response formatters
# ---------------------------------------------------------------------------

def _format_site_details(sites_response: list[dict]) -> list[dict]:
    """Return the SOLIDserver site fields useful to an MCP client."""
    return [
        {
            "parent_site_name": site.get(
                "parent_site_name",
                "No parent site",
            ),
            "parent_site_id": site.get(
                "parent_site_id",
                "No parent site ID",
            ),
            "site_name": site.get("site_name"),
            "site_id": site.get("site_id"),
            "site_description": site.get(
                "site_description",
                "No description available",
            ),
        }
        for site in sites_response
    ]


def _format_subnet_details(subnets_response: list[dict]) -> list[dict]:
    """Return the SOLIDserver subnet fields useful to an MCP client."""
    return [
        {
            "subnet_name": subnet.get(
                "subnet_name",
                "No subnet name",
            ),
            "subnet_id": subnet.get(
                "subnet_id",
                "No subnet ID",
            ),
            "subnet_size": subnet.get(
                "subnet_size",
                "No size available",
            ),
            "subnet_ip_reserved_size": subnet.get(
                "subnet_ip_reserved_size",
                "No reserved size available",
            ),
            "start_ip": subnet.get(
                "start_hostaddr",
                "No start IP",
            ),
            "end_ip": subnet.get(
                "end_hostaddr",
                "No end IP",
            ),
            "parent_subnet_id": subnet.get(
                "parent_subnet_id"
            ),
            "parent_subnet_name": subnet.get(
                "parent_subnet_name"
            ),
            "subnet_level": subnet.get("subnet_level"),
            "subnet_belongs_to_site_id": subnet.get(
                "site_id",
                "No site ID",
            ),
            "subnet_belongs_to_site_name": subnet.get(
                "site_name",
                "No site name",
            ),
            "subnet_description": subnet.get(
                "subnet_description",
                "No description available",
            ),
        }
        for subnet in subnets_response
    ]


def _format_ip_details(ip_response: list[dict]) -> list[dict]:
    """Return the SOLIDserver IP fields useful to an MCP client."""
    return [
        {
            "ip_type": ip.get(
                "type",
                "No type available",
            ),
            "ip_id": ip.get(
                "ip_id",
                "No IP ID",
            ),
            "ip_address": ip.get("hostaddr"),
            "ip_name": ip.get(
                "ip_name",
                "No IP name",
            ),
            "ip_description": ip.get(
                "ip_description",
                "No description available",
            ),
            "ip_class_name": ip.get(
                "ip_class_name",
                "No class name",
            ),
            "subnet_id": ip.get(
                "subnet_id",
                "No subnet ID",
            ),
            "subnet_name": ip.get(
                "subnet_name",
                "No subnet name",
            ),
            "site_id": ip.get(
                "site_id",
                "No site ID",
            ),
            "site_name": ip.get(
                "site_name",
                "No site name",
            ),
        }
        for ip in ip_response
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def calculate_subnet_bounds(subnet_cidr: str) -> dict:
    """Calculate network and usable address boundaries for a CIDR."""

    network = ipaddress.ip_network(
        subnet_cidr,
        strict=False,
    )

    hosts = list(network.hosts())

    return {
        "start_ip_addr": str(network.network_address),
        "end_ip_addr": str(network.broadcast_address),
        "first_usable": (
            str(hosts[0])
            if hosts
            else str(network.network_address)
        ),
        "last_usable": (
            str(hosts[-1])
            if hosts
            else str(network.broadcast_address)
        ),
        "total_addresses": network.num_addresses,
    }


async def _get_client(ctx: Context) -> SolidServerClient:
    """Create a SOLIDserver client using credentials from MCP state."""

    username = await ctx.get_state("username")
    password = await ctx.get_state("password")

    return SolidServerClient(
        username=username,
        password=password,
    )


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------

def register_read_tools(mcp):

    # -----------------------------------------------------------------------
    # Site tools
    # -----------------------------------------------------------------------

    @mcp.tool(tags={"read"})
    async def get_sites(ctx: Context) -> dict:
        """Retrieve all IP spaces (sites) from SOLIDserver."""

        client = await _get_client(ctx)
        response = client.get("/rest/ip_site_list")

        if not response.text:
            return {
                "status": "error",
                "error": "No data returned from SOLIDserver",
            }

        return {
            "status": "success",
            "data": _format_site_details(response.json()),
        }

    @mcp.tool(tags={"read"})
    async def get_site_info(
        ctx: Context,
        site_id: str,
    ) -> dict:
        """Retrieve information about a specific IP site."""

        client = await _get_client(ctx)

        response = client.get(
            "/rest/ip_site_info",
            params={"site_id": site_id},
        )

        if not response.text:
            return {
                "status": "error",
                "error": "No data returned from SOLIDserver",
            }

        return {
            "status": "success",
            "data": _format_site_details(response.json()),
        }

    # -----------------------------------------------------------------------
    # Subnet tools
    # -----------------------------------------------------------------------

    @mcp.tool(tags={"read"})
    async def get_subnets(
        ctx: Context,
        site_name: str | None = None,
    ) -> dict:
        """Retrieve subnets, optionally filtered by site name."""

        client = await _get_client(ctx)

        params = {}

        if site_name:
            params["WHERE"] = f"site_name='{site_name}'"

        response = client.get(
            "/rest/ip_block_subnet_list",
            params=params,
        )

        if not response.text:
            return {
                "status": "error",
                "error": "No data returned from SOLIDserver",
            }

        return {
            "status": "success",
            "data": _format_subnet_details(response.json()),
        }

    @mcp.tool(tags={"read"})
    async def get_subnet_info(
        ctx: Context,
        subnet_id: int | None = None,
        subnet_name: str | None = None,
    ) -> dict:
        """Retrieve subnet information by subnet ID or name."""

        if subnet_id is None and subnet_name is None:
            return {
                "status": "error",
                "error": "subnet_id or subnet_name required",
            }

        client = await _get_client(ctx)

        if subnet_id is not None:
            where = f"subnet_id='{subnet_id}'"
        else:
            where = f"subnet_name='{subnet_name}'"

        response = client.get(
            "/rest/ip_block_subnet_list",
            params={"WHERE": where},
        )

        if not response.text:
            return {
                "status": "success",
                "data": (
                    f"{subnet_name or subnet_id} "
                    "entry does not exist in IPAM"
                ),
            }

        return {
            "status": "success",
            "data": _format_subnet_details(response.json()),
        }

    @mcp.tool(tags={"read"})
    async def subnet_exists(
        ctx: Context,
        subnet_addr: str,
        site_name: str | None = None,
        site_id: int | None = None,
    ) -> dict:
        """Check whether a subnet already exists in SOLIDserver."""

        client = await _get_client(ctx)

        bounds = calculate_subnet_bounds(subnet_addr)

        where = (
            f"start_hostaddr='{bounds['start_ip_addr']}' "
            f"and end_hostaddr='{bounds['end_ip_addr']}'"
        )

        if site_name:
            where += f" AND site_name='{site_name}'"

        if site_id is not None:
            where += f" AND site_id='{site_id}'"

        response = client.get(
            "/rest/ip_block_subnet_list",
            params={"WHERE": where},
        )

        if not response.text:
            return {
                "status": "success",
                "data": (
                    f"{subnet_addr} entry does not exist in IPAM"
                ),
            }

        return {
            "status": "success",
            "data": _format_subnet_details(response.json()),
        }

    # -----------------------------------------------------------------------
    # IP address tools
    # -----------------------------------------------------------------------

    @mcp.tool(tags={"read"})
    async def get_list_of_ips(
        ctx: Context,
        subnet_id: int | None = None,
    ) -> dict:
        """Retrieve IPv4 addresses, optionally filtered by subnet."""

        client = await _get_client(ctx)

        params = {}

        if subnet_id is not None:
            params["WHERE"] = f"subnet_id='{subnet_id}'"

        response = client.get(
            "/rest/ip_address_list",
            params=params,
        )

        if not response.text:
            return {
                "status": "error",
                "error": "No data returned from SOLIDserver",
            }

        return {
            "status": "success",
            "data": _format_ip_details(response.json()),
        }

    @mcp.tool(tags={"read"})
    async def get_ip_info(
        ctx: Context,
        ip_addr: str,
        name: str | None = None,
        subnet_id: str | None = None,
        ip_id: str | None = None,
    ) -> dict:
        """Retrieve metadata for a specific IPv4 address."""

        client = await _get_client(ctx)

        # Preserve the precedence of the original implementation while
        # constructing a single deterministic filter.
        if subnet_id:
            where = f"subnet_id='{subnet_id}'"
        elif name:
            where = f"name='{name}'"
        elif ip_addr:
            where = f"hostaddr='{ip_addr}'"
        elif ip_id:
            where = f"ip_id='{ip_id}'"
        else:
            return {
                "status": "error",
                "error": "An IP lookup value is required",
            }

        response = client.get(
            "/rest/ip_address_list",
            params={"WHERE": where},
        )

        if not response.text:
            return {
                "status": "success",
                "data": f"{ip_addr} entry does not exist in IPAM",
            }

        return {
            "status": "success",
            "data": _format_ip_details(response.json()),
        }

    @mcp.tool(tags={"read"})
    async def get_free_ips(
        ctx: Context,
        subnet_id: int,
        max_find: int = 5,
    ) -> dict:
        """Find available IPv4 addresses in a subnet."""

        client = await _get_client(ctx)

        response = client.get(
            "/rpc/ip_find_free_address",
            params={
                "subnet_id": str(subnet_id),
                "max_find": str(max_find),
            },
        )

        if not response.text:
            return {
                "status": "error",
                "error": "No data returned from SOLIDserver",
            }

        return {
            "status": "success",
            "data": _format_ip_details(response.json()),
        }

    @mcp.tool(tags={"read"})
    async def get_free_address_list(
        ctx: Context,
        subnet_id: int,
    ) -> dict:
        """Retrieve unassigned IPv4 addresses in a subnet."""

        client = await _get_client(ctx)

        response = client.get(
            "/rest/ip_free_address_list",
            params={"subnet_id": str(subnet_id)},
        )

        if not response.text:
            return {
                "status": "error",
                "error": "No data returned from SOLIDserver",
            }

        data = response.json()

        # Preserve the defensive filtering from the original implementation.
        filtered_data = [
            entry
            for entry in data
            if str(entry.get("subnet_id")) == str(subnet_id)
        ]

        return {
            "status": "success",
            "data": (
                _format_ip_details(filtered_data)
                if filtered_data
                else []
            ),
        }

    @mcp.tool(tags={"read"})
    async def get_used_address_list(
        ctx: Context,
        subnet_id: int,
    ) -> dict:
        """Retrieve assigned IPv4 addresses in a subnet."""

        client = await _get_client(ctx)

        response = client.get(
            "/rest/ip_used_address_list",
            params={"subnet_id": str(subnet_id)},
        )

        if not response.text:
            return {
                "status": "error",
                "error": "No data returned from SOLIDserver",
            }

        data = response.json()

        filtered_data = [
            entry
            for entry in data
            if str(entry.get("subnet_id")) == str(subnet_id)
        ]

        return {
            "status": "success",
            "data": (
                _format_ip_details(filtered_data)
                if filtered_data
                else []
            ),
        }

    # -----------------------------------------------------------------------
    # Pool tools
    # -----------------------------------------------------------------------

    @mcp.tool(tags={"read"})
    async def get_ip_pools(
        ctx: Context,
        site_name: str | None = None,
    ) -> dict:
        """Retrieve IP pools, optionally filtered by site."""

        client = await _get_client(ctx)

        params = {}

        if site_name:
            params["WHERE"] = f"site_name='{site_name}'"

        response = client.get(
            "/rest/ip_pool_list",
            params=params,
        )

        if not response.text:
            return {
                "status": "error",
                "error": "No data returned from SOLIDserver",
            }

        return {
            "status": "success",
            "data": response.json(),
        }

    @mcp.tool(tags={"read"})
    async def get_pool_info(
        ctx: Context,
        pool_id: int | None = None,
        pool_name: str | None = None,
    ) -> dict:
        """Retrieve details for a specific IP pool."""

        if pool_id is None and pool_name is None:
            return {
                "status": "error",
                "error": "pool_id or pool_name required",
            }

        client = await _get_client(ctx)

        if pool_id is not None:
            where = f"pool_id='{pool_id}'"
        else:
            where = f"pool_name='{pool_name}'"

        response = client.get(
            "/rest/ip_pool_list",
            params={"WHERE": where},
        )

        if not response.text:
            return {
                "status": "error",
                "error": "No data returned from SOLIDserver",
            }

        return {
            "status": "success",
            "data": response.json(),
        }