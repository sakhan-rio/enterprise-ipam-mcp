import base64

import requests

from ipam_mcp.utils.config import get_solidserver_settings


class SolidServerClient:
    """Client for the EfficientIP SOLIDserver REST API."""

    def __init__(self, username: str, password: str):
        self.settings = get_solidserver_settings()

        self.headers = {
            "x-ipm-username": base64.b64encode(
                username.encode()
            ).decode(),
            "x-ipm-password": base64.b64encode(
                password.encode()
            ).decode(),
            "cache-control": "no-cache",
        }

    @property
    def verify(self) -> bool | str:
        """Return TLS verification configuration."""
        return self.settings.ca_bundle or self.settings.verify_ssl

    def get(
        self,
        path: str,
        params: dict | None = None,
    ) -> requests.Response:
        response = requests.get(
            f"{self.settings.base_url.rstrip('/')}/{path.lstrip('/')}",
            headers=self.headers,
            params=params,
            verify=self.verify,
            timeout=30,
        )

        response.raise_for_status()
        return response

    def post(
        self,
        path: str,
        params: dict | None = None,
    ) -> requests.Response:
        response = requests.post(
            f"{self.settings.base_url.rstrip('/')}/{path.lstrip('/')}",
            headers=self.headers,
            params=params,
            verify=self.verify,
            timeout=30,
        )

        response.raise_for_status()
        return response