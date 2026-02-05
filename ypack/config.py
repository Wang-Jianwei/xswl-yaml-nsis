"""
Configuration parser for YAML packaging configuration
"""

try:
    import yaml
except ImportError as e:
    raise ImportError("PyYAML is required. Install with: pip install PyYAML  OR pip install -r requirements.txt") from e

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class AppInfo:
    """Application information"""
    name: str
    version: str
    publisher: str = ""
    description: str = ""
    icon: str = ""
    license: str = ""
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppInfo":
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "1.0.0"),
            publisher=data.get("publisher", ""),
            description=data.get("description", ""),
            icon=data.get("icon", ""),
            license=data.get("license", "")
        )


@dataclass
class RegistryEntry:
    """Registry entry configuration for installer/uninstaller"""
    def __init__(self, hive: str, key: str, name: str, value: str, type: str = "string", view: str = "auto"):
        self.hive = hive
        self.key = key
        self.name = name
        self.value = value
        self.type = type  # "string", "expand", "dword"
        self.view = view  # "auto", "32", "64"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegistryEntry":
        return cls(
            hive=data.get("hive", "HKLM"),
            key=data.get("key", ""),
            name=data.get("name", ""),
            value=data.get("value", ""),
            type=data.get("type", "string"),
            view=data.get("view", "auto")
        )


@dataclass
class EnvVarEntry:
    """Environment variable configuration"""
    name: str
    value: str
    scope: str = "system"  # "system" (HKLM) or "user" (HKCU)
    remove_on_uninstall: bool = True
    append: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EnvVarEntry":
        return cls(
            name=data.get("name", ""),
            value=data.get("value", ""),
            scope=data.get("scope", "system"),
            remove_on_uninstall=data.get("remove_on_uninstall", True),
            append=data.get("append", False),
        )


@dataclass
class InstallConfig:
    """Installation configuration"""
    install_dir: str = "$PROGRAMFILES64\\${APP_NAME}"
    create_desktop_shortcut: bool = True
    create_start_menu_shortcut: bool = True
    registry_key: str = "Software\\${APP_NAME}"
    registry_entries: List[RegistryEntry] = field(default_factory=list)
    env_vars: List[EnvVarEntry] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InstallConfig":
        entries = []
        for e in data.get("registry_entries", []):
            if isinstance(e, dict):
                entries.append(RegistryEntry.from_dict(e))
        envs = []
        for v in data.get("env_vars", []):
            if isinstance(v, dict):
                envs.append(EnvVarEntry.from_dict(v))
        return cls(
            install_dir=data.get("install_dir", "$PROGRAMFILES64\\${APP_NAME}"),
            create_desktop_shortcut=data.get("create_desktop_shortcut", True),
            create_start_menu_shortcut=data.get("create_start_menu_shortcut", True),
            registry_key=data.get("registry_key", "Software\\${APP_NAME}"),
            registry_entries=entries,
            env_vars=envs,
        )


@dataclass
class FileEntry:
    """File entry for installation"""
    source: str
    destination: str = "$INSTDIR"
    recursive: bool = False
    
    @classmethod
    def from_dict(cls, data: Any) -> "FileEntry":
        if isinstance(data, str):
            return cls(source=data)
        return cls(
            source=data.get("source", ""),
            destination=data.get("destination", "$INSTDIR"),
            recursive=data.get("recursive", False)
        )


@dataclass
class PackageEntry:
    """Package/Component entry for modular installation"""
    name: str
    sources: List[Dict[str, str]]  # List of {source, destination} dicts
    recursive: bool = True
    optional: bool = False
    default: bool = True
    description: str = ""
    children: List["PackageEntry"] = field(default_factory=list)
    post_install: List[str] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "PackageEntry":
        # Handle nested children (SectionGroup)
        children_data = data.get("children", {})
        children_list: List[PackageEntry] = []
        if isinstance(children_data, dict):
            for child_name, child_data in children_data.items():
                if isinstance(child_data, dict):
                    children_list.append(PackageEntry.from_dict(child_name, child_data))

        # Handle sources as list of dicts or convert from old format
        sources_data = data.get("sources", data.get("source", []))
        sources_list = []
        
        if isinstance(sources_data, str):
            # Single source string (old format)
            sources_list = [{
                "source": sources_data,
                "destination": data.get("destination", "$INSTDIR")
            }]
        elif isinstance(sources_data, list):
            # List format - can be strings or dicts
            for item in sources_data:
                if isinstance(item, str):
                    # String source with package-level destination
                    sources_list.append({
                        "source": item,
                        "destination": data.get("destination", "$INSTDIR")
                    })
                elif isinstance(item, dict):
                    # Dict with source possibly being a string or a list of strings
                    src = item.get("source", "")
                    dest = item.get("destination", data.get("destination", "$INSTDIR"))
                    if isinstance(src, list):
                        for s in src:
                            sources_list.append({
                                "source": s,
                                "destination": dest
                            })
                    else:
                        sources_list.append({
                            "source": src,
                            "destination": dest
                        })
        
        # Handle post-install commands
        post_install_data = data.get("post_install", [])
        if isinstance(post_install_data, str):
            post_install_list = [post_install_data]
        elif isinstance(post_install_data, list):
            post_install_list = [str(x) for x in post_install_data if x]
        else:
            post_install_list = []

        return cls(
            name=name,
            sources=sources_list,
            recursive=data.get("recursive", True),
            optional=data.get("optional", False),
            default=data.get("default", True),
            description=data.get("description", ""),
            children=children_list,
            post_install=post_install_list,
        )


@dataclass
class SigningConfig:
    """Code signing configuration"""
    enabled: bool = False
    certificate: str = ""
    password: str = ""
    timestamp_url: str = "http://timestamp.digicert.com"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SigningConfig":
        return cls(
            enabled=data.get("enabled", False),
            certificate=data.get("certificate", ""),
            password=data.get("password", ""),
            timestamp_url=data.get("timestamp_url", "http://timestamp.digicert.com")
        )


@dataclass
class UpdateConfig:
    """Auto-update configuration"""
    enabled: bool = False
    update_url: str = ""
    check_on_startup: bool = True
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UpdateConfig":
        return cls(
            enabled=data.get("enabled", False),
            update_url=data.get("update_url", ""),
            check_on_startup=data.get("check_on_startup", True)
        )


@dataclass
class PackageConfig:
    """Main package configuration"""
    app: AppInfo
    install: InstallConfig
    files: List[FileEntry] = field(default_factory=list)
    packages: List[PackageEntry] = field(default_factory=list)
    signing: Optional[SigningConfig] = None
    update: Optional[UpdateConfig] = None
    languages: List[str] = field(default_factory=lambda: ["English"])
    custom_nsis_includes: List[str] = field(default_factory=list)
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> "PackageConfig":
        """Load configuration from YAML file"""
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return cls(
            app=AppInfo.from_dict(data.get("app", {})),
            install=InstallConfig.from_dict(data.get("install", {})),
            files=[FileEntry.from_dict(f) for f in data.get("files", [])],
            packages=[PackageEntry.from_dict(name, pkg_data) 
                     for name, pkg_data in data.get("packages", {}).items()],
            signing=SigningConfig.from_dict(data["signing"]) if "signing" in data else None,
            update=UpdateConfig.from_dict(data["update"]) if "update" in data else None,
            languages=data.get("languages", ["English"]),
            custom_nsis_includes=data.get("custom_nsis_includes", [])
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackageConfig":
        """Load configuration from dictionary"""
        return cls(
            app=AppInfo.from_dict(data.get("app", {})),
            install=InstallConfig.from_dict(data.get("install", {})),
            files=[FileEntry.from_dict(f) for f in data.get("files", [])],
            packages=[PackageEntry.from_dict(name, pkg_data) 
                     for name, pkg_data in data.get("packages", {}).items()],
            signing=SigningConfig.from_dict(data["signing"]) if "signing" in data else None,
            update=UpdateConfig.from_dict(data["update"]) if "update" in data else None,
            languages=data.get("languages", ["English"]),
            custom_nsis_includes=data.get("custom_nsis_includes", [])
        )
