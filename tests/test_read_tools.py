from ipam_mcp.tools.read import (
    _format_ip_details,
    _format_site_details,
    _format_subnet_details,
    calculate_subnet_bounds,
)


def test_format_site_details():
    response = [
        {
            "site_name": "example-site",
            "site_id": "100",
            "site_description": "Example site",
            "parent_site_name": "parent-site",
            "parent_site_id": "10",
            "unused_vendor_field": "ignored",
        }
    ]

    result = _format_site_details(response)

    assert result == [
        {
            "parent_site_name": "parent-site",
            "parent_site_id": "10",
            "site_name": "example-site",
            "site_id": "100",
            "site_description": "Example site",
        }
    ]

    # Vendor fields not relevant to the MCP contract
    # should not leak into tool output.
    assert "unused_vendor_field" not in result[0]


def test_format_site_details_handles_missing_optional_fields():
    result = _format_site_details(
        [
            {
                "site_name": "example-site",
                "site_id": "100",
            }
        ]
    )

    assert result[0]["parent_site_name"] == "No parent site"
    assert result[0]["parent_site_id"] == "No parent site ID"
    assert result[0]["site_description"] == "No description available"


def test_format_subnet_details():
    response = [
        {
            "subnet_name": "example-subnet",
            "subnet_id": "200",
            "subnet_size": "256",
            "subnet_ip_reserved_size": "10",
            "start_hostaddr": "192.0.2.0",
            "end_hostaddr": "192.0.2.255",
            "parent_subnet_id": "20",
            "parent_subnet_name": "parent-subnet",
            "subnet_level": "2",
            "site_id": "100",
            "site_name": "example-site",
            "subnet_description": "Example subnet",
        }
    ]

    result = _format_subnet_details(response)

    assert result[0]["subnet_name"] == "example-subnet"
    assert result[0]["subnet_id"] == "200"
    assert result[0]["start_ip"] == "192.0.2.0"
    assert result[0]["end_ip"] == "192.0.2.255"
    assert result[0]["subnet_belongs_to_site_name"] == "example-site"


def test_format_ip_details():
    response = [
        {
            "type": "A",
            "ip_id": "300",
            "hostaddr": "192.0.2.10",
            "ip_name": "example-host",
            "ip_description": "Example address",
            "ip_class_name": "ExampleClass",
            "subnet_id": "200",
            "subnet_name": "example-subnet",
            "site_id": "100",
            "site_name": "example-site",
            "another_vendor_field": "ignored",
        }
    ]

    result = _format_ip_details(response)

    assert result == [
        {
            "ip_type": "A",
            "ip_id": "300",
            "ip_address": "192.0.2.10",
            "ip_name": "example-host",
            "ip_description": "Example address",
            "ip_class_name": "ExampleClass",
            "subnet_id": "200",
            "subnet_name": "example-subnet",
            "site_id": "100",
            "site_name": "example-site",
        }
    ]

    assert "another_vendor_field" not in result[0]


def test_calculate_subnet_bounds():
    result = calculate_subnet_bounds("192.0.2.0/24")

    assert result == {
        "start_ip_addr": "192.0.2.0",
        "end_ip_addr": "192.0.2.255",
        "first_usable": "192.0.2.1",
        "last_usable": "192.0.2.254",
        "total_addresses": 256,
    }


def test_calculate_subnet_bounds_accepts_host_address():
    result = calculate_subnet_bounds("192.0.2.42/24")

    assert result["start_ip_addr"] == "192.0.2.0"
    assert result["end_ip_addr"] == "192.0.2.255"


def test_calculate_small_subnet():
    result = calculate_subnet_bounds("192.0.2.0/31")

    assert result["start_ip_addr"] == "192.0.2.0"
    assert result["end_ip_addr"] == "192.0.2.1"
    assert result["total_addresses"] == 2