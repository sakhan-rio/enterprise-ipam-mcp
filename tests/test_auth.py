import base64
import json

from ipam_mcp.utils.auth import (
    get_allowed_tags,
    get_entra_roles,
)


def _principal_header(roles: list[str]) -> str:
    principal = {
        "claims": [
            {
                "typ": "roles",
                "val": role,
            }
            for role in roles
        ]
    }

    return base64.b64encode(
        json.dumps(principal).encode()
    ).decode()


def test_read_role_allows_read_only():
    allowed = get_allowed_tags({"IPAM.Read"})

    assert allowed == {"read"}


def test_write_role_allows_read_and_write():
    allowed = get_allowed_tags({"IPAM.Write"})

    assert allowed == {"read", "write"}


def test_multiple_roles_are_combined():
    allowed = get_allowed_tags(
        {"IPAM.Read", "IPAM.Write"}
    )

    assert allowed == {"read", "write"}


def test_unknown_role_has_no_permissions():
    allowed = get_allowed_tags({"Unknown.Role"})

    assert allowed == set()


def test_no_role_has_no_permissions():
    assert get_allowed_tags(set()) == set()


def test_entra_roles_are_extracted_from_principal():
    headers = {
        "x-ms-client-principal": _principal_header(
            ["IPAM.Read"]
        )
    }

    roles = get_entra_roles(headers)

    assert roles == {"IPAM.Read"}


def test_multiple_entra_roles_are_extracted():
    headers = {
        "x-ms-client-principal": _principal_header(
            ["IPAM.Read", "IPAM.Write"]
        )
    }

    roles = get_entra_roles(headers)

    assert roles == {
        "IPAM.Read",
        "IPAM.Write",
    }


def test_missing_principal_returns_no_roles():
    assert get_entra_roles({}) == set()


def test_invalid_principal_returns_no_roles():
    headers = {
        "x-ms-client-principal": "not-valid-base64"
    }

    assert get_entra_roles(headers) == set()