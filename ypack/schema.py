"""
YAML configuration schema validation.

Uses jsonschema to validate the structure and types of the YAML
configuration before parsing into dataclasses.
"""

from __future__ import annotations

from typing import Any, Dict, List

# Schema is defined inline to avoid extra file dependencies.
# Only the top-level required fields are strictly enforced; optional
# sections are validated when present.

_STRING = {"type": "string"}
_BOOL = {"type": "boolean"}
_INT = {"type": "integer"}

_REGISTRY_ENTRY = {
    "type": "object",
    "properties": {
        "hive": {"type": "string", "enum": ["HKLM", "HKCU", "HKCR", "HKU", "HKCC"]},
        "key": _STRING,
        "name": _STRING,
        "value": _STRING,
        "type": {"type": "string", "enum": ["string", "expand", "dword"]},
        "view": {"type": "string", "enum": ["auto", "32", "64"]},
    },
    "required": ["key", "name", "value"],
}

_ENV_VAR = {
    "type": "object",
    "properties": {
        "name": _STRING,
        "value": _STRING,
        "scope": {"type": "string", "enum": ["system", "user"]},
        "remove_on_uninstall": _BOOL,
        "append": _BOOL,
    },
    "required": ["name", "value"],
}

_FILE_ASSOCIATION = {
    "type": "object",
    "properties": {
        "extension": _STRING,
        "prog_id": _STRING,
        "description": _STRING,
        "application": _STRING,
        "default_icon": _STRING,
        "verbs": {"type": "object", "additionalProperties": _STRING},
        "register_for_all_users": _BOOL,
    },
    "required": ["extension"],
}

_SYSTEM_REQUIREMENTS = {
    "type": "object",
    "properties": {
        "min_windows_version": _STRING,
        "min_free_space_mb": _INT,
        "min_ram_mb": _INT,
        "require_admin": _BOOL,
    },
}

_FILE_ENTRY = {
    "oneOf": [
        _STRING,
        {
            "type": "object",
            "properties": {
                "source": {"oneOf": [_STRING, {"type": "array", "items": _STRING}]},
                "download_url": _STRING,
                "destination": _STRING,
                "recursive": _BOOL,
                "checksum_type": _STRING,
                "checksum_value": _STRING,
                "decompress": _BOOL,
            },
            "required": ["source"],
        },
    ]
}

CONFIG_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["app"],
    "properties": {
        "app": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": _STRING,
                "version": _STRING,
                "publisher": _STRING,
                "description": _STRING,
                "install_icon": _STRING,
                "uninstall_icon": _STRING,
                "license": _STRING,
            },
        },
        "install": {
            "type": "object",
            "properties": {
                "install_dir": _STRING,
                "desktop_shortcut_target": _STRING,
                "start_menu_shortcut_target": _STRING,
                "registry_entries": {"type": "array", "items": _REGISTRY_ENTRY},
                "env_vars": {"type": "array", "items": _ENV_VAR},
                "file_associations": {"type": "array", "items": _FILE_ASSOCIATION},
                "system_requirements": _SYSTEM_REQUIREMENTS,
                "launch_on_finish": _STRING,
                "launch_on_finish_label": _STRING,
                "launch_in_background": _BOOL,
                "silent_install": _BOOL,
                "registry_key": _STRING,
                "registry_view": {"type": "string", "enum": ["auto", "32", "64"], "default": "auto"},
                "existing_install": {
                    "oneOf": [
                        {"type": "string", "enum": ["prompt_uninstall", "auto_uninstall", "overwrite", "abort", "none"]},
                        {
                            "type": "object",
                            "properties": {
                                "mode": {"type": "string", "enum": ["prompt_uninstall", "auto_uninstall", "overwrite", "abort", "none"], "default": "prompt_uninstall"},
                                "version_check": _BOOL,
                                "allow_multiple": _BOOL,
                                "uninstaller_args": _STRING,
                                "show_version_info": _BOOL,
                                "uninstall_wait_ms": _INT,
                            },
                        },
                    ],
                },
                # Legacy field — prefer existing_install.allow_multiple
                "allow_multiple_installations": _BOOL,
            },
        },
        "files": {"type": "array", "items": _FILE_ENTRY},
        "packages": {"type": "object"},
        "signing": {
            "type": "object",
            "properties": {
                "enabled": _BOOL,
                "certificate": _STRING,
                "password": _STRING,
                "timestamp_url": _STRING,
                "verify_signature": _BOOL,
                "checksum_type": _STRING,
                "checksum_value": _STRING,
            },
        },
        "update": {
            "type": "object",
            "properties": {
                "enabled": _BOOL,
                "update_url": _STRING,
                "download_url": _STRING,
                "backup_on_upgrade": _BOOL,
                "repair_enabled": _BOOL,
                "check_on_startup": _BOOL,
                "registry_hive": _STRING,
                "registry_key": _STRING,
            },
        },
        "logging": {
            "type": "object",
            "properties": {
                "enabled": _BOOL,
                "path": _STRING,
                "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]},
            },
        },
        "languages": {"type": "array", "items": _STRING},
        "variables": {"type": "object"},
        "custom_includes": {"type": "object"},
    },
}


class ConfigValidationError(Exception):
    """Raised when YAML configuration fails schema validation."""

    def __init__(self, errors: List[str]) -> None:
        self.errors = errors
        msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
        super().__init__(msg)


def validate_config(data: Any) -> None:
    """Validate *data* against :data:`CONFIG_SCHEMA`.

    Uses ``jsonschema`` when available; falls back to a lightweight
    built-in check (only top-level required keys) otherwise.

    Raises:
        ConfigValidationError: on validation failure.
    """
    try:
        import jsonschema  # type: ignore[import-untyped]
    except ImportError:
        # Lightweight fallback — only check required top-level keys
        _validate_fallback(data)
        return

    validator = jsonschema.Draft7Validator(CONFIG_SCHEMA)
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
    if errors:
        messages = [
            f"{'.'.join(str(p) for p in e.absolute_path) or '(root)'}: {e.message}"
            for e in errors
        ]
        raise ConfigValidationError(messages)


def _validate_fallback(data: Any) -> None:
    """Minimal validation without jsonschema."""
    errors: List[str] = []
    if not isinstance(data, dict):
        errors.append("Root element must be a mapping (dict)")
    else:
        if "app" not in data:
            errors.append("Missing required key: 'app'")
        elif not isinstance(data["app"], dict):
            errors.append("'app' must be a mapping")
        elif "name" not in data["app"]:
            errors.append("Missing required key: 'app.name'")
    if errors:
        raise ConfigValidationError(errors)
