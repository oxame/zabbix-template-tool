"""ZTT command-line entrypoint."""

from ztt.api_exports import app
from ztt import promotion_cli as _promotion_cli  # noqa: F401

__all__ = ["app"]
