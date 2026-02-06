"""
Integration tests for xswl-YPack
"""

import unittest
import tempfile
import os
from ypack.config import PackageConfig
from ypack.converters.convert_nsis import YamlToNsisConverter


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete workflow"""
    
    def test_simple_workflow(self):
        """Test complete workflow from YAML to NSIS"""
        # Create a temporary YAML file
        yaml_content = """
app:
  name: IntegrationTest
  version: "1.0.0"
  publisher: Test
  description: Integration test app

install:
  install_dir: $PROGRAMFILES64\\IntegrationTest
  desktop_shortcut_target: $INSTDIR\\IntegrationTest.exe
  start_menu_shortcut_target: $INSTDIR\\IntegrationTest.exe

files:
  - test.exe
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name
        
        try:
            # Load config
            config = PackageConfig.from_yaml(yaml_path)
            self.assertEqual(config.app.name, "IntegrationTest")
            
            # Convert to NSIS
            converter = YamlToNsisConverter(config)
            nsis_script = converter.convert()
            
            # Verify script content
            self.assertIn("IntegrationTest", nsis_script)
            self.assertIn("Section \"Install\"", nsis_script)
            self.assertIn("Section \"Uninstall\"", nsis_script)
            
            # Save to file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.nsi', delete=False) as nsi_f:
                nsi_path = nsi_f.name
            
            converter.save(nsi_path)
            
            # Verify file was created
            self.assertTrue(os.path.exists(nsi_path))
            
            # Verify file content
            with open(nsi_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self.assertIn("IntegrationTest", content)
            
            os.unlink(nsi_path)
            
        finally:
            os.unlink(yaml_path)
    
    def test_complete_config_workflow(self):
        """Test workflow with all features enabled"""
        yaml_content = """
app:
  name: CompleteTest
  version: "2.0.0"
  publisher: Complete Publisher
  description: Complete test
  install_icon: app.ico
  uninstall_icon: uninstall.ico
  license: LICENSE.txt

install:
  install_dir: $PROGRAMFILES64\\CompleteTest
  desktop_shortcut_target: $INSTDIR\\CompleteTest.exe
  start_menu_shortcut_target: $INSTDIR\\CompleteTest.exe

files:
  - app.exe
  - source: lib/*
    recursive: true

signing:
  enabled: true
  certificate: cert.pfx
  password: pass

update:
  enabled: true
  update_url: https://example.com/updates
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name
        
        try:
            config = PackageConfig.from_yaml(yaml_path)
            converter = YamlToNsisConverter(config)
            nsis_script = converter.convert()
            
            # Verify all features are present
            self.assertIn("CompleteTest", nsis_script)
            self.assertIn("MUI_ICON", nsis_script)  # Changed from "Icon" to "MUI_ICON" (MUI2 standard)
            self.assertIn("MUI_UNICON", nsis_script)
            self.assertIn("app.ico", nsis_script)
            self.assertIn("uninstall.ico", nsis_script)
            self.assertIn("LicenseData", nsis_script)
            self.assertIn("!finalize", nsis_script)  # Signing
            self.assertIn("UPDATE_URL", nsis_script)  # Update config
            
        finally:
            os.unlink(yaml_path)

    def test_install_icon_implies_uninstall_icon_in_nsis(self):
        """If only install_icon is provided, NSIS output should set both MUI_ICON and MUI_UNICON"""
        yaml_content = """
app:
  name: IconFallback
  version: "1.0.0"
  publisher: Test
  description: "Icon fallback test"
  install_icon: single.ico

install:
  install_dir: $PROGRAMFILES64\\IconFallback

files:
  - app.exe
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            yaml_path = f.name
        try:
            config = PackageConfig.from_yaml(yaml_path)
            converter = YamlToNsisConverter(config)
            nsis_script = converter.convert()
            self.assertIn("MUI_ICON", nsis_script)
            self.assertIn("MUI_UNICON", nsis_script)
            self.assertIn("single.ico", nsis_script)
        finally:
            os.unlink(yaml_path)


if __name__ == '__main__':
    unittest.main()
