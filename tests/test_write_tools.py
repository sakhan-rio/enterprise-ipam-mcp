from unittest.mock import Mock

from ipam_mcp.tools.write import _parse_ip_write_response


def _response(data=None, text="response"):
    response = Mock()
    response.text = text

    if data is not None:
        response.json.return_value = data

    return response


def test_write_success():
    response = _response(
        {
            "errno": "0",
            "ret_oid": "12345",
            "msg": "Address created",
        }
    )

    result = _parse_ip_write_response(
        response,
        "IP address successfully added",
    )

    assert result["status"] == "success"
    assert result["ip_id"] == "12345"
    assert result["message"] == "Address created"


def test_write_success_when_response_is_list():
    response = _response(
        [
            {
                "errno": "0",
                "ret_oid": "12345",
                "msg": "Address created",
            }
        ]
    )

    result = _parse_ip_write_response(
        response,
        "IP address successfully added",
    )

    assert result["status"] == "success"
    assert result["ip_id"] == "12345"


def test_write_nonzero_errno_is_failure():
    response = _response(
        {
            "errno": "42",
            "ret_oid": "0",
            "errmsg": "Address already exists",
        }
    )

    result = _parse_ip_write_response(
        response,
        "IP address successfully added",
    )

    assert result["status"] == "error"
    assert result["errno"] == "42"
    assert result["message"] == "Address already exists"


def test_write_without_object_id_is_failure():
    response = _response(
        {
            "errno": "0",
            "ret_oid": "0",
            "msg": "No object created",
        }
    )

    result = _parse_ip_write_response(
        response,
        "IP address successfully added",
    )

    assert result["status"] == "error"


def test_empty_http_response_is_failure():
    response = _response(text="")

    result = _parse_ip_write_response(
        response,
        "IP address successfully added",
    )

    assert result["status"] == "error"


def test_empty_list_response_is_failure():
    response = _response([])

    result = _parse_ip_write_response(
        response,
        "IP address successfully added",
    )

    assert result["status"] == "error"