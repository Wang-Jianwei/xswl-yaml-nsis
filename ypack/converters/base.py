"""
Base converter interface for packaging tools.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..config import PackageConfig
from .context import BuildContext


class BaseConverter(ABC):
    """Abstract base class that every format converter must implement."""

    tool_name: str = "generic"

    # Default output file extension per tool (subclasses may override).
    output_extension: str = ".txt"

    def __init__(self, config: PackageConfig, raw_config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config
        self.raw_config = raw_config or getattr(config, "_raw_dict", {})
        self.ctx = BuildContext(
            config=config,
            raw_config=self.raw_config,
            target_tool=self.tool_name,
            config_dir=getattr(config, "_config_dir", ""),
        )

    # ------------------------------------------------------------------
    # Public API every converter MUST implement
    # ------------------------------------------------------------------

    @abstractmethod
    def convert(self) -> str:
        """Generate the full installer script as a string."""
        ...

    @abstractmethod
    def save(self, output_path: str) -> None:
        """Write the generated script to *output_path*."""
        ...

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def resolve_variables(self, text: str) -> str:
        """Convenience proxy to ``self.ctx.resolve``."""
        return self.ctx.resolve(text)

    def _warn_unsupported(self, feature: str) -> str:
        return f"; [UNSUPPORTED by {self.tool_name}] {feature}"
