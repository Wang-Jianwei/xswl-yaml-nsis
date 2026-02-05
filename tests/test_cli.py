import subprocess
import os
import sys
import unittest

class TestCLIFormat(unittest.TestCase):
    def test_cli_format_nsis_generates(self):
        # Use the provided example YAML in tmp
        out = subprocess.run([
            sys.executable, '-m', 'xswl_yaml_nsis.cli',
            'tmp/sigvna_installer.yaml', '-o', 'tmp/out_nsis.nsi', '--format', 'nsis'
        ], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, msg=f"STDERR: {out.stderr}")
        self.assertIn('Generated NSIS script', out.stdout)
        self.assertTrue(os.path.exists('tmp/out_nsis.nsi'))

    def test_cli_format_wix_unsupported(self):
        out = subprocess.run([
            sys.executable, '-m', 'xswl_yaml_nsis.cli',
            'tmp/sigvna_installer.yaml', '-o', 'tmp/out_wix.nsi', '--format', 'wix'
        ], capture_output=True, text=True)
        # Expect non-zero and message about not supported
        self.assertNotEqual(out.returncode, 0)
        self.assertIn("not supported", out.stderr)

if __name__ == '__main__':
    unittest.main()
