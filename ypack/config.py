"""
Configuration parser for YAML packaging configuration.

All configuration data classes are defined here with proper ordering
to avoid forward reference issues.
"""

from __future__ import annotations

try:
    import yaml
except ImportError as e:
    raise ImportError(
        "PyYAML is required. Install with: pip install PyYAML"
    ) from e

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Leaf data classes (no forward references)
# ---------------------------------------------------------------------------

@dataclass
class AppInfo:
    """Application metadata."""
    name: str
    version: str
    publisher: str = ""
    description: str = ""
    install_icon: str = ""
    uninstall_icon: str = ""
    license: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AppInfo:
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            publisher=data.get("publisher", ""),
            description=data.get("description", ""),
            install_icon=data.get("install_icon", ""),
            uninstall_icon=data.get("uninstall_icon", data.get("install_icon", "")),
            license=data.get("license", ""),
        )


@dataclass
class RegistryEntry:
    """Registry entry written / removed by the installer."""
    hive: str = "HKLM"
    key: str = ""
    name: str = ""
    value: str = ""
    type: str = "string"   # "string" | "expand" | "dword"
    view: str = "auto"     # "auto" | "32" | "64"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RegistryEntry:
        return cls(
            hive=data.get("hive", "HKLM"),
            key=data.get("key", ""),
            name=data.get("name", ""),
            value=data.get("value", ""),
            type=data.get("type", "string"),
            view=data.get("view", "auto"),
        )


@dataclass
class EnvVarEntry:
    """Environment variable set / removed by the installer."""
    name: str = ""
    value: str = ""
    scope: str = "system"        # "system" (HKLM) | "user" (HKCU)
    remove_on_uninstall: bool = True
    append: bool = False         # PATH-append semantics

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EnvVarEntry:
        return cls(
            name=data.get("name", ""),
            value=data.get("value", ""),
            scope=data.get("scope", "system"),
            remove_on_uninstall=data.get("remove_on_uninstall", True),
            append=data.get("append", False),
        )


@dataclass
class FileAssociation:
    """File type association registered by the installer."""
    extension: str = ""
    prog_id: str = ""
    description: str = ""
    application: str = ""
    default_icon: str = ""
    verbs: Dict[str, str] = field(default_factory=dict)
    register_for_all_users: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FileAssociation:
        return cls(
            extension=data.get("extension", ""),
            prog_id=data.get("prog_id", ""),
            description=data.get("description", ""),
            application=data.get("application", ""),
            default_icon=data.get("default_icon", ""),
            verbs=data.get("verbs", {}),
            register_for_all_users=data.get("register_for_all_users", True),
        )


@dataclass
class SystemRequirements:
    """Pre-installation system checks."""
    min_windows_version: str = ""
    min_free_space_mb: int = 0
    min_ram_mb: int = 0
    require_admin: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SystemRequirements:
        return cls(
            min_windows_version=data.get("min_windows_version", ""),
            min_free_space_mb=int(data.get("min_free_space_mb", 0)),
            min_ram_mb=int(data.get("min_ram_mb", 0)),
            require_admin=data.get("require_admin", False),
        )


@dataclass
class SigningConfig:
    """Code-signing configuration."""
    enabled: bool = False
    certificate: str = ""
    password: str = ""
    timestamp_url: str = "http://timestamp.digicert.com"
    verify_signature: bool = False
    checksum_type: str = ""
    checksum_value: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SigningConfig:
        return cls(
            enabled=data.get("enabled", False),
            certificate=data.get("certificate", ""),
            password=data.get("password", ""),
            timestamp_url=data.get("timestamp_url", "http://timestamp.digicert.com"),
            verify_signature=data.get("verify_signature", False),
            checksum_type=data.get("checksum_type", ""),
            checksum_value=data.get("checksum_value", ""),
        )


@dataclass
class UpdateConfig:
    """Auto-update metadata written to the registry."""
    enabled: bool = False
    update_url: str = ""
    download_url: str = ""
    backup_on_upgrade: bool = False
    repair_enabled: bool = False
    check_on_startup: bool = True
    registry_hive: str = "HKLM"
    registry_key: str = "Software\\${app.name}"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> UpdateConfig:
        return cls(
            enabled=data.get("enabled", False),
            update_url=data.get("update_url", ""),
            download_url=data.get("download_url", ""),
            backup_on_upgrade=data.get("backup_on_upgrade", False),
            repair_enabled=data.get("repair_enabled", False),
            check_on_startup=data.get("check_on_startup", True),
            registry_hive=data.get("registry_hive", "HKLM"),
            registry_key=data.get("registry_key", "Software\\${app.name}"),
        )


@dataclass
class LoggingConfig:
    """Installer logging settings."""
    enabled: bool = False
    path: str = ""
    level: str = "INFO"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LoggingConfig:
        return cls(
            enabled=data.get("enabled", False),
            path=data.get("path", ""),
            level=data.get("level", "INFO"),
        )


# ---------------------------------------------------------------------------
# ExistingInstallConfig — rich policy for existing-install detection
# ---------------------------------------------------------------------------

@dataclass
class ExistingInstallConfig:
    """Policy for detecting and handling an existing installation.

    Modes:
    * ``prompt_uninstall`` – ask the user whether to uninstall first.
    * ``auto_uninstall``   – silently uninstall previous install.
    * ``overwrite``        – install over existing files.
    * ``abort``            – refuse to install.
    * ``none``             – skip detection entirely.
    """
    mode: str = "prompt_uninstall"
    # Version comparison: skip detection when the installed version equals
    # (or is older than) the current version.
    version_check: bool = False
    # Allow multiple independent installations in different directories.
    allow_multiple: bool = False
    # Extra CLI args to pass to the old uninstaller (e.g. "/S _?=$R1").
    uninstaller_args: str = ""
    # Show the installed version in the prompt dialog.
    show_version_info: bool = True
    # Wait (in ms) for the uninstaller to finish before continuing.
    uninstall_wait_ms: int = 15000  # default to 15s — better for heavier uninstallers

    @classmethod
    def from_dict(cls, data: Any) -> ExistingInstallConfig:
        # Backward compat: accept a plain string as shorthand for mode
        if isinstance(data, str):
            return cls(mode=data)
        if not isinstance(data, dict):
            return cls()
        return cls(
            mode=data.get("mode", "prompt_uninstall"),
            version_check=data.get("version_check", False),
            allow_multiple=data.get("allow_multiple", False),
            uninstaller_args=data.get("uninstaller_args", ""),
            show_version_info=data.get("show_version_info", True),
            uninstall_wait_ms=int(data.get("uninstall_wait_ms", 5000)),
        )


# ---------------------------------------------------------------------------
# InstallConfig — depends on the leaf types above
# ---------------------------------------------------------------------------

@dataclass
class InstallConfig:
    """Installation behaviour configuration."""
    install_dir: str = "$PROGRAMFILES64\\${APP_NAME}"
    desktop_shortcut_target: str = ""
    start_menu_shortcut_target: str = ""
    registry_entries: List[RegistryEntry] = field(default_factory=list)
    env_vars: List[EnvVarEntry] = field(default_factory=list)
    file_associations: List[FileAssociation] = field(default_factory=list)
    system_requirements: Optional[SystemRequirements] = None
    launch_on_finish: str = ""
    launch_on_finish_label: str = ""
    launch_in_background: bool = True
    silent_install: bool = False
    installer_name: str = ""
    # Rich existing-install detection policy
    existing_install: Optional[ExistingInstallConfig] = field(default_factory=ExistingInstallConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> InstallConfig:
        registry_entries = [
            RegistryEntry.from_dict(e)
            for e in data.get("registry_entries", [])
            if isinstance(e, dict)
        ]
        env_vars = [
            EnvVarEntry.from_dict(v)
            for v in data.get("env_vars", [])
            if isinstance(v, dict)
        ]
        file_associations = [
            FileAssociation.from_dict(fa)
            for fa in data.get("file_associations", [])
            if isinstance(fa, dict)
        ]
        sysreq = None
        sysreq_data = data.get("system_requirements")
        if isinstance(sysreq_data, dict):
            sysreq = SystemRequirements.from_dict(sysreq_data)

        # Parse existing_install — supports both string and dict
        ei_raw = data.get("existing_install", "prompt_uninstall")
        ei = ExistingInstallConfig.from_dict(ei_raw)
        # Legacy: allow_multiple_installations -> existing_install.allow_multiple
        if data.get("allow_multiple_installations"):
            ei.allow_multiple = True

        return cls(
            install_dir=data.get("install_dir", "$PROGRAMFILES64\\${APP_NAME}"),
            desktop_shortcut_target=data.get("desktop_shortcut_target", ""),
            start_menu_shortcut_target=data.get("start_menu_shortcut_target", ""),
            registry_entries=registry_entries,
            env_vars=env_vars,
            file_associations=file_associations,
            system_requirements=sysreq,
            launch_on_finish=data.get("launch_on_finish", ""),
            launch_on_finish_label=data.get("launch_on_finish_label", ""),
            launch_in_background=data.get("launch_in_background", True),
            silent_install=data.get("silent_install", False),
            installer_name=data.get("installer_name", ""),
            existing_install=ei,
        )


# ---------------------------------------------------------------------------
# FileEntry / PackageEntry
# ---------------------------------------------------------------------------

@dataclass
class FileEntry:
    """A single file / directory to be installed.

    *source* may be a local path or a remote URL (http:// / https://).
    """
    source: str
    destination: str = "$INSTDIR"
    recursive: bool = False
    checksum_type: str = ""
    checksum_value: str = ""
    decompress: bool = False

    @property
    def is_remote(self) -> bool:
        return self.source.startswith("http://") or self.source.startswith("https://")

    @classmethod
    def from_dict(cls, data: Any) -> FileEntry:
        if isinstance(data, str):
            return cls(source=data)
        source: str = data.get("source", "")
        download_url: str = data.get("download_url", "")
        if download_url and not source.startswith(("http://", "https://")):
            source = download_url
        return cls(
            source=source,
            destination=data.get("destination", "$INSTDIR"),
            recursive=data.get("recursive", False),
            checksum_type=data.get("checksum_type", ""),
            checksum_value=data.get("checksum_value", ""),
            decompress=data.get("decompress", False),
        )


@dataclass
class PackageEntry:
    """A component / package for modular installation."""
    name: str
    sources: List[Dict[str, str]]
    recursive: bool = True
    optional: bool = False
    default: bool = True
    description: str = ""
    children: List[PackageEntry] = field(default_factory=list)
    post_install: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> PackageEntry:
        # Children (nested SectionGroup)
        children: List[PackageEntry] = []
        children_data = data.get("children", {})
        if isinstance(children_data, dict):
            for child_name, child_data in children_data.items():
                if isinstance(child_data, dict):
                    children.append(PackageEntry.from_dict(child_name, child_data))

        # Sources — normalise many accepted input shapes
        sources_data = data.get("sources", data.get("source", []))
        sources: List[Dict[str, str]] = []
        default_dest = data.get("destination", "$INSTDIR")

        if isinstance(sources_data, str):
            sources = [{"source": sources_data, "destination": default_dest}]
        elif isinstance(sources_data, list):
            for item in sources_data:
                if isinstance(item, str):
                    sources.append({"source": item, "destination": default_dest})
                elif isinstance(item, dict):
                    src = item.get("source", "")
                    dest = item.get("destination", default_dest)
                    if isinstance(src, list):
                        for s in src:
                            sources.append({"source": s, "destination": dest})
                    else:
                        sources.append({"source": src, "destination": dest})

        # Post-install commands
        post_raw = data.get("post_install", [])
        if isinstance(post_raw, str):
            post_install = [post_raw]
        elif isinstance(post_raw, list):
            post_install = [str(x) for x in post_raw if x]
        else:
            post_install = []

        return cls(
            name=name,
            sources=sources,
            recursive=data.get("recursive", True),
            optional=data.get("optional", False),
            default=data.get("default", True),
            description=data.get("description", ""),
            children=children,
            post_install=post_install,
        )


# ---------------------------------------------------------------------------
# Top-level PackageConfig
# ---------------------------------------------------------------------------

@dataclass
class PackageConfig:
    """Root configuration object — parsed from a YAML file."""
    app: AppInfo
    install: InstallConfig
    files: List[FileEntry] = field(default_factory=list)
    packages: List[PackageEntry] = field(default_factory=list)
    signing: Optional[SigningConfig] = None
    update: Optional[UpdateConfig] = None
    logging: Optional[LoggingConfig] = None
    languages: List[str] = field(default_factory=lambda: ["English"])
    custom_includes: Dict[str, List[str]] = field(default_factory=dict)
    _raw_dict: Dict[str, Any] = field(default_factory=dict, repr=False)
    _config_dir: str = field(default="", repr=False)

    # ------------------------------------------------------------------
    # Constructors
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, yaml_path: str) -> PackageConfig:
        """Load and validate configuration from a YAML file."""
        import os
        with open(yaml_path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)

        from .schema import validate_config
        validate_config(data)

        config = cls._build(data)
        config._config_dir = os.path.dirname(os.path.abspath(yaml_path))
        return config

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PackageConfig:
        """Build configuration from a plain dictionary (tests, API)."""
        return cls._build(data)

    @classmethod
    def _build(cls, data: Dict[str, Any]) -> PackageConfig:
        return cls(
            app=AppInfo.from_dict(data.get("app", {})),
            install=InstallConfig.from_dict(data.get("install", {})),
            files=[FileEntry.from_dict(f) for f in data.get("files", [])],
            packages=[
                PackageEntry.from_dict(name, pkg)
                for name, pkg in data.get("packages", {}).items()
            ],
            signing=(
                SigningConfig.from_dict(data["signing"])
                if "signing" in data else None
            ),
            update=(
                UpdateConfig.from_dict(data["update"])
                if "update" in data else None
            ),
            logging=(
                LoggingConfig.from_dict(data["logging"])
                if "logging" in data else None
            ),
            languages=data.get("languages", ["English"]),
            custom_includes=data.get("custom_includes", {}),
            _raw_dict=data,
        )
