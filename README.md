# xswl-YPack

一个轻量级的 Windows 工程打包工具，和 Electron-Builder 类似。

A lightweight Windows packaging tool, similar to Electron-Builder.

## 特性 / Features

- 🚀 **语言无关** / Language-agnostic: 支持 C++、Python、Go 等任何语言的项目
- 📝 **YAML 配置** / YAML-based: 通过简单的 YAML 配置文件定义打包内容
- 🔍 **可审计** / Auditable: 生成可读的 NSIS 脚本，便于审查和定制
- ✍️ **易定制** / Easy to customize: 支持代码签名、自动更新、自定义安装流程
- 🎯 **轻量级** / Lightweight: 纯 Python 实现，无复杂依赖

## 工作流程 / Workflow

```js
YAML 配置 → Python 转换器 → NSIS 脚本 → makensis → Windows 安装包
YAML Config → Python Converter → NSIS Script → makensis → Windows Installer
```

## 安装 / Installation

### 从源码安装 / Install from source

```bash
git clone https://github.com/Wang-Jianwei/xswl-yaml-nsis.git
cd xswl-yaml-nsis
pip install -e .
```

### 使用 pip 安装 / Install with pip

```bash
pip install xswl-yaml-nsis
```

## 快速开始 / Quick Start

### 1. 创建 YAML 配置文件 / Create a YAML configuration file

创建一个 `installer.yaml` 文件：

```yaml
app:
  name: "MyApp"
  version: "1.0.0"
  publisher: "My Company"
  description: "My awesome application"

install:
  install_dir: "$PROGRAMFILES64\\${APP_NAME}"
  create_desktop_shortcut: true
  create_start_menu_shortcut: true

files:
  - "MyApp.exe"
  - source: "resources/**/*"  # Use ** to indicate recursion (recommended)
    # recursive: true  # Deprecated: use ** in source pattern instead
```

### 2. 生成 NSIS 脚本 / Generate NSIS script

```bash
xswl-yaml-nsis installer.yaml -o installer.nsi
```

这将生成一个可读的 `installer.nsi` 文件，您可以查看和修改它。

### 3. 构建安装包 / Build installer

```bash
# 仅生成 NSIS 脚本 / Generate NSIS script only
xswl-yaml-nsis installer.yaml

# 生成脚本并构建安装包 / Generate and build installer
xswl-yaml-nsis installer.yaml --build

# 指定 makensis 路径 / Specify makensis path
xswl-yaml-nsis installer.yaml --build --makensis "C:\Program Files\NSIS\makensis.exe"
```

## 配置选项 / Configuration Options

### 应用信息 / Application Information

```yaml
app:
  name: "MyApplication"           # 应用名称 / Application name
  version: "1.0.0"                # 版本号 / Version
  publisher: "My Company"         # 发布者 / Publisher
  description: "App description"  # 描述 / Description
  icon: "app.ico"                 # 图标文件 / Icon file (optional)
  license: "LICENSE.txt"          # 许可协议 / License file (optional)
```

### 安装配置 / Installation Configuration

```yaml
install:
  install_dir: "$PROGRAMFILES64\\${APP_NAME}"  # 安装目录 / Install directory
  create_desktop_shortcut: true                # 桌面快捷方式 / Desktop shortcut
  create_start_menu_shortcut: true             # 开始菜单快捷方式 / Start menu shortcut
  registry_key: "Software\\${APP_NAME}"        # 注册表键 / Registry key
```

#### 注册表项 / Registry entries

你可以在安装时写入自定义注册表值，并在卸载时自动删除它们。支持三种类型：`string`（WriteRegStr）、`expand`（WriteRegExpandStr）和 `dword`（WriteRegDWORD）。

示例：

```yaml
install:
  registry_entries:
    - hive: HKLM
      key: "Software\\MyApp"
      name: "UpdateURL"
      value: "https://example.com/updates"
      type: "string"
      view: "64"
    - hive: HKCU
      key: "Software\\MyApp"
      name: "Enabled"
      value: "1"
      type: "dword"
      view: "32"  # (optional) view: auto|32|64, default auto
```

生成的安装脚本会在安装阶段写入这些值，卸载阶段会调用 `DeleteRegValue` 删除对应的值。

注意：`SetRegView` 会改变后续的注册表视图（32/64 位）。转换器会在每条有指定 `view` 的条目之前插入对应的 `SetRegView`，以确保写入/删除在预期的注册表视图中执行。

如果在同一配置中混用了多个不同的 `view`（例如既有 `32` 又有 `64`），生成器会在注册表段顶部插入显眼注释提醒：

```
; ============================================================
; WARNING: registry entries use multiple SetRegView values: 32,64
; Converter will insert SetRegView before each affected entry.
; Be aware: SetRegView affects subsequent registry operations.
; ============================================================
```

### 文件配置 / Files Configuration

> 说明：从 v0.x 起，**仅当 source 模式包含 `**`（例如 `dir/**/*`）时，转换器会把该条目视为递归（生成 `File /r`）。**
> 
> - `dir/*` 仅匹配当前目录的直接子项（非递归）。
> - `dir/**/*` 会递归匹配所有子目录和文件（生成 `File /r`）。
> - `recursive` 字段仍然兼容但已不推荐使用；建议使用 `**` 明确表达递归意图。



```yaml
files:
  # 简单文件 / Simple file
  - "MyApp.exe"
  
  # 带目标路径的文件 / File with destination
  - source: "config.json"
    destination: "$INSTDIR"
    recursive: false
  
  # 递归目录 / Recursive directory
  - source: "resources/**/*"  # recursive: use ** for recursion (matches all subdirs and files)
    destination: "$INSTDIR\\resources"
    # recursive: true  # deprecated: prefer using ** in source pattern
```

### 代码签名 / Code Signing (可选 / Optional)

```yaml
signing:
  enabled: true
  certificate: "path/to/certificate.pfx"
  password: "your_password"
  timestamp_url: "http://timestamp.digicert.com"
```

### 自动更新 / Auto-update (可选 / Optional)

```yaml
update:
  enabled: true
  update_url: "https://example.com/updates/latest.json"
  check_on_startup: true
```

### 自定义 NSIS 脚本 / Custom NSIS Includes (可选 / Optional)

```yaml
custom_nsis_includes:
  - "custom_functions.nsh"
  - "extra_pages.nsh"
```

## 使用示例 / Usage Examples

### Python 项目 / Python Project

```yaml
app:
  name: "MyPythonApp"
  version: "1.0.0"
  publisher: "Python Developer"

files:
  - "dist/MyPythonApp.exe"  # PyInstaller 生成的可执行文件
  - source: "dist/lib/*"
    recursive: true
```

### C++ 项目 / C++ Project

```yaml
app:
  name: "MyCppApp"
  version: "2.0.0"
  publisher: "C++ Developer"

files:
  - "Release/MyCppApp.exe"
  - "Release/*.dll"
```

### Go 项目 / Go Project

```yaml
app:
  name: "MyGoApp"
  version: "1.5.0"
  publisher: "Go Developer"

files:
  - "MyGoApp.exe"
  - "config.yaml"
```

## CLI 命令 / CLI Commands

```bash
# 查看帮助 / Show help
xswl-yaml-nsis --help

# 生成 NSIS 脚本 / Generate NSIS script (默认格式 nsis)
xswl-yaml-nsis config.yaml

# 指定格式 / Specify format (currently: nsis)
xswl-yaml-nsis config.yaml --format nsis

# 指定输出文件 / Specify output file
xswl-yaml-nsis config.yaml -o custom.nsi

# 生成并构建 / Generate and build
xswl-yaml-nsis config.yaml --build

# 详细输出 / Verbose output
xswl-yaml-nsis config.yaml -v --build
```

## Python API 使用 / Python API Usage

```python
from xswl_yaml_nsis import PackageConfig, YamlToNsisConverter

# 从 YAML 文件加载配置 / Load config from YAML
config = PackageConfig.from_yaml("installer.yaml")

# 创建转换器 / Create converter
converter = YamlToNsisConverter(config)

# 生成 NSIS 脚本 / Generate NSIS script
nsis_script = converter.convert()

# 保存到文件 / Save to file
converter.save("installer.nsi")
```

## 要求 / Requirements

- Python 3.7+
- PyYAML 5.1+
- NSIS (用于构建安装包 / for building installers)

## 许可证 / License

MIT License

## 贡献 / Contributing

欢迎提交 Issue 和 Pull Request！

Welcome to submit Issues and Pull Requests!

## 相关项目 / Related Projects

- [NSIS](https://nsis.sourceforge.io/) - Nullsoft Scriptable Install System
- [Electron-Builder](https://www.electron.build/) - Complete solution to package Electron apps
