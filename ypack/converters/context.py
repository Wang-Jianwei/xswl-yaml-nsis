"""
Build context shared across converter modules.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..config import PackageConfig


_PATH_SEPARATORS: Dict[str, str] = {
    "nsis": "\\",
    "wix": "\\",
    "inno": "\\",
}


@dataclass
class BuildContext:
    """Immutable context that every converter module can access.

    Centralises path resolution, variable resolution, and the raw
    configuration dictionary so that individual generator modules
    don't need to reach back into the converter or config objects.
    """

    config: PackageConfig
    raw_config: Dict[str, Any] = field(default_factory=dict)
    target_tool: str = "nsis"
    config_dir: str = ""
    output_dir: str = ""

    def __post_init__(self) -> None:
        if not self.config_dir:
            self.config_dir = getattr(self.config, "_config_dir", "") or os.getcwd()
        if not self.output_dir:
            self.output_dir = self.config_dir

        from ..resolver import create_resolver
        self._resolver = create_resolver(self.raw_config, self.target_tool)

    @property
    def path_separator(self) -> str:
        """Return the path separator for the current target tool."""
        return _PATH_SEPARATORS.get(self.target_tool, "\\")

    @property
    def effective_reg_view(self) -> str:
        """Resolve the effective registry view ('32' or '64').

        When ``registry_view`` is ``"auto"`` we derive the view from
        ``install_dir``:
        * ``$PROGRAMFILES64`` → ``"64"``
        * ``$PROGRAMFILES``   → ``"32"``
        * Otherwise           → ``"64"`` (safe default on modern Windows)
        """
        view = self.config.install.registry_view
        if view in ("32", "64"):
            return view
        # Auto-detect from install directory
        install_dir = self.config.install.install_dir.upper()
        if "$PROGRAMFILES64" in install_dir or "PROGRAMW6432" in install_dir:
            return "64"
        if "$PROGRAMFILES\\" in install_dir or install_dir.endswith("$PROGRAMFILES"):
            return "32"
        return "64"  # default for modern systems

    # ------------------------------------------------------------------
    # Variable resolution
    # ------------------------------------------------------------------

    def resolve(self, text: str) -> str:
        """Resolve all variable references in *text*."""
        if not text or not isinstance(text, str):
            return text
        return self._resolver.resolve(text)

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def resolve_path(self, path: str) -> str:
        """Return an absolute path, resolving relative to *config_dir*."""
        if not path:
            return path
        if os.path.isabs(path) and os.path.exists(path):
            return os.path.abspath(path)
        if os.path.exists(path):
            return os.path.abspath(path)
        if self.config_dir:
            candidate = os.path.abspath(os.path.join(self.config_dir, path))
            if os.path.exists(candidate):
                return candidate
        return path

    def relative_to_output(self, file_path: str) -> str:
        """Return *file_path* relative to *output_dir* for script references."""
        if not file_path:
            return file_path
        abs_path = self.resolve_path(file_path)
        sep = self.path_separator
        try:
            rel = os.path.relpath(abs_path, self.output_dir)
            return rel.replace("/", sep)
        except ValueError:
            return abs_path.replace("/", sep)
