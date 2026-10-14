import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SolidServerSettings:
    base_url: str
    verify_ssl: bool = True
    ca_bundle: str | None = None


def get_solidserver_settings() -> SolidServerSettings:
    base_url = os.getenv("SOLIDSERVER_URL", "").rstrip("/")
    if not base_url:
        raise RuntimeError("SOLIDSERVER_URL must be configured")

    verify_ssl = os.getenv("SOLIDSERVER_VERIFY_SSL", "true").lower() in {"1", "true", "yes"}
    ca_bundle = os.getenv("SOLIDSERVER_CA_BUNDLE") or None
    return SolidServerSettings(base_url=base_url, verify_ssl=verify_ssl, ca_bundle=ca_bundle)
