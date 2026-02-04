"""
xswl-yaml-nsis - A lightweight Windows packaging tool
Converts YAML configurations to NSIS scripts for building installers
"""

__version__ = "0.1.0"

from .converter import YamlToNsisConverter
from .config import PackageConfig

__all__ = ["YamlToNsisConverter", "PackageConfig"]
