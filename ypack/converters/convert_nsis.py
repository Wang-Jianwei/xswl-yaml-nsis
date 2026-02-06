"""
YAML → NSIS script converter.

This is the main entry point that assembles the output from
the various sub-modules (header, sections, packages, helpers).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..config import PackageConfig
from .base import BaseConverter
from .context import BuildContext
from .nsis_header import (
    generate_custom_includes,
    generate_general_settings,
    generate_header,
    generate_modern_ui,
)
from .nsis_helpers import generate_checksum_helper, generate_log_macros, generate_path_helpers
from .nsis_packages import (
    generate_oninit,
    generate_package_sections,
    generate_signing_section,
    generate_update_section,
)
from .nsis_sections import generate_installer_section, generate_uninstaller_section


class YamlToNsisConverter(BaseConverter):
    """Converts a :class:`PackageConfig` into a complete NSIS script."""

    tool_name = "nsis"
    output_extension = ".nsi"

    def __init__(self, config: PackageConfig, raw_config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config, raw_config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(self) -> str:  # noqa: D102
        parts: List[str] = []

        # Header (unicode, defines, icons)
        parts.extend(generate_header(self.ctx))
        parts.extend(generate_custom_includes(self.ctx))
        parts.extend(generate_general_settings(self.ctx))
        parts.extend(generate_modern_ui(self.ctx))

        # Signing & update
        parts.extend(generate_signing_section(self.ctx))
        parts.extend(generate_update_section(self.ctx))

        # Logging macros (must come before sections that use them)
        if self.config.logging and self.config.logging.enabled:
            parts.extend(generate_log_macros())

        # PATH helpers (only when needed)
        needs_path_helpers = any(
            e.append for e in self.config.install.env_vars
        )
        if needs_path_helpers:
            parts.extend(generate_path_helpers(self.ctx))

        # Main install / uninstall
        parts.extend(generate_installer_section(self.ctx))
        parts.extend(generate_package_sections(self.ctx))
        parts.extend(generate_uninstaller_section(self.ctx))

        # .onInit
        parts.extend(generate_oninit(self.ctx))

        # Checksum / extract helpers (always emitted — lightweight stubs)
        has_remote = any(fe.is_remote for fe in self.config.files)
        has_checksum = any(fe.checksum_type for fe in self.config.files)
        if has_remote or has_checksum:
            parts.extend(generate_checksum_helper())

        return "\n".join(parts)

    def save(self, output_path: str) -> None:  # noqa: D102
        import os
        self.ctx.output_dir = os.path.dirname(os.path.abspath(output_path))
        script = self.convert()

        # Post-process: resolve any remaining configuration-style variables
        # (e.g. ${app.name}) that may appear in the final text. We only
        # resolve lowercase/dotted references to avoid touching NSIS defines
        # such as ${APP_NAME}.
        import re
        pattern = re.compile(r"\$\{([a-z][a-z0-9_.]*)\}")
        def _repl(m: re.Match) -> str:
            return self.ctx.resolve(m.group(0))
        script = pattern.sub(_repl, script)

        # NSIS requires the script file to be encoded as UTF-8 with BOM
        # when it contains Unicode characters. Use 'utf-8-sig' so Python
        # writes the BOM automatically at the start of the file.
        with open(output_path, "w", encoding="utf-8-sig") as fh:
            fh.write(script)
