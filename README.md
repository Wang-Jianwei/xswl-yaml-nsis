# xswl-YPack

一个轻量级的 Windows 工程打包工具，类似 Electron-Builder。支持 NSIS、WIX、Inno Setup 等多种后端。

A lightweight Windows packaging tool, similar to Electron-Builder. Supports multiple backends: NSIS, WIX, Inno Setup, and more.

## 特性 / Features

- 🚀 **语言无关** / Language-agnostic: 支持 C++、Python、Go 等任何语言的项目
- 📝 **YAML 配置** / YAML-based: 通过简单的 YAML 配置文件定义打包内容
- 🔌 **多后端** / Multi-backend: 支持 NSIS（已实现），WIX / Inno Setup（计划中）
- 🔍 **可审计** / Auditable: 生成可读的安装脚本，便于审查和定制
- ✍️ **易定制** / Easy to customize: 支持代码签名、自动更新、自定义安装流程
- 🎯 **轻量级** / Lightweight: 纯 Python 实现，仅依赖 PyYAML
- ✅ **Schema 校验** / Schema validation: 可选的 jsonschema 校验，配置错误即时发现
- 🔧 **子命令 CLI** / Subcommand CLI: `convert` · `init` · `validate`

## 工作流程 / Workflow

```
YAML 配置 → Python 转换器 → NSIS / WIX / Inno 脚本 → 编译器 → Windows 安装包
YAML Config → Python Converter → NSIS / WIX / Inno Script → Compiler → Windows Installer
```

## 安装 / Installation

### 使用 pip / Install with pip

```bash
pip install xswl-ypack
```

### 从源码安装 / Install from source

```bash
git clone https://github.com/Wang-Jianwei/xswl-YPack.git
cd xswl-YPack
pip install -e ".[dev,validation]"
```

> `validation` 可选依赖会安装 `jsonschema`，启用完整的 YAML 配置校验。
> `dev` 包含 pytest / ruff / mypy / jsonschema 等开发工具。

## 快速开始 / Quick Start

### 1. 生成配置模板 / Generate a starter config

```bash
xswl-ypack init
```

这会在当前目录创建 `installer.yaml` 模板。

### 2. 编辑 YAML 配置 / Edit the YAML

```yaml
app:
  name: "MyApp"
  version: "1.0.0"
  publisher: "My Company"
  description: "My awesome application"

install:
  install_dir: "$PROGRAMFILES64\\${APP_NAME}"
  desktop_shortcut_target: "$INSTDIR\\MyApp.exe"
  start_menu_shortcut_target: "$INSTDIR\\MyApp.exe"

files:
  - "MyApp.exe"
  - source: "resources/**/*"
    destination: "$INSTDIR\\resources"
```

### 3. 生成安装脚本 / Convert

```bash
# 生成 installer.nsi（默认 NSIS 格式）
xswl-ypack convert installer.yaml

# 指定输出格式（nsis / wix / inno）
xswl-ypack convert installer.yaml -f nsis

# 指定输出路径
xswl-ypack convert installer.yaml -o dist/installer.nsi

# 预览到标准输出（不写文件）
xswl-ypack convert installer.yaml --dry-run

> 注意：生成的安装脚本在写入磁盘时会以 **UTF-8 with BOM**（`utf-8-sig`）编码保存，以确保 NSIS 在处理包含 Unicode 字符的脚本时能够正确识别。
```

### 4. 构建安装包 / Build

```bash
xswl-ypack convert installer.yaml --build
```

需要系统安装对应编译器（如 [NSIS](https://nsis.sourceforge.io/) 的 `makensis`，需在 PATH 中或通过 `--makensis` 指定路径）。

### 5. 校验配置 / Validate only

```bash
xswl-ypack validate installer.yaml -v
```

## CLI 命令 / CLI Commands

```bash
xswl-ypack --help              # 查看帮助
xswl-ypack --version           # 版本号

# 子命令
xswl-ypack convert <yaml> [-o output] [-f nsis|wix|inno] [--installer-name NAME] [--dry-run] [--build] [-v]
xswl-ypack init [-o installer.yaml]
xswl-ypack validate <yaml> [-v]

# 向后兼容：直接传文件名等价于 convert
xswl-ypack installer.yaml -o out.nsi
```

`-f / --format` 指定目标后端（默认 `nsis`）。当前已实现 NSIS；WIX 和 Inno Setup 后端即将推出。

## 配置选项 / Configuration Reference

### 应用信息 / Application Information

```yaml
app:
  name: "MyApp"                    # 必须 / required
  version: "1.0.0"                 # 版本号
  publisher: "My Company"          # 发布者
  description: "App description"   # 描述
  install_icon: "app.ico"          # 安装器图标
  uninstall_icon: "uninstall.ico"  # 卸载器图标（默认回退到 install_icon）
  license: "LICENSE.txt"           # 许可协议文件
```

### 安装配置 / Installation Configuration

```yaml
install:
  install_dir: "$PROGRAMFILES64\\${app.name}"
  desktop_shortcut_target: "$INSTDIR\\MyApp.exe"
  start_menu_shortcut_target: "$INSTDIR\\MyApp.exe"
  launch_on_finish: "$INSTDIR\\MyApp.exe"
  launch_on_finish_label: "Launch MyApp"
  launch_in_background: true
  silent_install: false
  installer_name: "${app.name}-${app.version}-Setup.exe"  # 可选：自定义安装包文件名（可被 CLI 的 --installer-name 覆盖）
  # Application registry key — 安装器用此路径存储 InstallPath、Version，
  # 也用于 InstallDirRegKey 和已存在安装检测。支持 ${app.xxx} 变量。
  # 默认值：Software\{publisher}\{app_name}（行业惯例）
  registry_key: "Software\\${app.publisher}\\${app.name}"
  # Existing-install behavior (string shorthand or object):
  existing_install:
    mode: "prompt_uninstall"   # prompt_uninstall | auto_uninstall | overwrite | abort | none
    version_check: false       # Skip if same version is already installed
    allow_multiple: false      # Only detect conflict for the same target directory
    show_version_info: true    # Show installed version in dialogs
    uninstall_wait_ms: 5000    # Wait for old uninstaller to finish (ms); set to -1 to wait indefinitely (use with caution — installer will block until the old uninstaller exits)

  # Suggestion: typical values by workload
  #   - Desktop apps: 15000 (default)
  #   - Services: 60000
  #   - Drivers: 30000 - 120000 (30s–2m)
  # Note: when logging is enabled the installer will write "Waiting for uninstaller..." and "Uninstaller finished." messages to the log.
```

### 文件 / Files

```yaml
files:
  - "MyApp.exe"                      # 简单文件
  - source: "config.json"            # 指定目标
    destination: "$INSTDIR"
  - source: "resources/**/*"         # ** 表示递归
    destination: "$INSTDIR\\resources"
  - source: "https://example.com/plugin.zip"   # 远程下载
    checksum_type: sha256
    checksum_value: "abc123..."
    decompress: true
```

> **模式语义**：`dir/*` = 非递归；`dir/**/*` = 递归（生成 `File /r`）

### 注册表 / Registry Entries

```yaml
install:
  registry_entries:
    - hive: HKLM                   # HKLM | HKCU | HKCR | HKU | HKCC
      key: "Software\\MyApp"
      name: "InstallPath"
      value: "$INSTDIR"
      type: "string"               # string | expand | dword
      view: "64"                   # auto | 32 | 64
```

安装时写入，卸载时自动 `DeleteRegValue`。`SetRegView` 会在每条带 `view` 的条目前自动插入。

### 环境变量 / Environment Variables

```yaml
install:
  env_vars:
    - name: MYAPP_HOME
      value: "$INSTDIR"
      scope: system                 # system | user
      remove_on_uninstall: true
    - name: PATH
      value: "$INSTDIR\\bin"
      scope: system
      append: true                  # PATH 追加（自动去重，卸载时精确移除）
      remove_on_uninstall: true
```

`append: true` 时自动生成 `_StrContains` / `_RemovePathEntry` 辅助函数，并在修改后广播 `WM_SETTINGCHANGE`。

### 文件关联 / File Associations

```yaml
install:
  file_associations:
    - extension: ".myf"
      prog_id: "MyApp.File"
      description: "MyApp Document"
      application: "$INSTDIR\\MyApp.exe"
      default_icon: "$INSTDIR\\icons\\doc.ico"
      verbs:
        open: '$INSTDIR\\MyApp.exe "%1"'
      register_for_all_users: true  # true → HKCR, false → HKCU\Software\Classes
```

### 系统需求检查 / System Requirements

```yaml
install:
  system_requirements:
    min_windows_version: "10.0"
    min_free_space_mb: 500
    min_ram_mb: 2048
    require_admin: true
```

在 `.onInit` 中生成对应的预检逻辑。

### 组件包 / Packages (Components)

```yaml
packages:
  App:
    sources:
      - source: "app/*"
        destination: "$INSTDIR"
    optional: false
  Drivers:
    children:
      PXI:
        sources:
          - source: "pxi/*"
            destination: "$INSTDIR\\pxi"
        optional: true
        default: false
        post_install:
          - "$INSTDIR\\pxi\\setup.cmd"
```

生成 NSIS `SectionGroup` / `Section`。`post_install` 以 `ExecWait` 执行。

### 代码签名 / Code Signing

```yaml
signing:
  enabled: true
  certificate: "cert.pfx"
  password: "secret"
  timestamp_url: "http://timestamp.digicert.com"
  verify_signature: true
```

### 自动更新 / Auto-Update

```yaml
update:
  enabled: true
  update_url: "https://example.com/latest.json"
  download_url: "https://example.com/download"
  backup_on_upgrade: true
  registry_hive: "HKCU"
  registry_key: "Software\\MyCompany\\MyApp"
```

### 安装日志 / Logging

```yaml
logging:
  enabled: true
  path: "$APPDATA\\${APP_NAME}\\install.log"
  level: DEBUG          # DEBUG | INFO | WARNING | ERROR
```

### 多语言 / Languages

```yaml
languages:
  - English
  - SimplifiedChinese
  - Japanese
```

默认值：`["English"]`。使用 NSIS MUI 语言标识符。

### 自定义脚本 / Custom Includes

```yaml
custom_includes:
  nsis:
    - "custom_functions.nsh"
    - "extra_pages.nsh"
```

### 变量 / Variables

有关变量系统（内置变量、配置引用与自定义变量）的完整说明，请参阅 [docs/VARIABLES.md](docs/VARIABLES.md)。

## Python API

```python
from ypack import PackageConfig, YamlToNsisConverter, get_converter_class

# 直接使用 NSIS 转换器
config = PackageConfig.from_yaml("installer.yaml")
converter = YamlToNsisConverter(config, config._raw_dict)
converter.save("installer.nsi")

# 或通过注册表按名称获取转换器（支持 nsis / wix / inno …）
ConverterClass = get_converter_class("nsis")
converter = ConverterClass(config, config._raw_dict)
script = converter.convert()
```

## 开发 / Development

```bash
# 安装开发依赖
pip install -e ".[dev,validation]"

# 运行测试
pytest tests/ -v

# 代码检查
ruff check ypack/
mypy ypack/
```

## 项目结构 / Project Structure

```
ypack/
  __init__.py          # 版本 & 公共 API（导出 get_converter_class）
  cli.py               # CLI 入口 (convert / init / validate / --format)
  config.py            # YAML → dataclass 配置解析
  schema.py            # jsonschema 配置校验
  variables.py         # 内置变量 & 语言定义（NSIS / WIX / Inno 三重映射）
  resolver.py          # 变量引用解析 (${...} / $VAR)
  converters/
    __init__.py        # 转换器注册表 (CONVERTER_REGISTRY)
    base.py            # 抽象基类 BaseConverter（tool_name / output_extension）
    context.py         # BuildContext (target_tool 驱动路径分隔符 & 变量映射)
    convert_nsis.py    # NSIS 脚本组装器
    nsis_header.py     # 头部 / 定义 / MUI
    nsis_sections.py   # 安装 / 卸载 Section
    nsis_packages.py   # 组件 Section / 签名 / 更新 / .onInit
    nsis_helpers.py    # PATH 辅助函数 / 校验函数
```

## 系统要求 / Requirements

- Python ≥ 3.8
- PyYAML ≥ 6.0
- NSIS / WIX / Inno Setup（对应后端的编译器）

## 许可证 / License

MIT License

## 贡献 / Contributing

欢迎提交 Issue 和 Pull Request！

## 相关项目 / Related Projects

- [NSIS](https://nsis.sourceforge.io/) - Nullsoft Scriptable Install System
- [WiX Toolset](https://wixtoolset.org/) - Windows Installer XML Toolset
- [Inno Setup](https://jrsoftware.org/isinfo.php) - Free installer for Windows programs
- [Electron-Builder](https://www.electron.build/) - Complete solution to package Electron apps
