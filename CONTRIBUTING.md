# Contributing

Thanks for your interest in contributing to xswl-YPack! This file contains basic setup instructions for developers.

## Developer environment (Windows — Python 3.8)

We use Python 3.8 for CI and wide compatibility. To create a repeatable local dev environment, follow these steps:

1. Ensure Python 3.8 is installed. Example path on this machine: `D:\Python\Python38`.

2. From repository root, run the PowerShell helper (recommended):

```powershell
# Create and prepare a venv named .venv38
scripts\setup-venv38.ps1
```

This script will:
- create `.venv38` using Python 3.8
- upgrade pip/setuptools/wheel
- install the project in editable mode with extras `dev` and `validation`
- run the test suite to verify everything is working

3. Manually (alternative):

```powershell
D:\Python\Python38\python.exe -m venv .venv38
.\.venv38\Scripts\Activate
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[dev,validation]"
python -m pytest tests/ -v
```

4. Running the CLI from the repo without installing via pip:

```powershell
# Use the in-repo console script
.\.venv38\Scripts\Activate
python -m ypack.cli convert tmp/sigvna_installer.yaml -o tmp/sigvna_installer.nsi -v
```

If you encounter issues, please open an issue with OS/Python version and the failing command output. Thanks! 🎯