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
git clone https://github.com/Wang-Jianwei/xswl-YPack.git
cd xswl-YPack
pip install -e .
```

### 使用 pip 安装 / Install with pip

```bash
pip install xswl-ypack
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
xswl-ypack installer.yaml -o installer.nsi
```

这将生成一个可读的 `installer.nsi` 文件，您可以查看和修改它。

### 3. 构建安装包 / Build installer

```bash
# 仅生成 NSIS 脚本 / Generate NSIS script only
xswl-ypack installer.yaml

# 生成脚本并构建安装包 / Generate and build installer
xswl-ypack installer.yaml --build

# 指定 makensis 路径 / Specify makensis path
xswl-ypack installer.yaml --build --makensis "C:\Program Files\NSIS\makensis.exe"
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

### 环境变量 / Environment variables

你可以通过 `install.env_vars` 在安装/卸载阶段设置或删除环境变量。对 `PATH` 支持追加模式（`append: true`）并包含归一化机制来避免重复和处理大小写差异。

示例：

```yaml
install:
  env_vars:
    - name: MY_VAR
      value: "C:\\Program Files\\MyApp"
      scope: system        # system -> HKLM, user -> HKCU
      remove_on_uninstall: true
      append: false

    - name: PATH
      value: "$INSTDIR\\bin"
      scope: system
      append: true         # 追加到 PATH（会去重并在卸载时移除）
      remove_on_uninstall: true
```

实现说明：

- 当 `append: true` 且 `name` 为 `PATH` 时，生成器会：
  - 读取当前 PATH（注册表）并对 PATH 与要追加的条目进行 **归一化**（转换分隔符、去重、大小写规范化），
  - 仅在未存在时追加，写回注册表并广播 `WM_SETTINGCHANGE` 以使修改生效，
  - 在卸载时会精确移除之前追加的条目（如果 `remove_on_uninstall: true`）。

- 对非 `PATH` 的 `append: true`，转换器会写入值但不会做自动合并（会以注释说明）。

- 注意：修改系统 PATH 需要管理员权限，且在某些情况下需要重启或重新登录以完全生效。

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
  download_url: "https://example.com/downloads/latest.exe"  # 可选：下载安装包的 URL
  backup_on_upgrade: true     # 可选：在升级前备份旧版本
  repair_enabled: true        # 可选：启用修复模式
  check_on_startup: true
  # 可选：写入注册表的 Hive 与 Key
  registry_hive: "HKCU"      # HKLM (系统范围，需要管理员) 或 HKCU (当前用户)
  registry_key: "Software\\MyCompany\\MyApp"  # 可选自定义注册表路径
```

说明：

- `update_url`：应用用于检查更新的 URL（例如 JSON 元数据）。
- `download_url`：可选，实际的安装包下载地址（安装器会把该值写入注册表供应用使用）。
- `backup_on_upgrade`：若为 `true`，安装器会将当前安装备份以便回滚（应用需要在运行时实现具体逻辑）。
- `repair_enabled`：若为 `true`，安装器会在注册表写入相应标志，应用或用户可使用此标志触发修复流程。
- `registry_hive` / `registry_key`：可配置在安装时写入更新元数据的注册表位置。默认写入 `HKLM ${REG_KEY}`，若设置为 `HKCU` 则会写入当前用户范围（无需管理员权限）。

### 自定义 NSIS 脚本 / Custom NSIS Includes (可选 / Optional)

```yaml
custom_nsis_includes:
  - "custom_functions.nsh"
  - "extra_pages.nsh"
```

## 国际化 / Languages

你可以通过 `languages` 字段为生成的安装器启用多个界面语言（NSIS Modern UI 的 MUI 语言标识）。

示例：

```yaml
# 在 installer.yaml 中指定多语言支持
languages:
  - English
  - SimplifiedChinese  # 简体中文
  - TraditionalChinese # 繁體中文
```

说明：

- 默认值：如果未指定 `languages`，转换器会使用 `["English"]`。
- 支持值：使用 NSIS MUI 可识别的语言标识（例如：`English`, `SimplifiedChinese`, `TraditionalChinese`, `French`, `German`, `Spanish`, `Japanese`, `Korean`, `Russian` 等）。
- 注意：请使用 MUI 的精确标识字符串，转换器会为每个配置项生成一条 `!insertmacro MUI_LANGUAGE "<lang>"` 指令。

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
xswl-ypack --help

# 生成 NSIS 脚本 / Generate NSIS script (默认格式 nsis)
xswl-ypack config.yaml

# 指定格式 / Specify format (currently: nsis)
xswl-ypack config.yaml --format nsis

# 指定输出文件 / Specify output file
xswl-ypack config.yaml -o custom.nsi

# 生成并构建 / Generate and build
xswl-ypack config.yaml --build

# 详细输出 / Verbose output
xswl-ypack config.yaml -v --build
```

## Python API 使用 / Python API Usage

```python
from ypack import PackageConfig, YamlToNsisConverter

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
