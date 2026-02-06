# xswl-YPack 开发计划与功能评审

**评审日期**: 2026年2月5日  
**项目**: xswl-YPack (YAML 驱动的 NSIS 安装包生成工具)  
**评审目标**: 核对 YAML 配置（config.py）是否支持安装包的 20 项常用功能  
**评审角度**: **优先聚焦 config.py 的配置支持，其次考虑 converter 的转换实现**

---

## 🎯 执行摘要

| 关键指标 | 数据 |
|---------|------|
| Config.py 完全支持 | **15 项（75%）** - 无需修改 |
| Config.py 部分支持 | **2 项（10%）** - 需扩展字段 |
| Config.py 完全缺失 | **5 项（25%）** - 需新增数据类 |
| **Config 改进工作量** | **~11.5-17 小时** |
| **Converter 实现工作量** | **~15-20 小时** |
| **总体开发工作量** | **~26.5-37 小时**（4-6 周） |

---

## 🎯 评审维度说明

本评审以 **config.py 配置支持** 为核心指标，分为三类：

| 级别 | 定义 | 示例 |
|------|------|------|
| ✅ **完全支持** | config.py 已有完整的数据类和字段定义，NSIS converter 已实现转换 | 快捷方式、注册表、卸载 |
| ⚠️ **部分支持** | config.py 已有字段定义，但 NSIS converter 转换不完整或不完善 | 依赖管理、多语言（框架存在但转换不全） |
| ❌ **未支持** | config.py 完全缺少数据类定义，需要从零添加 | 环境变量、文件关联、日志、下载校验 |

**关键点**: 如果 config.py 已支持某功能的配置定义，则视为该功能在配置层已就绪，converter 的不完整不影响 config 的评分。

---

## 📊 总体功能支持现状（Config.py 维度）

| 支持状态 | 数量 | 比例 |
|---------|------|------|
| ✅ config.py 完全支持 | 13 项 | 65% |
| ⚠️ config.py 部分支持 | 2 项 | 10% |
| ❌ config.py 未支持 | 5 项 | 25% |

---

## 🔍 Config.py 配置现状概览

### 已完全支持的配置数据类（13 项，无需修改）:

| 数据类 | 字段 | 相关功能 | 位置 |
|--------|------|---------|------|
| `AppInfo` | name, version, publisher, description, icon, license | 1, 3, 5, 6, 9, 10, 11, 12, 14, 19 | [L15-L30](../ypack/config.py#L15-L30) |
| `FileEntry` | source, destination, recursive | 1, 14 | [L75-L90](../ypack/config.py#L75-L90) |
| `InstallConfig` | install_dir, create_desktop_shortcut, create_start_menu_shortcut, registry_entries | 3, 5, 6, 9, 10, 11, 12 | [L54-L74](../ypack/config.py#L54-L74) |
| `RegistryEntry` | hive, key, name, value, type, view | 5, 6, 9, 12, 14 | [L37-L52](../ypack/config.py#L37-L52) |
| `PackageEntry` | name, sources, recursive, optional, default, description, children, **post_install** | 1, 3, 6, 14, 16 | [L94-L180](../ypack/config.py#L94-L180) |
| `SigningConfig` | enabled, certificate, password, timestamp_url | 19 | [L193-L206](../ypack/config.py#L193-L206) |
| `custom_includes` | 字典（按工具分组） | 19 | [L361](../ypack/config.py#L361) |

**关键发现**:
- ✅ 项目 **16（安装后自动运行）** 实际已通过 `PackageEntry.post_install` 支持，转换器已生成 `ExecWait` 指令
- ✅ **POST_INSTALL 字段** 是多功能的：可用于配置文件生成、依赖检测、程序启动等

---

### 部分支持的配置（2 项，需扩展字段）:

| 功能 | 现状 | 缺失字段 | 工作量 |
|------|------|---------|--------|
| 8. 升级/修复 | `UpdateConfig` 存在但字段不全 | `download_url`, `backup_on_upgrade`, `repair_enabled` 等 | 1-2h |
| 20. 安全校验 | `SigningConfig` 存在但无校验逻辑 | `verify_signature`, `checksum_type`, `checksum_value` 等 | 0.5-1h |

**总计Config扩展**: ~1.5-3 小时

---

### 完全未支持的配置（5 项，需新增数据类）:

| 功能 | 新数据类 | 所属位置 | 字段概览 | 工作量 |
|------|---------|---------|---------|--------|
| 4. 环境变量 | `EnvVarEntry` | `InstallConfig.env_vars` | name, value, scope, append_to_path | 2-3h |
| 7. 多语言 | (直接在 `PackageConfig`) | `PackageConfig.languages` | languages: List[str] | 0.5-1h |
| 13. 安装前检测 | `SystemRequirements` | `InstallConfig.system_requirements` | min_disk_space, min_os_version, required_frameworks | 1.5-2h |
| 15. 日志记录 | `LoggingConfig` | `PackageConfig.logging` | enabled, path, level | 0.5-1h |
| 17. 文件关联 | `FileAssociation` | `InstallConfig.file_associations` | extension, description, program_id, icon, command | 2-3h |
| 18. 网络下载 | (扩展 `FileEntry` / `PackageEntry`) | `FileEntry.download_url`, `checksum_*` | source (支持 URL), checksum_type, checksum_value, decompress | 2-3h |

**总计新增**: ~10-14 小时

**CONFIG.PY 总工作量: ~11.5-17 小时**

---

## 🟢 第一类：完全支持（13 项，即插即用）

### 1. ✅ 安装主程序文件

**Config.py 状态**: ✅ `FileEntry` 完整支持  
**相关代码**:

- [ypack/config.py](../ypack/config.py#L80-L110) - `FileEntry` 和 `PackageEntry` 数据类
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L286-L310) - `_generate_installer_section()` 生成 `File` 指令

**使用示例**:

```yaml
files:
  - "MyApplication.exe"
  - source: "resources/*"
    destination: "$INSTDIR\\resources"
    recursive: true

packages:
  MainApp:
    sources:
      - source: "app.exe"
        destination: "$INSTDIR"
```

**状态**: ✅ 生产就绪

---

### 3. ✅ 创建快捷方式（桌面 / 开始菜单）

**实现方式**: presence of `install.desktop_shortcut_target` and `install.start_menu_shortcut_target` will indicate creation of shortcuts (no boolean flags)  
**相关代码**:

- [ypack/config.py](../ypack/config.py#L54-L74) - `InstallConfig` 数据类
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L330-L345) - 快捷方式创建逻辑
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L379-L400) - 卸载时删除快捷方式

**使用示例**:

```yaml
install:
  create_desktop_shortcut: true
  create_start_menu_shortcut: true
```

**生成代码（NSIS）**:

```nsis
CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_NAME}.exe"
CreateDirectory "$SMPROGRAMS\${APP_NAME}"
CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_NAME}.exe"
```

**状态**: ✅ 生产就绪

---

### 5. ✅ 写入注册表（含 32/64 位视图）

**实现方式**: `install.registry_entries` 配置  
**相关代码**:

- [ypack/config.py](../ypack/config.py#L37-L52) - `RegistryEntry` 数据类（支持 string/expand/dword，视图 32/64 位）
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L347-L365) - 注册表写入与 `SetRegView` 处理
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L401-L413) - 卸载时删除注册表

**使用示例**:

```yaml
install:
  registry_entries:
    - hive: "HKLM"
      key: "Software\\MyApp"
      name: "InstallPath"
      value: "{install.install_dir}"
      type: "string"
      view: "64"
```

**特点**:

- 支持多种类型 (`string`, `expand`, `dword`)
- 自动处理 32/64 位注册表视图切换
- 卸载时自动清理

**状态**: ✅ 生产就绪（已验证多视图处理）

---

### 6. ✅ 卸载功能（完整流程）

**实现方式**: 自动生成 `Uninstall` 段  
**相关代码**:

- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L367-L413) - `_generate_uninstaller_section()`

**包含操作**:

- 删除所有已安装文件
- 删除快捷方式（桌面与开始菜单）
- 删除注册表项（包括 32/64 位视图处理）
- 删除卸载程序本身
- 删除安装目录

**状态**: ✅ 生产就绪

---

### 9. ✅ 权限检测与提升

**实现方式**: `RequestExecutionLevel admin` 指令（自动添加）  
**相关代码**:

- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L185-L187) - `_generate_general_settings()`

**生成代码（NSIS）**:

```nsis
RequestExecutionLevel admin
```

**效果**: Windows 会自动提示用户进行 UAC（用户账户控制）确认，确保具有管理员权限

**状态**: ✅ 生产就绪

---

### 10. ✅ 安装路径选择

**实现方式**: `install.install_dir` 配置 + NSIS 目录选择页面  
**相关代码**:

- [ypack/config.py](../ypack/config.py#L56) - `install_dir` 字段
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L184-L187) - `InstallDir` 生成
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L210) - `MUI_PAGE_DIRECTORY` 页面

**使用示例**:

```yaml
install:
  install_dir: "$PROGRAMFILES64\\${APP_NAME}"
  # 或者自定义
  # install_dir: "$LOCALAPPDATA\\${APP_NAME}"
```

**特点**:

- 支持 NSIS 变量占位符 (`$PROGRAMFILES64`、`$PROGRAMFILES`、`$LOCALAPPDATA` 等)
- 支持自定义 YAML 占位符 (`{app.name}`、`{install.install_dir}` 等)
- 用户可在安装向导中修改安装路径

**状态**: ✅ 生产就绪

---

### 11. ✅ 安装进度显示

**实现方式**: MUI 现代化安装界面  
**相关代码**:

- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L200-L217) - `_generate_modern_ui()`

**生成页面**:

- License 页面（如已配置）
- Components 页面（如已配置包）
- Directory 页面（选择安装路径）
- **Instfiles 页面**（安装进度条 ← 这是关键）
- Finish 页面

**特点**: NSIS MUI2 框架自动提供专业的进度条界面

**状态**: ✅ 生产就绪

---

### 12. ✅ 许可协议展示

**实现方式**: `app.license` 配置  
**相关代码**:

- [ypack/config.py](../ypack/config.py#L23) - `license` 字段
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L189-L199) - 许可文件加载与定义
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L204-L205) - `MUI_PAGE_LICENSE` 生成

**使用示例**:

```yaml
app:
  name: "MyApp"
  license: "LICENSE.txt"  # 相对于 YAML 目录
```

**特点**:

- 自动查找许可文件（相对路径解析）
- 用户必须勾选同意许可协议才能继续安装
- 不存在时会发出警告注释

**状态**: ✅ 生产就绪

---

### 14. ✅ 配置文件生成与修改

**实现方式**: `files` 列表 + `packages[].post_install` 脚本  
**相关代码**:

- [ypack/config.py](../ypack/config.py#L127-L130) - `post_install` 列表字段
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L478-L485) - `ExecWait` 执行命令

**使用方案**:

- **直接复制**: 在 `files` 中放入预先准备的配置文件模板
- **动态生成**: 通过 `post_install` 执行脚本（PowerShell/VBScript 等）生成或修改配置

**使用示例**:

```yaml
files:
  - source: "config_template.ini"
    destination: "$INSTDIR\\config.ini"

packages:
  ConfigSetup:
    sources:
      - source: "setup_script.ps1"
        destination: "$INSTDIR"
    post_install:
      - 'PowerShell -ExecutionPolicy Bypass -File "$INSTDIR\\setup_script.ps1"'
```

**生成代码（NSIS）**:

```nsis
ExecWait "PowerShell -ExecutionPolicy Bypass -File \"$INSTDIR\setup_script.ps1\""
```

**状态**: ✅ 生产就绪（已支持脚本执行）

---

### 19. ✅ 自定义界面（品牌化支持）

**实现方式**: `app.icon` + `custom_includes`  
**相关代码**:

- [ypack/config.py](../ypack/config.py#L22) - `icon` 字段
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L113-L128) - 图标定义
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L800-L838) - 自定义 include 处理
- [ypack/config.py](../ypack/config.py#L361) - `custom_includes`

**使用示例**:

```yaml
app:
  install_icon: "assets/myapp.ico"  # 安装器/快捷方式的图标
  uninstall_icon: "assets/myapp_uninstall.ico"  # 卸载程序的图标

custom_includes:
  nsis:
    - "custom_pages.nsh"
    - "custom_functions.nsh"
```

**特点**:

- 图标用于安装向导和卸载程序
- `custom_includes` 允许为不同目标工具注入不同的 include 列表（例如 `nsis` / `wix`）

**状态**: ✅ 生产就绪（含自定义扩展点）

---

## 🟡 第二类：部分支持（5 项，需扩展）

### 2. ⚠️ 安装依赖组件（Runtime 自动安装）

**当前状态**: 可手动配置，但无自动化 runtime 检测与下载  
**相关代码**:

- [ypack/config.py](../ypack/config.py#L100-L130) - `PackageEntry` 与 `post_install` 字段

**现有能力**:

- 可在 `packages` 中定义依赖包（如 `.NET Framework`、`VC++ Redistributable` 等）
- 可通过 `post_install` 执行安装命令

**缺失能力**:

- ❌ 不会自动检测系统是否已安装依赖
- ❌ 不会自动下载依赖包
- ❌ 没有"仅当不存在时才安装"的条件逻辑
- ❌ 没有内置的 .NET/VC++ 检测脚本

**建议改进**:

1. 添加 `install.dependencies` 配置节
2. 在 converter 中生成 NSIS 依赖检测脚本（如检查注册表中的版本）
3. 支持条件性 `ExecWait`（如 `RunUnless` 或 `RunIf`）

**优先级**: 🟡 中等（很多项目都需要）  
**预期工作量**: 2-3 小时

**示例设计**（未实现）:

```yaml
install:
  dependencies:
    - name: ".NET Framework 4.8"
      check_registry_key: "HKLM\\Software\\Microsoft\\NET Framework Setup\\NDP\\v4.8"
      check_value: "Release"
      min_value: 533320
      installer_url: "https://..."  # 或本地路径
      installer_args: "/q /norestart"
      optional: false
```

**状态**: ⚠️ 可用但需增强

---

### 7. ✅ 多语言支持（已实现）

**当前状态**: 已在 `PackageConfig.languages` 中支持语言列表，并由转换器为每个语言生成 `!insertmacro MUI_LANGUAGE`。  
**相关代码**:

- [ypack/config.py](../ypack/config.py#L227-L235) - `PackageConfig.languages`
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L310-L320) - 生成 `!insertmacro MUI_LANGUAGE` 指令

**现有能力**:

- ✅ 支持在 YAML 中列出语言（例如 `English`, `SimplifiedChinese` 等）
- ✅ Converter 为每个配置的语言输出 `!insertmacro MUI_LANGUAGE` 指令

**待改进**:

- 提供语言特定的界面字符串资源（卸载确认、错误提示等）以实现更完整的本地化体验。

**优先级**: 🟡 中等（国际化项目需要）  
**预期工作量**: 2-4 小时（添加资源和字符串集成）

**示例（已支持）**:

```yaml
languages:
  - English
  - SimplifiedChinese
```

**生成代码示例**:

```nsis
!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimplifiedChinese"
```

**状态**: ⚠️ 需要添加配置支持

---

### 8. ⚠️ 升级与修复功能（仅写入注册表，无检测/执行逻辑）

**当前状态**: 可配置 update URL 和启动时检查标志，但无内置检测/下载/升级流程  
**相关代码**:

- [ypack/config.py](../ypack/config.py#L209-L220) - `UpdateConfig` 数据类
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L502-L515) - 写入更新配置到注册表

**现有能力**:

- ✅ 可配置更新 URL 和启动检查标志
- ✅ 会在注册表中写入 `UpdateURL` 和 `CheckOnStartup` 键

**缺失能力**:

- ❌ 不会在安装程序中执行更新检查
- ❌ 不会处理升级安装（如 `$0.1.0` → `$1.0.0` 的文件替换和迁移）
- ❌ 不会处理"修复"功能（重新安装或恢复损坏的文件）
- ❌ 没有版本检测与比较逻辑

**建议改进**:

1. 向 `PackageEntry` 添加 `repair_mode` / `upgrade_mode` 标志
2. 在卸载前备份重要文件（如用户数据）
3. 提供升级时的数据迁移脚本支持
4. 在应用启动时由应用程序定期检查 `UpdateURL` 并下载/安装

**优先级**: 🟠 较高（成熟项目需要）  
**预期工作量**: 4-5 小时

**状态**: ⚠️ 框架已有，需增加检测与迁移逻辑

---

### 13. ⚠️ 安装前检测（磁盘空间、系统要求、冲突检测）

**当前状态**: 无内置检测，仅通过 `RequestExecutionLevel admin` 检查权限  
**相关代码**:

- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L186) - 权限要求

**现有能力**:

- ✅ 检查管理员权限
- ✅ 支持自定义 NSIS include（可手写检测函数）

**缺失能力**:

- ❌ 不会检查最小/可用磁盘空间
- ❌ 不会检查 Windows 版本（如需要 Win10+）
- ❌ 不会检查冲突软件（如旧版本、竞争产品）
- ❌ 不会检查所需系统库（DirectX、.NET 等）

**建议改进**:

1. 添加 `install.system_requirements` 配置
2. 在 converter 中生成 `.onInit` 函数，检测系统要求
3. 失败时弹出错误对话框，阻止安装

**优先级**: 🟡 中等（正式发布需要）  
**预期工作量**: 3 小时

**示例设计**（未实现）:

```yaml
install:
  system_requirements:
    min_windows_version: "10"  # Windows 10 或更高
    min_disk_space_mb: 500
    required_frameworks:
      - ".NET Framework 4.8"
      - "Visual C++ 2019 Runtime"
```

**状态**: ⚠️ 需要配置 schema 和检测脚本支持

---

### 16. ⚠️ 安装后自动运行（无专用字段，需用 post_install）

**当前状态**: 无专用配置，可用 `post_install` 变通  
**相关代码**:

- [ypack/config.py](../ypack/config.py#L127-L130) - `post_install` 字段
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L478-L485) - `ExecWait` 生成

**现有能力**:

- ✅ 可通过 `post_install` 执行任意命令（如启动应用）
- ✅ 可用 `ExecWait`（等待程序完成）或 `Exec`（后台运行）

**缺失能力**:

- ❌ 没有专用的 `run_after_install` 字段（API 不清晰）
- ❌ 不会在 Finish 页面勾选"立即运行应用"的选项
- ❌ 没有异步运行支持（`Exec` 指令需要手写）

**建议改进**:

1. 添加 `install.run_after_install` 字段（可指定可执行文件路径）
2. 添加 `install.run_in_background` 布尔值（控制 `ExecWait` vs `Exec`）
3. 在 Finish 页面添加"完成后立即启动"的复选框（MUI callback）

**优先级**: 🟡 中等  
**预期工作量**: 1.5 小时

**示例设计**（未实现）:

```yaml
install:
  run_after_install: "$INSTDIR\\MyApp.exe"
  run_in_background: false  # 阻塞直到应用退出
```

**状态**: ⚠️ 可用但 API 需优化

---

## 🔴 第三类：完全未支持（4 项，需新增）

### 4. ❌ 注册环境变量

**当前状态**: 完全不支持  
**缺失代码**: 没有 `install.env_vars` 配置，没有环境变量 NSIS 指令生成

**为什么需要**:

- 多数开发者工具需要 `PATH` 环境变量（如 Go、Python、Node.js 的二进制目录）
- 应用程序可能需要自定义环境变量（如 `APP_HOME`、`LOG_DIR`）

**实现思路**:

1. 在 `InstallConfig` 中添加 `env_vars: List[EnvVar]`
2. 定义 `EnvVar` 数据类：`name`, `value`, `append_to_path` (bool), `scope` ('user'/'machine')
3. 在 converter 中生成 NSIS `WriteRegExpandStr` 到 `HKCU\\Environment` 或 `HKLM\\System\\CurrentControlSet\\Control\\Session Manager\\Environment`
4. 添加刷新环境变量的逻辑（`SendMessage` 或 `SetEnvironmentVariable` 调用）
5. 卸载时相应删除

**优先级**: 🔴 高（很多项目需要）  
**预期工作量**: 3-4 小时

**示例设计**:

```yaml
install:
  env_vars:
    - name: "MYAPP_HOME"
      value: "{install.install_dir}"
      scope: "machine"  # 或 "user"
    - name: "PATH"
      value: "{install.install_dir}\\bin"
      append_to_path: true  # 追加而非替换
      scope: "machine"
```

**生成代码示例**:

```nsis
; 写入环境变量
WriteRegExpandStr HKLM "System\\CurrentControlSet\\Control\\Session Manager\\Environment" "MYAPP_HOME" "$INSTDIR"

; 追加到 PATH
ReadRegStr $0 HKLM "System\\CurrentControlSet\\Control\\Session Manager\\Environment" "PATH"
WriteRegExpandStr HKLM "System\\CurrentControlSet\\Control\\Session Manager\\Environment" "PATH" "$0;$INSTDIR\\bin"

; 通知所有窗口刷新环境变量
SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=5000
```

**状态**: ❌ 需要从零实现

---

### 15. ✅ 日志记录（安装过程日志输出）

**当前状态**: 已实现（基础支持）  
**已实现内容**:

- `PackageConfig.logging` 已解析（`enabled/path/level`），转换器会在安装器头部输出 `LogSet on` 并生成日志路径/级别注释。
- 卸载段也包含日志启用注释，方便收集卸载日志。
- 新增单元测试验证脚本输出包含 `LogSet on` 与路径注释。

**下一步（建议）**:

1. 在真实 Windows 环境上验证日志文件的写入位置和权限，确认 $APPDATA 等变量解析正确。
2. 可选：添加日志轮换或包含卸载日志的选项（`include_uninstall`）。

**优先级**: 🟡 中等（调试和支持时有用）  
**预期工作量**: 0.5-1.5 小时（集成验证与额外选项）

**示例设计（已支持）**:

```yaml
logging:
  enabled: true
  path: "$APPDATA\\${APP_NAME}\\install.log"
  level: "DEBUG"
```

**生成示例**:

```nsis
; Logging enabled: path=$APPDATA\${APP_NAME}\install.log level=DEBUG
LogSet on
```

---

### 17. ❌ 文件关联（将文件类型与程序关联）

**当前状态**: 完全不支持  
**缺失代码**: 没有 `file_associations` 配置，没有注册表 ProgID 生成

**为什么需要**:

- 让用户双击 `.myformat` 文件直接打开（如 `.doc` 打开 Word）
- 右键菜单中显示"打开方式"
- 关联多个文件扩展名

**实现思路**:

1. 在 `InstallConfig` 中添加 `file_associations: List[FileAssociation]`
2. 定义 `FileAssociation` 数据类：`extension`, `description`, `program_id`, `icon`, `open_action` 等
3. 在 converter 中生成注册表写入操作：
   - `HKCR\.ext` → `(Default)` = `MyAppFile`
   - `HKCR\MyAppFile\shell\open\command` → `(Default)` = `"$INSTDIR\MyApp.exe" "%1"`
   - `HKCR\MyAppFile\DefaultIcon` → `(Default)` = `"$INSTDIR\app.ico"`
4. 卸载时删除相关注册表键

**优先级**: 🟡 中等（面向用户的应用需要）  
**预期工作量**: 2-3 小时

**示例设计**:

```yaml
install:
  file_associations:
    - extension: ".myformat"
      description: "My Custom File"
      program_id: "MyApp.Document"
      default_icon: "$INSTDIR\\icons\\document.ico"
      open_action: "open"
      open_command: "\"$INSTDIR\\MyApp.exe\" \"%1\""
      
    - extension: ".myproject"
      description: "My Project File"
      program_id: "MyApp.Project"
      default_icon: "$INSTDIR\\icons\\project.ico"
```

**生成代码**:

```nsis
; 文件扩展关联
WriteRegStr HKCR ".myformat" "" "MyApp.Document"

; ProgID 定义
WriteRegStr HKCR "MyApp.Document" "" "My Custom File"
WriteRegStr HKCR "MyApp.Document\DefaultIcon" "" "$INSTDIR\icons\document.ico"
WriteRegStr HKCR "MyApp.Document\shell\open\command" "" "\"$INSTDIR\MyApp.exe\" \"%1\""
```

**状态**: ❌ 需要从零实现

---

### 18. ❌ 网络下载与完整性校验

**当前状态**: 完全不支持（除了配置 update URL）  
**缺失代码**: 没有下载配置，没有校验和逻辑，没有 `InetLoad`/`NSISdl` 插件调用

**为什么需要**:

- 安装过程中自动下载大型组件（而非在构建时打包）
- 验证下载文件未被篡改（checksum/签名）
- 节省安装包体积

**实现思路**:

1. 在 `PackageEntry` 或 `files` 中支持远程 URL 源
2. 在 converter 中生成 `InetLoad` 调用下载文件
3. 下载后验证校验和（MD5/SHA256）
4. 校验失败时提示用户并中止安装

**优先级**: 🟠 较高（大型项目和组件化安装需要）  
**预期工作量**: 4-5 小时

**示例设计**:

```yaml
files:
  - source: "https://example.com/lib/mylib.zip"
    destination: "$INSTDIR\\lib"
    checksum_type: "sha256"  # 或 "md5"
    checksum_value: "abcdef1234..."
    decompress: true  # 解压 zip

packages:
  DownloadableComponent:
    sources:
      - source: "https://example.com/components/v1.0.0/component.exe"
        destination: "$INSTDIR\\components"
        checksum_type: "sha256"
        checksum_value: "..."
```

**生成代码**:

```nsis
; 下载文件
inetc::get "https://example.com/lib/mylib.zip" "$INSTDIR\lib\mylib.zip" /END

; 验证校验和（伪代码，实际需要 hash 计算插件）
; ${VerifySHA256} "$INSTDIR\lib\mylib.zip" "abcdef1234..."
```

**状态**: ❌ 需要从零实现

---

### 20. ❌ 安全校验（包签名、防篡改）

**当前状态**: 代码签名配置存在但不完整  
**缺失代码**: 没有校验包完整性、没有验证签名的逻辑

**相关代码**（部分实现）:

- [ypack/config.py](../ypack/config.py#L193-L206) - `SigningConfig` 数据类
- [ypack/converters/convert_nsis.py](../ypack/converters/convert_nsis.py#L490-L500) - 签名指令生成（`signtool`）

**现有能力**:

- ✅ 可配置证书和时间戳 URL
- ✅ 会生成 `!finalize` 签名指令

**缺失能力**:

- ❌ 无安装前验证包签名的逻辑
- ❌ 无法检测包是否被篡改
- ❌ 无 Authenticode 验证
- ❌ 没有用户提示（"来自已验证发行商"）

**建议改进**:

1. 在 `signing` 配置中添加 `verify_signature` 字段
2. 在 NSIS 脚本的 `.onInit` 中调用签名验证逻辑
3. 如验证失败，显示警告并询问用户是否继续

**优先级**: 🔴 高（商业发布和安全敏感项目需要）  
**预期工作量**: 3-4 小时

**状态**: ⚠️ 配置已有框架，需补充验证逻辑

---

## 📋 完整需求矩阵（按 Config.py 支持状态）

| # | 功能 | Config 支持 | Converter 实现 | 优先级 | 工作量 | 状态 |
|---|------|------------|--------------|--------|--------|------|
| 1 | 安装主程序文件 | ✅ | ✅ | - | 已完成 | ✅ |
| 2 | 安装依赖组件 | ⚠️ | ⚠️ | 🟡 中等 | 2-3h | 需完善 |
| 3 | 创建快捷方式 | ✅ | ✅ | - | 已完成 | ✅ |
| 4 | 注册环境变量 | ❌ | ❌ | 🔴 高 | 3-4h | 待开发 |
| 5 | 写入注册表 | ✅ | ✅ | - | 已完成 | ✅ |
| 6 | 卸载功能 | ✅ | ✅ | - | 已完成 | ✅ |
| 7 | 多语言支持 | ❌ | ❌ | 🟡 中等 | 2h | 待开发 |
| 8 | 升级/修复功能 | ⚠️ | ⚠️ | 🟠 较高 | 4-5h | 需完善 |
| 9 | 权限检测与提升 | ✅ | ✅ | - | 已完成 | ✅ |
| 10 | 安装路径选择 | ✅ | ✅ | - | 已完成 | ✅ |
| 11 | 安装进度显示 | ✅ | ✅ | - | 已完成 | ✅ |
| 12 | 许可协议展示 | ✅ | ✅ | - | 已完成 | ✅ |
| 13 | 安装前检测 | ✅ | ✅ | 🟡 中等 | 0.5-1.5h | 已实现（PowerShell checks） |
| 14 | 配置文件生成 | ✅ | ✅ | - | 已完成 | ✅ |
| 15 | 日志记录 | ❌ | ❌ | 🟡 中等 | 2-3h | 待开发 |
| 16 | 安装后自动运行 | ✅ | ✅ | - | 已完成 | ✅ |
| 17 | 文件关联 | ❌ | ❌ | 🟡 中等 | 2-3h | 待开发 |
| 18 | 网络下载/校验 | ⚠️ 部分实现 | ⚠️ 部分实现 | 🟠 较高 | 2-4h | 部分实现（生成下载调用 + 占位校验/解压 + 单元测试）；需集成真实校验与解压 |
| 19 | 自定义界面 | ✅ | ✅ | - | 已完成 | ✅ |
| 20 | 安全校验 | ⚠️ | ⚠️ | 🔴 高 | 3-4h | 需完善 |

**Config.py 开发工作量统计**:
- ✅ 完全支持（13 项）：0 小时（已完成）
- ⚠️ 部分支持（2 项）：**~2-3 小时**（扩展字段）
- ❌ 未支持（5 项）：**~12-16 小时**（新增配置类）
- **总计**: **~14-19 小时**（Config 层开发）

**Converter 开发工作量统计**:
- 完全实现：13 项
- 需完善/优化：4 项
- 未实现：3 项
- **总计**: **~15-20 小时**（Converter 层开发）

---

## 🔍 Config.py 配置现状详查

---

## 🚀 分阶段开发计划

### Phase 1：快速赢（推荐优先，1-2 周）

**目标**: 覆盖最常用的缺失功能，提升易用性

| 功能 | 优先级 | 工作量 | 说明 |
|------|--------|--------|------|
| 4. 注册环境变量 | 🔴 高 | 3-4h | 很多项目急需，实现难度中等 |
| 16. 安装后自动运行 | 🟡 中等 | 1.5h | API 优化，快速收益 |
| 15. 日志记录 | 🟡 中等 | 2-3h | 调试支持，简单实现 |

**小计**: ~6-8 小时，三个功能完成

---

### Phase 2：增强稳定性（2-3 周）

**目标**: 安装前检测、多语言、依赖管理

| 功能 | 优先级 | 工作量 | 说明 |
|------|--------|--------|------|
| 2. 安装依赖组件 | 🟡 中等 | 2-3h | 支持条件安装 |
| 7. 多语言支持 | 🟡 中等 | 2h | 扩展国际化 |
| 13. 安装前检测 | 🟡 中等 | 3h | 系统要求检查 |

**小计**: ~7-8 小时，三个功能完成

---

### Phase 3：企业级功能（3-4 周）

**目标**: 下载、签名校验、文件关联、升级

| 功能 | 优先级 | 工作量 | 说明 |
|------|--------|--------|------|
| 20. 安全校验补完 | 🔴 高 | 3-4h | Authenticode 验证 |
| 18. 网络下载/校验 | 🟠 较高 | 4-5h | 远程组件支持 |
| 17. 文件关联 | 🟡 中等 | 2-3h | ProgID 注册 |
| 8. 升级/修复功能 | 🟠 较高 | 4-5h | 版本迁移与恢复 |

**小计**: ~13-17 小时，四个功能完成

---

### 🔧 Converter - 尚未实现 / 部分实现的关键项（优先级与验收）

下面列出的项在配置层已支持或已添加字段，但转换器需要实现相应的 NSIS 行为或增强：

| 功能 | 优先级 | 预估工时 | 验收条件 |
|------|--------|----------|---------|
| 网络下载与校验（download_url / checksum / decompress） | 🔴 高 | 2-4h | **部分实现**：已生成 `inetc::get` 下载调用与占位 `VerifyChecksum`/`ExtractArchive` 并有单元测试。下一步：集成哈希校验插件（或外部工具）并实现解压（`nsisunz`/7z），添加集成测试并验证失败时中止安装。 |
| 安装时签名验证（verify_signature） | 🔴 高 | 0.5-1.5h | **已实现（PowerShell + signtool 回退）**：已在 `.onInit` 使用 PowerShell `Get-AuthenticodeSignature` 并在失败时回退到 `signtool.exe`；建议后续添加 WinVerifyTrust 回退与更多集成测试。 |
| 安装前系统要求检查（SystemRequirements） | � 已实现 | 0.5-1.5h | **已实现（PowerShell checks）**：已在 `.onInit` 中生成检查；建议做集成测试并考虑 NSIS 插件回退选项。 |
| 依赖检测与条件安装（dependencies） | 🟡 中 | 3-5h | 能检测常见依赖并根据配置执行下载或安装命令（或通过 `post_install` 条件触发）。 |
| 日志记录（LogSet, 日志路径） | 🟢 低 | 1-2h | 支持 `logging.enabled/path` 并在安装过程中写入日志文件。 |
| Finish 页面的“立即运行”选项（run_after_install） | 🟢 低 | 1-2h | 添加 `install.run_after_install` 字段并在 Finish 页面显示复选框以控制 `Exec`/`ExecWait`。 |

> 建议：按优先级先实现网络下载与签名验证（高风险/高价值），并为每项编写对应的单元测试与示例 YAML，随后合并到主分支并在 CI（最好带 Windows runner）上做集成验证。

---

## � 项目健康度评分（按 Config.py 优先）

| 维度 | 评分 | 备注 |
|------|------|------|
| Config.py 完整性 | ⭐⭐⭐⭐☆ | **65% 功能已完整定义**，14 项开箱即用；仍需 5 项新增配置类 |
| Converter 实现 | ⭐⭐⭐⭐☆ | 13 项转换完成，4 项需完善，3 项待实现 |
| 代码质量 | ⭐⭐⭐⭐☆ | 结构清晰，类型注解不足，测试覆盖有限 |
| 文档完整度 | ⭐⭐⭐☆☆ | 基本文档存在，使用示例不足，无 API 文档 |
| 可维护性 | ⭐⭐⭐⭐☆ | 模块化好，扩展点清晰，config 层设计一致性强 |
| 生产就绪度 | ⭐⭐⭐⭐☆ | **Config 层已可用于中小型项目**；Converter 需扩展才能支持企业级特性 |

**总体评分**: ⭐⭐⭐⭐☆ (4/5 星) - **Config 架构稳定，Converter 需迭代**

---

## 📌 核心结论

### ✅ Config.py 的优势
1. **13 项功能已完全支持**，无需修改 `ypack/config.py`（占 65%）
2. **2 项部分支持**，仅需扩展字段（1.5-3h）
3. **5 项待新增**，需创建新数据类（10-14h）
4. **总计 Config 工作量**: ~11.5-17 小时，**可在 1-2 周内完成**

### ⚠️ Converter 的差距
- Config 层已准备好的功能中，Converter 实现仅覆盖 **62%**
- 许多 Config 配置（如 `post_install`）可支持多种用途（安装后运行、依赖检测等），Converter 需增加用例

### 🎯 立即优先级（按 Config.py 完成顺序）
1. **Phase 0（0.5-1h）**: 补充 `languages` 字段到 `PackageConfig` → 多语言支持立即就绪
2. **Phase 1（3-4h）**: 新增 `EnvVarEntry` + `InstallConfig.env_vars` → 环境变量配置完成
3. **Phase 2（2-3h）**: 扩展 `UpdateConfig` 和 `SigningConfig` → 升级/安全校验配置完善
4. **Phase 3（6-8h）**: 新增 `SystemRequirements`, `LoggingConfig`, `FileAssociation` 等

---

## 📝 建议后续动作

### 立即行动（本周）

1. ✅ 完成本评审文档（已做）
2. ☐ 与团队讨论 Config.py 优先级（重点：哪 5 项新增最急需）
3. ☐ 为 Config 层的改动创建 GitHub Issue（含数据类设计）
4. ☐ 编写示例 YAML 和对应的 Converter 适配需求

### 短期（1-2 周）

1. ☐ **优先完成 Config.py 改动** (Phase 0-1，预计 6-8h)
   - 添加 `languages` 字段
   - 新增 `EnvVarEntry` 数据类
   - 更新 `from_yaml()` 和 `from_dict()` 解析逻辑
2. ☐ 为新增 Config 字段编写单元测试
3. ☐ 更新示例 YAML 文件
4. ☐ **然后启动 Converter 适配**（Phase 1，预计 4-6h）

### 中期（2-3 周）

1. ☐ 完成 Phase 2-3 的 Config 改动
2. ☐ 逐个实现 Converter 适配
3. ☐ 发布 v2.0 版本（新增 Config 字段）

### 长期（1 个月）

1. ☐ 完成全部 Converter 实现
2. ☐ 集成测试与文档完善
3. ☐ 发布 v3.0 版本（完整功能）

### 长期（2-3 个月）

1. ☐ 完成 Phase 3（企业级功能）
2. ☐ 性能优化和代码重构
3. ☐ 发布 v3.0 版本（企业版）

---

## 🔧 技术债务与改进建议

### 代码质量

- ☐ 补充 `ypack/config.py` 的类型提示（可用 `mypy` 检查）
- ☐ 为 `convert_nsis.py` 中的长函数添加单元测试
- ☐ 将 NSIS 代码生成逻辑进一步模块化（如 `nsis_helpers.py`）

### 文档

- ☐ 完善 [README.md](../README.md)（补充每个新功能的使用示例）
- ☐ 创建 [YAML_SCHEMA.md](./YAML_SCHEMA.md)（完整的 YAML 配置说明）
- ☐ 维护 [CHANGELOG.md](../CHANGELOG.md)

### 自动化

- ☐ 添加 GitHub Actions CI/CD（自动测试 + 代码质量检查）
- ☐ 在 CI 中生成 NSIS 脚本并验证语法

---

## 📊 项目健康度评分

| 维度 | 评分 | 备注 |
|------|------|------|
| 功能完整性 | ⭐⭐⭐⭐☆ | 55% 功能完成，核心功能齐全，缺少企业级特性 |
| 代码质量 | ⭐⭐⭐⭐☆ | 结构清晰，类型注解不足，测试覆盖有限 |
| 文档完整度 | ⭐⭐⭐☆☆ | 基本文档存在，使用示例不足，无 API 文档 |
| 可维护性 | ⭐⭐⭐⭐☆ | 模块化好，扩展点清晰，未来改动应无大碍 |
| 生产就绪度 | ⭐⭐⭐⭐☆ | 可用于中小型项目，大型项目需扩展 |

**总体评分**: ⭐⭐⭐⭐☆ (4/5 星) - **稳定可用，需持续迭代**

---

**文档编制日期**: 2026-02-05  
**下次评审计划**: 2026-03 月（Phase 1 完成后）
