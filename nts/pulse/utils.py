"""Compatibility shim: keep old `nts.pulse.utils` imports working."""

from nts.utils import get_app_version, get_nts_version

__all__ = ["get_app_version", "get_nts_version"]
