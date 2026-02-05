"""
Unit tests for xswl-YPack NSIS converter
"""

import unittest
from ypack.config import PackageConfig, AppInfo, InstallConfig, FileEntry, PackageEntry
from ypack.converters.convert_nsis import YamlToNsisConverter


class TestYamlToNsisConverter(unittest.TestCase):
    """Test NSIS converter functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.simple_config = PackageConfig(
            app=AppInfo(
                name="TestApp",
                version="1.0.0",
                publisher="Test Publisher",
                description="Test description"
            ),
            install=InstallConfig(),
            files=[
                FileEntry(source="test.exe")
            ]
        )
    
    def test_converter_initialization(self):
        """Test converter initialization"""
        converter = YamlToNsisConverter(self.simple_config)
        self.assertEqual(converter.config.app.name, "TestApp")
    
    def test_generate_header(self):
        """Test NSIS header generation"""
        converter = YamlToNsisConverter(self.simple_config)
        header = converter._generate_header()
        self.assertTrue(any("TestApp" in line for line in header))
        self.assertTrue(any("1.0.0" in line for line in header))
    
    def test_convert_generates_valid_script(self):
        """Test that convert() generates a valid NSIS script"""
        converter = YamlToNsisConverter(self.simple_config)
        script = converter.convert()
        
        # Check for essential NSIS elements
        self.assertIn("!define APP_NAME", script)
        self.assertIn("Section \"Install\"", script)
        self.assertIn("Section \"Uninstall\"", script)
        self.assertIn("MUI2.nsh", script)
    
    def test_variable_replacement(self):
        """Test variable replacement in strings"""
        converter = YamlToNsisConverter(self.simple_config)
        result = converter._replace_variables("$PROGRAMFILES64\\${APP_NAME}")
        self.assertEqual(result, "$PROGRAMFILES64\\TestApp")
    
    def test_installer_section_with_files(self):
        """Test installer section generation with files"""
        converter = YamlToNsisConverter(self.simple_config)
        section = converter._generate_installer_section()
        script = "\n".join(section)
        
        self.assertIn('File "test.exe"', script)
        self.assertIn("WriteUninstaller", script)
        self.assertIn("WriteRegStr", script)
    
    def test_shortcuts_generation(self):
        """Test shortcut generation"""
        config = self.simple_config
        config.install.create_desktop_shortcut = True
        config.install.create_start_menu_shortcut = True
        
        converter = YamlToNsisConverter(config)
        section = converter._generate_installer_section()
        script = "\n".join(section)
        
        self.assertIn("CreateShortCut", script)
        self.assertIn("$DESKTOP", script)
        self.assertIn("$SMPROGRAMS", script)
    
    def test_uninstaller_section(self):
        """Test uninstaller section generation"""
        converter = YamlToNsisConverter(self.simple_config)
        section = converter._generate_uninstaller_section()
        script = "\n".join(section)
        
        self.assertIn("Delete", script)
        self.assertIn("DeleteRegKey", script)
        self.assertIn("RMDir", script)
    
    def test_signing_section_disabled(self):
        """Test that signing section is empty when disabled"""
        converter = YamlToNsisConverter(self.simple_config)
        section = converter._generate_signing_section()
        self.assertEqual(len(section), 0)
    
    def test_update_section_disabled(self):
        """Test that update section is empty when disabled"""
        converter = YamlToNsisConverter(self.simple_config)
        section = converter._generate_update_section()
        self.assertEqual(len(section), 0)

    def test_update_section_extended(self):
        """Extended update fields should be emitted into the update section"""
        from ypack.config import UpdateConfig
        config = self.simple_config
        config.update = UpdateConfig(enabled=True, update_url="https://upd", download_url="https://dl", backup_on_upgrade=True, repair_enabled=False)
        section = "\n".join(YamlToNsisConverter(config)._generate_update_section())
        self.assertIn('!define UPDATE_URL "https://upd"', section)
        self.assertIn('!define DOWNLOAD_URL "https://dl"', section)
        self.assertIn('WriteRegStr HKLM "${REG_KEY}" "BackupOnUpgrade" "${BACKUP_ON_UPGRADE}"', section)
        self.assertIn('WriteRegStr HKLM "${REG_KEY}" "RepairEnabled" "${REPAIR_ENABLED}"', section)

    def test_update_registry_scope_and_key(self):
        """Update section should honor registry_hive and registry_key settings"""
        from ypack.config import UpdateConfig
        config = self.simple_config
        config.update = UpdateConfig(enabled=True, update_url="https://upd", download_url="https://dl", registry_hive="HKCU", registry_key="Software\\MyAppUpdate")
        section = "\n".join(YamlToNsisConverter(config)._generate_update_section())
        self.assertIn('WriteRegStr HKCU "Software\\MyAppUpdate" "UpdateURL" "${UPDATE_URL}"', section)
        self.assertIn('WriteRegStr HKCU "Software\\MyAppUpdate" "DownloadURL" "${DOWNLOAD_URL}"', section)
    def test_signing_section_extended(self):
        """Extended signing fields should be emitted into the signing section"""
        from ypack.config import SigningConfig
        config = self.simple_config
        config.signing = SigningConfig(enabled=True, certificate="c", password="p", timestamp_url="t", verify_signature=True, checksum_type="sha256", checksum_value="abc")
        section = "\n".join(YamlToNsisConverter(config)._generate_signing_section())
        self.assertIn('Verify signature after build: True', section)
        self.assertIn('Checksum: sha256 abc', section)
    
    def test_packages_without_components(self):
        """Test that converter works without packages (backward compatible)"""
        converter = YamlToNsisConverter(self.simple_config)
        script = converter.convert()
        # Should NOT have MUI_PAGE_COMPONENTS when packages is empty
        self.assertNotIn("MUI_PAGE_COMPONENTS", script)

    def test_modern_ui_languages(self):
        """Modern UI should include MUI_LANGUAGE entries for each configured language"""
        config = self.simple_config
        config.languages = ["English", "SimplifiedChinese"]
        converter = YamlToNsisConverter(config)
        ui = converter._generate_modern_ui()
        script = "\n".join(ui)
        self.assertIn('!insertmacro MUI_LANGUAGE "English"', script)
        self.assertIn('!insertmacro MUI_LANGUAGE "SimplifiedChinese"', script)

    def test_env_vars_are_written_and_removed(self):
        """Environment variables should be written to registry and removed on uninstall"""
        from ypack.config import EnvVarEntry

        config = self.simple_config
        config.install.env_vars = [
            EnvVarEntry(name="MYVAR", value="C:\\Program Files\\MyApp", scope="system", remove_on_uninstall=True)
        ]
        converter = YamlToNsisConverter(config)
        script = converter.convert()
        # Installer writes the env var into the system environment registry
        self.assertIn('WriteRegStr HKLM "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" "MYVAR" "C:\\Program Files\\MyApp"', script)
        # Uninstaller removes the registry value
        self.assertIn('DeleteRegValue HKLM "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" "MYVAR"', script)

    def test_path_append_and_remove_logic(self):
        """When append=True for PATH, generator emits helper functions and calls to append/remove path entries"""
        from ypack.config import EnvVarEntry

        config = self.simple_config
        config.install.env_vars = [
            EnvVarEntry(name="PATH", value="$INSTDIR\\bin", scope="system", append=True, remove_on_uninstall=True)
        ]
        converter = YamlToNsisConverter(config)
        script = converter.convert()
        # Should include helper functions and calls
        self.assertIn('Function _Contains', script)
        self.assertIn('Call _Contains', script)
        self.assertIn('Function _RemovePathEntry', script)
        self.assertIn('Call _RemovePathEntry', script)
        # Should read and write PATH in installer/uninstaller
        self.assertIn('ReadRegStr $0 HKLM "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" "PATH"', script)
        self.assertIn('WriteRegStr HKLM "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment" "PATH"', script)
        # Should broadcast environment change to make PATH effective
        self.assertIn('SendMessageTimeoutA', script)
        # Normalization helpers should be present and invoked
        self.assertIn('Function _NormalizePathEntry', script)
        self.assertIn('Call _NormalizePathEntry', script)
        self.assertIn('CharUpperBuffA', script)
    
    def test_package_sections_generation(self):
        """Test generation of package sections"""
        config = PackageConfig(
            app=AppInfo(name="ModularApp", version="2.0.0"),
            install=InstallConfig(),
            files=[],
            packages=[
                PackageEntry(
                    name="app",
                    sources=[{"source": "app/**/*", "destination": "$INSTDIR"}],
                    optional=False,
                    default=True,
                    description="Main Application"
                ),
                PackageEntry(
                    name="PXI_driver",
                    sources=[{"source": "pxi/**/*", "destination": "$INSTDIR\\drivers\\PXI"}],
                    optional=True,
                    default=False,
                    description="PXI Driver"
                )
            ]
        )
        
        converter = YamlToNsisConverter(config)
        script = converter.convert()
        
        # Should have components page
        self.assertIn("MUI_PAGE_COMPONENTS", script)
        # Should have package sections with package names (keys)
        self.assertIn('Section "app"', script)
        self.assertIn('Section "PXI_driver"', script)
        # Should have file directives (normalized paths)
        self.assertIn(f'File /r "{converter._normalize_path("app/*")}"', script)
        self.assertIn(f'File /r "{converter._normalize_path("pxi/*")}"', script)
        # Should have destination paths
        self.assertIn('SetOutPath "$INSTDIR"', script)
        self.assertIn('SetOutPath "$INSTDIR\\drivers\\PXI"', script)

    def test_package_source_as_list(self):
        """Test package sources where a source entry's source is a list"""
        config = PackageConfig(
            app=AppInfo(name="MultiSrcApp", version="1.2.3"),
            install=InstallConfig(),
            files=[],
            packages=[
                PackageEntry(
                    name="multi",
                    sources=[
                        {"source": ["a/**/*", "b/**/*"], "destination": "$INSTDIR\\data"}
                    ],
                    optional=False
                )
            ]
        )
        
        converter = YamlToNsisConverter(config)
        script = converter.convert()
        self.assertIn(f'File /r "{converter._normalize_path("a/*")}"', script)
        self.assertIn(f'File /r "{converter._normalize_path("b/*")}"', script)
        self.assertIn('SetOutPath "$INSTDIR\\data"', script)

    def test_package_groups_generation(self):
        """Test generation of SectionGroup for nested packages"""
        config = PackageConfig(
            app=AppInfo(name="GroupedApp", version="1.0.0"),
            install=InstallConfig(),
            files=[],
            packages=[
                PackageEntry(
                    name="Drivers",
                    sources=[],
                    children=[
                        PackageEntry(
                            name="PXI_driver",
                            sources=[{"source": "pxi/*", "destination": "$INSTDIR\\drivers\\PXI"}],
                            optional=True,
                            default=False,
                        )
                    ]
                )
            ]
        )

        converter = YamlToNsisConverter(config)
        script = converter.convert()

        self.assertIn('SectionGroup "Drivers"', script)
        self.assertIn('Section "PXI_driver"', script)

    def test_remote_file_and_file_association_emitted(self):
        """Remote file with download/checksum and file association should emit explanatory lines"""
        from ypack.config import FileEntry, FileAssociation
        config = self.simple_config
        config.files = [FileEntry(source="remote.bin", download_url="https://example.com/remote.bin", checksum_type="sha256", checksum_value="abcd", decompress=True)]
        config.install.file_associations = [FileAssociation(extension=".foo", prog_id="Foo.File", description="Foo File", application="$INSTDIR\\Foo.exe", default_icon="$INSTDIR\\icons\\foo.ico", verbs={"open": "$INSTDIR\\Foo.exe \"%1\""})]
        script = YamlToNsisConverter(config).convert()
        # Installer should include download and checksum commands
        self.assertIn('inetc::get', script)
        self.assertIn('https://example.com/remote.bin', script)
        self.assertIn('Push "$INSTDIR\\remote.bin"', script)
        self.assertIn('Push "sha256"', script)
        self.assertIn('Push "abcd"', script)
        self.assertIn('Call VerifyChecksum', script)
        self.assertIn('Call ExtractArchive', script)
        # File association registration should appear
        self.assertIn('File association: .foo -> $INSTDIR\\Foo.exe', script)
        self.assertIn('WriteRegStr HKCR ".foo" "" "Foo.File"', script)
        self.assertIn('WriteRegStr HKCR "Foo.File\\DefaultIcon" "" "$INSTDIR\\icons\\foo.ico"', script)
        self.assertIn('WriteRegStr HKCR "Foo.File\\Shell\\open\\Command" "" "$INSTDIR\\Foo.exe "%1""', script)
        # Uninstaller should remove keys
        self.assertIn('DeleteRegKey HKCR ".foo"', script)

    def test_install_time_signature_verification_emitted(self):
        """When signing.verify_signature is True, .onInit should contain PowerShell signature verification"""
        from ypack.config import SigningConfig
        config = self.simple_config
        config.signing = SigningConfig(enabled=True, certificate="c", password="p", timestamp_url="t", verify_signature=True)
        script = YamlToNsisConverter(config).convert()
        self.assertIn('Get-AuthenticodeSignature', script)
        self.assertIn('Signature verification failed', script)
        self.assertIn('ExecWait', script)
        # Fallback to signtool should be present
        self.assertIn('IfFileExists "$WINDIR\\system32\\signtool.exe"', script)
        self.assertIn('signtool.exe', script)

    def test_system_requirements_checks_emitted(self):
        """When SystemRequirements are defined, .onInit should contain version/space/memory checks"""
        from ypack.config import SystemRequirements
        config = self.simple_config
        config.install.system_requirements = SystemRequirements(min_windows_version="10.0.0", min_free_space_mb=500, min_ram_mb=2048, require_admin=True)
        script = YamlToNsisConverter(config).convert()
        # Check Windows version check and messages
        self.assertIn('Get-CimInstance Win32_OperatingSystem', script)
        self.assertIn('Requires Windows 10.0.0 or higher', script)
        # Check free space
        self.assertIn('Not enough free disk space on installation drive. Require at least 500 MB', script)
        # Check RAM
        self.assertIn('Not enough physical memory. Require at least 2048 MB', script)
        # Admin requirement note present
        self.assertIn('Ensure running as administrator (UAC check)', script)

    def test_logging_config_emitted(self):
        """When logging.enabled is True, generator should emit LogSet on and path"""
        from ypack.config import LoggingConfig
        config = self.simple_config
        config.logging = LoggingConfig(enabled=True, path="$APPDATA\\${APP_NAME}\\install.log", level="DEBUG")
        script = YamlToNsisConverter(config).convert()
        self.assertIn('LogSet on', script)
        self.assertIn('Logging enabled: path=$APPDATA\\${APP_NAME}\\install.log level=DEBUG', script)
        # Uninstaller logging note
        self.assertIn('Uninstaller logging enabled', script)

    def test_finish_run_checkbox_emitted(self):
        """When install.launch_on_finish is set, generator should emit MUI_FINISHPAGE_RUN defines"""
        from ypack.config import InstallConfig
        config = self.simple_config
        config.install.launch_on_finish = "$INSTDIR\\MyApp.exe"
        config.install.launch_on_finish_label = "Run MyApp"
        script = YamlToNsisConverter(config).convert()
        self.assertIn('!define MUI_FINISHPAGE_RUN "$INSTDIR\\MyApp.exe"', script)
        self.assertIn('!define MUI_FINISHPAGE_RUN_TEXT "Run MyApp"', script)

    def test_package_post_install_commands(self):
        """Test post-install commands are emitted for package sections"""
        config = PackageConfig(
            app=AppInfo(name="PostInstallApp", version="1.0.0"),
            install=InstallConfig(),
            files=[],
            packages=[
                PackageEntry(
                    name="driver",
                    sources=[{"source": "drv/*", "destination": "$INSTDIR\\drivers"}],
                    post_install=["$INSTDIR\\drivers\\install_driver.exe /quiet"],
                    optional=True,
                    default=False,
                )
            ]
        )

        converter = YamlToNsisConverter(config)
        script = converter.convert()

        self.assertIn('ExecWait "$INSTDIR\\drivers\\install_driver.exe /quiet"', script)

    def test_install_registry_entries(self):
        """Test custom registry entries are written and removed"""
        reg_entries = [
            {
                "hive": "HKLM",
                "key": "Software\\TestApp",
                "name": "UpdateURL",
                "value": "https://example.com/updates",
                "type": "string",
                "view": "64"
            },
            {
                "hive": "HKCU",
                "key": "Software\\TestApp",
                "name": "Enabled",
                "value": "1",
                "type": "dword",
                "view": "32"
            }
        ]
        config = PackageConfig(
            app=AppInfo(name="RegApp", version="1.0.0"),
            install=InstallConfig.from_dict({"registry_entries": reg_entries}),
            files=[],
            packages=[]
        )

        converter = YamlToNsisConverter(config)
        script = converter.convert()

        self.assertIn('WriteRegStr HKLM "Software\\TestApp" "UpdateURL" "https://example.com/updates"', script)
        self.assertIn('WriteRegDWORD HKCU "Software\\TestApp" "Enabled" 1', script)
        # Check uninstaller deletes values
        self.assertIn('DeleteRegValue HKLM "Software\\TestApp" "UpdateURL"', script)
        self.assertIn('DeleteRegValue HKCU "Software\\TestApp" "Enabled"', script)
        # If multiple views are used, a boxed warning should be present
        self.assertIn('WARNING: registry entries use multiple SetRegView values', script)
        self.assertIn('Converter will insert SetRegView before each affected entry', script)


if __name__ == '__main__':
    unittest.main()