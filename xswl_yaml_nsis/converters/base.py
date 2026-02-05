"""
Base converter interfaces for packaging tools.
"""

from abc import ABC


class BaseConverter(ABC):
    """Base class for tool-specific converters."""

    tool_name = "generic"

    def __init__(self, config):
        self.config = config

    def _warn_unsupported(self, feature: str) -> str:
        """Return a standardized comment for unsupported features."""
        return f"; [UNSUPPORTED by {self.tool_name}] {feature}"