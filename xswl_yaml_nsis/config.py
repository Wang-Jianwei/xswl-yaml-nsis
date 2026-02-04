"""
Configuration parser for YAML packaging configuration
"""

import yaml
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
class InstallConfig:
    """Installation configuration"""
    install_dir: str = "$PROGRAMFILES64\\${APP_NAME}"
    create_desktop_shortcut: bool = True
    create_start_menu_shortcut: bool = True
    registry_key: str = "Software\\${APP_NAME}"
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InstallConfig":
        return cls(
            install_dir=data.get("install_dir", "$PROGRAMFILES64\\${APP_NAME}"),
            create_desktop_shortcut=data.get("create_desktop_shortcut", True),
            create_start_menu_shortcut=data.get("create_start_menu_shortcut", True),
            registry_key=data.get("registry_key", "Software\\${APP_NAME}")
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
    signing: Optional[SigningConfig] = None
    update: Optional[UpdateConfig] = None
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
            signing=SigningConfig.from_dict(data["signing"]) if "signing" in data else None,
            update=UpdateConfig.from_dict(data["update"]) if "update" in data else None,
            custom_nsis_includes=data.get("custom_nsis_includes", [])
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackageConfig":
        """Load configuration from dictionary"""
        return cls(
            app=AppInfo.from_dict(data.get("app", {})),
            install=InstallConfig.from_dict(data.get("install", {})),
            files=[FileEntry.from_dict(f) for f in data.get("files", [])],
            signing=SigningConfig.from_dict(data["signing"]) if "signing" in data else None,
            update=UpdateConfig.from_dict(data["update"]) if "update" in data else None,
            custom_nsis_includes=data.get("custom_nsis_includes", [])
        )
