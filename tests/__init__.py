"""
Test runner for xswl-yaml-nsis
"""

import unittest
import sys

# Discover and run all tests
if __name__ == '__main__':
    loader = unittest.TestLoader()
    tests = loader.discover('tests', pattern='test_*.py')
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(tests)
    sys.exit(0 if result.wasSuccessful() else 1)
