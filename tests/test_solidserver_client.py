import base64
from unittest.mock import Mock, patch

import pytest
import requests

from ipam_mcp.clients.solidserver import SolidServerClient


@pytest.fixture
def mock_settings():
    settings = Mock()
    settings.base_url = "https://solidserver.example.com"
    settings.verify_ssl = True
    settings.ca_bundle = None
    return settings


@pytest.fixture
def client(mock_settings):
    with patch(
        "ipam_mcp.clients.solidserver.get_solidserver_settings",
        return_value=mock_settings,
    ):
        return SolidServerClient(
            username="test-user",
            password="test-password",
        )


def test_credentials_are_base64_encoded(client):
    expected_username = base64.b64encode(
        b"test-user"
    ).decode()

    expected_password = base64.b64encode(
        b"test-password"
    ).decode()

    assert client.headers["x-ipm-username"] == expected_username
    assert client.headers["x-ipm-password"] == expected_password


def test_tls_verification_enabled_by_default(client):
    assert client.verify is True


def test_custom_ca_bundle_is_used(mock_settings):
    mock_settings.ca_bundle = "/path/to/company-ca.pem"

    with patch(
        "ipam_mcp.clients.solidserver.get_solidserver_settings",
        return_value=mock_settings,
    ):
        client = SolidServerClient("user", "password")

    assert client.verify == "/path/to/company-ca.pem"


def test_get_builds_correct_request(client):
    response = Mock()
    response.raise_for_status = Mock()

    with patch(
        "ipam_mcp.clients.solidserver.requests.get",
        return_value=response,
    ) as mock_get:

        result = client.get(
            "/rest/ip_site_list",
            params={"WHERE": "site_name='example'"},
        )

    mock_get.assert_called_once_with(
        "https://solidserver.example.com/rest/ip_site_list",
        headers=client.headers,
        params={"WHERE": "site_name='example'"},
        verify=True,
        timeout=30,
    )

    response.raise_for_status.assert_called_once()
    assert result is response


def test_post_builds_correct_request(client):
    response = Mock()
    response.raise_for_status = Mock()

    with patch(
        "ipam_mcp.clients.solidserver.requests.post",
        return_value=response,
    ) as mock_post:

        result = client.post(
            "/rest/ip_add",
            params={"hostaddr": "192.0.2.10"},
        )

    mock_post.assert_called_once_with(
        "https://solidserver.example.com/rest/ip_add",
        headers=client.headers,
        params={"hostaddr": "192.0.2.10"},
        verify=True,
        timeout=30,
    )

    response.raise_for_status.assert_called_once()
    assert result is response


def test_http_error_is_propagated(client):
    response = Mock()

    response.raise_for_status.side_effect = (
        requests.HTTPError("401 Unauthorized")
    )

    with patch(
        "ipam_mcp.clients.solidserver.requests.get",
        return_value=response,
    ):
        with pytest.raises(requests.HTTPError):
            client.get("/rest/ip_site_list")