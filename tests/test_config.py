"""
Unit tests for xswl-yaml-nsis configuration parser
"""

import unittest
import tempfile
import os
import yaml
from xswl_yaml_nsis.config import (
    AppInfo, InstallConfig, FileEntry, SigningConfig, 
    UpdateConfig, PackageConfig
)


class TestAppInfo(unittest.TestCase):
    """Test AppInfo class"""
    
    def test_from_dict_basic(self):
        """Test basic AppInfo creation from dict"""
        data = {
            "name": "TestApp",
            "version": "1.0.0",
            "publisher": "Test Publisher"
        }
        app = AppInfo.from_dict(data)
        self.assertEqual(app.name, "TestApp")
        self.assertEqual(app.version, "1.0.0")
        self.assertEqual(app.publisher, "Test Publisher")
    
    def test_from_dict_with_optionals(self):
        """Test AppInfo creation with optional fields"""
        data = {
            "name": "TestApp",
            "version": "1.0.0",
            "icon": "app.ico",
            "license": "LICENSE.txt"
        }
        app = AppInfo.from_dict(data)
        self.assertEqual(app.icon, "app.ico")
        self.assertEqual(app.license, "LICENSE.txt")


class TestFileEntry(unittest.TestCase):
    """Test FileEntry class"""
    
    def test_from_string(self):
        """Test FileEntry creation from string"""
        entry = FileEntry.from_dict("test.exe")
        self.assertEqual(entry.source, "test.exe")
        self.assertEqual(entry.destination, "$INSTDIR")
        self.assertFalse(entry.recursive)
    
    def test_from_dict(self):
        """Test FileEntry creation from dict"""
        data = {
            "source": "files/*",
            "destination": "$INSTDIR\\files",
            "recursive": True
        }
        entry = FileEntry.from_dict(data)
        self.assertEqual(entry.source, "files/*")
        self.assertEqual(entry.destination, "$INSTDIR\\files")
        self.assertTrue(entry.recursive)


class TestPackageConfig(unittest.TestCase):
    """Test PackageConfig class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_yaml = {
            "app": {
                "name": "TestApp",
                "version": "1.0.0",
                "publisher": "Test Publisher"
            },
            "install": {
                "install_dir": "$PROGRAMFILES64\\TestApp",
                "create_desktop_shortcut": True
            },
            "files": [
                "test.exe",
                {"source": "lib/*", "recursive": True}
            ]
        }
    
    def test_from_dict(self):
        """Test PackageConfig creation from dict"""
        config = PackageConfig.from_dict(self.test_yaml)
        self.assertEqual(config.app.name, "TestApp")
        self.assertEqual(config.app.version, "1.0.0")
        self.assertEqual(len(config.files), 2)
        self.assertTrue(config.install.create_desktop_shortcut)
    
    def test_from_yaml(self):
        """Test PackageConfig creation from YAML file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(self.test_yaml, f)
            temp_path = f.name
        
        try:
            config = PackageConfig.from_yaml(temp_path)
            self.assertEqual(config.app.name, "TestApp")
            self.assertEqual(len(config.files), 2)
        finally:
            os.unlink(temp_path)
    
    def test_with_signing(self):
        """Test PackageConfig with signing configuration"""
        data = self.test_yaml.copy()
        data["signing"] = {
            "enabled": True,
            "certificate": "cert.pfx",
            "password": "password"
        }
        config = PackageConfig.from_dict(data)
        self.assertIsNotNone(config.signing)
        self.assertTrue(config.signing.enabled)
        self.assertEqual(config.signing.certificate, "cert.pfx")
    
    def test_with_update(self):
        """Test PackageConfig with update configuration"""
        data = self.test_yaml.copy()
        data["update"] = {
            "enabled": True,
            "update_url": "https://example.com/updates"
        }
        config = PackageConfig.from_dict(data)
        self.assertIsNotNone(config.update)
        self.assertTrue(config.update.enabled)
        self.assertEqual(config.update.update_url, "https://example.com/updates")


if __name__ == '__main__':
    unittest.main()
