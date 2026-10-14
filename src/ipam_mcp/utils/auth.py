import base64
import json

ROLE_PERMISSIONS = {
    "IPAM.Read": {"read"},
    "IPAM.Write": {"read", "write"},
}


def get_entra_roles(headers) -> set[str]:
    principal = headers.get("x-ms-client-principal", "")
    if not principal:
        return set()
    try:
        claims = json.loads(base64.b64decode(principal)).get("claims", [])
        return {c["val"] for c in claims if c.get("typ") == "roles"}
    except (ValueError, json.JSONDecodeError, KeyError):
        return set()


def get_allowed_tags(roles: set[str]) -> set[str]:
    allowed = set()
    for role in roles:
        allowed.update(ROLE_PERMISSIONS.get(role, set()))
    return allowed
