"""
Unit tests for xswl-yaml-nsis NSIS converter
"""

import unittest
from xswl_yaml_nsis.config import PackageConfig, AppInfo, InstallConfig, FileEntry
from xswl_yaml_nsis.converter import YamlToNsisConverter


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


if __name__ == '__main__':
    unittest.main()
