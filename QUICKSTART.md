# Quick Start Guide

## Installation

```bash
pip install xswl-ypack
```

Or install from source with dev tools:

```bash
git clone https://github.com/Wang-Jianwei/xswl-YPack.git
cd xswl-YPack
pip install -e ".[dev,validation]"
```

## Basic Usage

### 1. Generate a starter configuration

```bash
xswl-ypack init
```

This creates `installer.yaml` with sensible defaults.

### 2. Edit the YAML

```yaml
app:
  name: MyApp
  version: "1.0.0"
  publisher: My Company

install:
  install_dir: "$PROGRAMFILES64\\MyApp"
  desktop_shortcut_target: "$INSTDIR\\MyApp.exe"
  start_menu_shortcut_target: "$INSTDIR\\MyApp.exe"
  # existing_install controls behavior when a prior install is found (default: prompt_uninstall)
  # Simple:   existing_install: "prompt_uninstall"
  # Full:     existing_install: { mode: "prompt_uninstall", version_check: true, allow_multiple: false, uninstall_wait_ms: 15000 }
  # Tip: set "uninstall_wait_ms: -1" to wait indefinitely for the previous uninstaller (use with caution)

files:
  - MyApp.exe
  - config.json
```

> **Pattern semantics:**
> - `dir/*` — direct children only (non-recursive).
> - `dir/**/*` — recursive (generates `File /r`).

### 3. Validate the configuration

```bash
xswl-ypack validate installer.yaml -v
```

### 4. Generate the installer script

```bash
# Default: NSIS
xswl-ypack convert installer.yaml

# Specify format explicitly (nsis / wix / inno)
xswl-ypack convert installer.yaml -f nsis

# Build and set custom installer filename
xswl-ypack convert installer.yaml --build --installer-name "MyApp-1.2.3-Setup.exe"
```

This generates `installer.nsi` in the same directory.

> Note: Generated scripts are written as **UTF-8 with BOM** (`utf-8-sig`) to ensure NSIS correctly handles Unicode characters.

### 5. Preview without writing a file

```bash
xswl-ypack convert installer.yaml --dry-run
```

### 6. Build the installer (requires compiler)

```bash
xswl-ypack convert installer.yaml --build
```

This generates the `.nsi` file and runs `makensis` to build `MyApp-1.0.0-Setup.exe`.

> Currently, `--build` is supported for NSIS only. WIX and Inno Setup backends are coming soon.

## Example Workflows

### Python Project (PyInstaller)

```yaml
app:
  name: MyPythonApp
  version: "1.0.0"

files:
  - dist/MyPythonApp.exe
  - source: "dist/_internal/**/*"
    destination: "$INSTDIR\\_internal"
```

### C++ Project

```yaml
app:
  name: MyCppApp
  version: "2.0.0"

files:
  - Release/MyCppApp.exe
  - source: "Release/*.dll"
    destination: "$INSTDIR"
```

### Go Project

```yaml
app:
  name: MyGoApp
  version: "1.5.0"

files:
  - build/MyGoApp.exe
  - config.yaml
```

## Advanced Features

### Registry Entries

```yaml
install:
  registry_entries:
    - hive: HKLM
      key: "Software\\MyApp"
      name: UpdateURL
      value: "https://example.com/updates"
      type: string
      view: "64"
```

### Environment Variables

```yaml
install:
  env_vars:
    - name: PATH
      value: "$INSTDIR\\bin"
      scope: system
      append: true
```

### Code Signing

```yaml
signing:
  enabled: true
  certificate: cert.pfx
  password: your_password
  timestamp_url: http://timestamp.digicert.com
```

### Auto-Update

```yaml
update:
  enabled: true
  update_url: https://example.com/latest.json
  download_url: https://example.com/download
  backup_on_upgrade: true
```

### Custom NSIS Includes

```yaml
custom_includes:
  nsis:
    - custom_functions.nsh
    - extra_pages.nsh
```

## Testing

```bash
pytest tests/ -v
```

## More Information

See the full [README.md](README.md) for detailed configuration reference.
