# Quick Start Guide

## Installation

```bash
pip install xswl-yaml-nsis
```

Or install from source:

```bash
git clone https://github.com/Wang-Jianwei/xswl-yaml-nsis.git
cd xswl-yaml-nsis
pip install -e .
```

## Basic Usage

### 1. Create a YAML configuration file

Create `installer.yaml`:

```yaml
app:
  name: MyApp
  version: "1.0.0"
  publisher: My Company

install:
  install_dir: $PROGRAMFILES64\\MyApp
  create_desktop_shortcut: true
  create_start_menu_shortcut: true

files:
  - MyApp.exe
  - config.json
```

### 2. Generate NSIS script

```bash
xswl-yaml-nsis installer.yaml
```

This generates `installer.nsi` in the same directory.

### 3. Build the installer (requires NSIS)

```bash
xswl-yaml-nsis installer.yaml --build
```

This generates both the `.nsi` file and builds `MyApp-1.0.0-Setup.exe`.

## Example Workflows

### For Python Projects (using PyInstaller)

```yaml
app:
  name: MyPythonApp
  version: "1.0.0"

files:
  - dist/MyPythonApp.exe
  - source: dist/_internal/*
    recursive: true
```

### For C++ Projects

```yaml
app:
  name: MyCppApp
  version: "2.0.0"

files:
  - Release/MyCppApp.exe
  - source: Release/*.dll
    recursive: false
```

### For Go Projects

```yaml
app:
  name: MyGoApp
  version: "1.5.0"

files:
  - build/MyGoApp.exe
  - config.yaml
```

## Advanced Features

### Code Signing

```yaml
signing:
  enabled: true
  certificate: path/to/cert.pfx
  password: your_password
  timestamp_url: http://timestamp.digicert.com
```

### Auto-Update

```yaml
update:
  enabled: true
  update_url: https://example.com/updates/latest.json
  check_on_startup: true
```

### Custom NSIS Includes

```yaml
custom_nsis_includes:
  - custom_functions.nsh
  - extra_pages.nsh
```

## Testing

Run the included tests:

```bash
python -m unittest discover tests
```

## More Information

See the full [README.md](README.md) for detailed documentation.
