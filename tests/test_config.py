"""
Unit tests for xswl-YPack configuration parser
"""

import unittest
import tempfile
import os
import yaml
from ypack.config import (
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
            "install_icon": "app.ico",
            "license": "LICENSE.txt"
        }
        app = AppInfo.from_dict(data)
        self.assertEqual(app.install_icon, "app.ico")
        self.assertEqual(app.license, "LICENSE.txt")

    def test_uninstall_icon_defaults_to_install_icon(self):
        """If only install_icon is provided, uninstall_icon should fall back to it"""
        data = {
            "name": "TestApp",
            "version": "1.0.0",
            "install_icon": "app.ico",
        }
        app = AppInfo.from_dict(data)
        self.assertEqual(app.install_icon, "app.ico")
        self.assertEqual(app.uninstall_icon, "app.ico")


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
                "desktop_shortcut_target": "$INSTDIR\\TestApp.exe"
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
        self.assertEqual(config.install.desktop_shortcut_target, "$INSTDIR\\TestApp.exe")
    
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

    def test_update_and_signing_extended_fields(self):
        """Test parsing of extended update and signing fields"""
        data = self.test_yaml.copy()
        data["update"] = {
            "enabled": True,
            "update_url": "https://example.com/updates",
            "download_url": "https://example.com/download",
            "backup_on_upgrade": True,
            "repair_enabled": True,
        }
        data["signing"] = {
            "enabled": True,
            "certificate": "cert.pfx",
            "password": "pwd",
            "timestamp_url": "http://timestamp",
            "verify_signature": True,
            "checksum_type": "sha256",
            "checksum_value": "deadbeef"
        }
        config = PackageConfig.from_dict(data)
        self.assertTrue(config.update.download_url, "https://example.com/download")
        self.assertTrue(config.update.backup_on_upgrade)
        self.assertTrue(config.update.repair_enabled)
        self.assertTrue(config.signing.verify_signature)
        self.assertEqual(config.signing.checksum_type, "sha256")
        self.assertEqual(config.signing.checksum_value, "deadbeef")
    def test_languages_default_and_custom(self):
        """Test default languages and custom language list from dict"""
        config = PackageConfig.from_dict(self.test_yaml)
        self.assertEqual(config.languages, ["English"])
        data = self.test_yaml.copy()
        data["languages"] = ["English", "SimplifiedChinese"]
        config2 = PackageConfig.from_dict(data)
        self.assertEqual(config2.languages, ["English", "SimplifiedChinese"])

    def test_env_vars_parsing(self):
        """Test parsing of environment variables from config"""
        data = self.test_yaml.copy()
        data["install"] = data.get("install", {})
        data["install"]["env_vars"] = [
            {
                "name": "TEST_VAR",
                "value": "test_value",
                "scope": "user",
                "remove_on_uninstall": True,
                "append": False,
            }
        ]
        config = PackageConfig.from_dict(data)
        self.assertEqual(len(config.install.env_vars), 1)
        ev = config.install.env_vars[0]
        self.assertEqual(ev.name, "TEST_VAR")
        self.assertEqual(ev.value, "test_value")
        self.assertEqual(ev.scope, "user")
        self.assertTrue(ev.remove_on_uninstall)
        self.assertFalse(ev.append)

    def test_fileentry_download_and_checksum(self):
        """Test FileEntry parsing of download/checksum/decompress fields"""
        data = self.test_yaml.copy()
        data["files"] = [
            {"source": "remote.bin", "download_url": "https://example.com/remote.bin", "checksum_type": "sha256", "checksum_value": "abcd", "decompress": True}
        ]
        config = PackageConfig.from_dict(data)
        self.assertEqual(len(config.files), 1)
        fe = config.files[0]
        self.assertEqual(fe.source, "remote.bin")
        self.assertEqual(fe.download_url, "https://example.com/remote.bin")
        self.assertEqual(fe.checksum_type, "sha256")
        self.assertEqual(fe.checksum_value, "abcd")
        self.assertTrue(fe.decompress)

    def test_system_requirements_and_file_association(self):
        """Test parsing of system_requirements and file_associations in install config"""
        data = self.test_yaml.copy()
        data["install"] = data.get("install", {})
        data["install"]["system_requirements"] = {"min_windows_version": "10.0", "min_free_space_mb": 1024, "min_ram_mb": 2048, "require_admin": True}
        data["install"]["file_associations"] = [
            {"extension": ".foo", "prog_id": "FooApp.File", "description": "Foo File", "application": "$INSTDIR\\Foo.exe", "default_icon": "$INSTDIR\\icons\\foo.ico", "verbs": {"open": "$INSTDIR\\Foo.exe \"%1\""}, "register_for_all_users": True}
        ]
        data["logging"] = {"enabled": True, "path": "C:\\logs", "level": "DEBUG"}
        config = PackageConfig.from_dict(data)
        # System requirements
        self.assertIsNotNone(config.install.system_requirements)
        self.assertEqual(config.install.system_requirements.min_windows_version, "10.0")
        self.assertEqual(config.install.system_requirements.min_free_space_mb, 1024)
        self.assertTrue(config.install.system_requirements.require_admin)
        # File association
        self.assertEqual(len(config.install.file_associations), 1)
        fa = config.install.file_associations[0]
        self.assertEqual(fa.extension, ".foo")
        self.assertEqual(fa.prog_id, "FooApp.File")
        self.assertEqual(fa.application, "$INSTDIR\\Foo.exe")
        # Logging config
        self.assertIsNotNone(config.logging)
        self.assertTrue(config.logging.enabled)
        self.assertEqual(config.logging.path, "C:\\logs")
        self.assertEqual(config.logging.level, "DEBUG")


if __name__ == '__main__':
    unittest.main()
