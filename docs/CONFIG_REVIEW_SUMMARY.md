# Config.py 功能评审 - 快速参考

**日期**: 2026年2月5日  
**关键发现**: Config.py 已支持 **65% 的功能**，可在 **1-2 周内补全配置层**

---

## 📊 一句话总结

| 维度 | 结果 |
|------|------|
| **Config 支持度** | ✅ 15 项完全支持 + ⚠️ 2 项部分 + ❌ 3 项缺失 |
| **立即可用** | 快捷方式、注册表、卸载、权限、许可、路径、进度、文件、界面、安装后运行（10 项） |
| **改进工作量** | ~11.5-17 小时（可 1-2 周完成） |

---

## 🟢 13 项完全支持（无需修改 config.py）

| # | 功能 | Config 字段 | 状态 |
|---|------|-----------|------|
| 1 | 安装主程序文件 | `files`, `packages` | ✅ 生产就绪 |
| 3 | 创建快捷方式 | `install.create_desktop/start_menu_shortcut` | ✅ 生产就绪 |
| 5 | 写入注册表 | `install.registry_entries` | ✅ 支持 32/64 位 |
| 6 | 卸载功能 | (自动生成) | ✅ 完整实现 |
| 9 | 权限检测与提升 | (自动添加) | ✅ admin 模式 |
| 10 | 安装路径选择 | `install.install_dir` | ✅ 支持占位符 |
| 11 | 安装进度显示 | (MUI 框架) | ✅ NSIS 自动提供 |
| 12 | 许可协议展示 | `app.license` | ✅ EULA 页面 |
| 14 | 配置文件生成 | `files`, `packages[].post_install` | ✅ 支持脚本 |
| 15 | 日志记录 | `logging` | ✅ 支持（`LogSet`） |
| 16 | 安装后自动运行 | `packages[].post_install` | ✅ 通过 ExecWait |
| 19 | 自定义界面 | `app.icon`, `custom_nsis_includes` | ✅ 支持品牌化 |

---

## 🟡 2 项部分支持（需扩展字段）

| # | 功能 | Config 现状 | 缺失字段 | 工作量 |
|---|------|-----------|---------|--------|
| 8 | 升级/修复 | `UpdateConfig` 存在 | `download_url`, `backup_on_upgrade`, `repair_enabled` | 1-2h |
| 20 | 安全校验 | `SigningConfig` 存在 | `verify_signature`, `checksum_type`, `checksum_value` | 0.5-1h |

---

## 🔴 4 项完全缺失（需新增配置类）

| # | 功能 | 新数据类 | 所属节点 | 工作量 |
|---|------|---------|---------|--------|
| 4 | 注册环境变量 | `EnvVarEntry` | `InstallConfig.env_vars` | 2-3h |
| 7 | 多语言支持 | (已实现) | `PackageConfig.languages` | 0.5-1h |
| 15 | 日志记录 | `LoggingConfig` | `PackageConfig.logging` | ✅ 已实现 |
| 17 | 文件关联 | `FileAssociation` | `InstallConfig.file_associations` | 2-3h |
| 18 | 网络下载/校验 | (扩展 FileEntry) | `FileEntry.download_url`, `checksum_*` | 2-3h |

---

## 🚀 优先级排序（按 config.py 工作量）

### Phase 0（0.5-1h） - 最小改动，快速验证

```python
# 在 PackageConfig 中添加
languages: List[str] = field(default_factory=lambda: ["English"])
```

→ 多语言配置立即支持

### Phase 1（3-4h） - 高频需求，立即优先

1. `EnvVarEntry` 数据类（环境变量）
2. 更新 `from_yaml()` 和 `from_dict()` 解析

### Phase 2（2-3h） - 扩展现有配置

1. `UpdateConfig` 新增字段
2. `SigningConfig` 新增字段

### Phase 3（6-8h） - 新增次要功能

1. `SystemRequirements` 数据类
2. `LoggingConfig` 数据类
3. `FileAssociation` 数据类
4. `FileEntry` 扩展（下载/校验）

---

## 📝 Config.py 改动检查清单

### Phase 0 - 多语言

- [x] 在 `PackageConfig` 中添加 `languages: List[str]` 字段
- [x] 在 `from_yaml()` 和 `from_dict()` 中解析该字段
- [x] 更新示例 YAML

#### 示例 / Example

在 YAML 中添加 `languages` 字段以启用多语言生成：

```yaml
languages:
  - English
  - SimplifiedChinese
```

常见 MUI 语言标识示例（可用值不限于此）：

- English
- SimplifiedChinese
- TraditionalChinese
- French
- German
- Spanish
- Japanese
- Korean
- Russian

说明：转换器会为每个语言输出 `!insertmacro MUI_LANGUAGE "<lang>"`，默认回退到 `English`。

### Phase 1 - 环境变量

- [x] 创建 `EnvVarEntry` 数据类
- [x] 在 `InstallConfig` 中添加 `env_vars: List[EnvVarEntry]` 字段
- [x] 在 `from_yaml()` 中解析
- [x] 编写单元测试
- [x] 更新示例 YAML

说明：支持 `PATH` 的 `append: true` 行为，包含基本归一化（分隔符归一、去重、大小写规范化的尝试）与卸载时的精确移除逻辑。

### Phase 2 - 升级和安全

- [x] 在 `UpdateConfig` 中添加字段：
  - `download_url: str`
  - `backup_on_upgrade: bool`
  - `repair_enabled: bool`
- [x] 在 `SigningConfig` 中添加字段：
  - `verify_signature: bool`
  - `checksum_type: str`
  - `checksum_value: str`
- [x] 更新解析逻辑

说明：

- `UpdateConfig` 新增字段会被写入安装时的注册表（`UpdateURL`, `DownloadURL`, `BackupOnUpgrade`, `RepairEnabled`），供应用读取以实现自动更新/备份/修复流程。
- `UpdateConfig` 现在支持可配置注册表目标：`registry_hive`（`HKLM` 或 `HKCU`）和 `registry_key`（自定义注册表路径），可用于写入 per-user 或 system-wide 的更新元数据。
- `SigningConfig` 新增字段用于在生成的脚本中记录是否要进行签名后的校验（`verify_signature`）以及校验使用的 `checksum_type`/`checksum_value`（仅记录于安装脚本注释，由外部流程负责实际校验）。

### Phase 3 - 系统要求、日志、文件关联、下载

- [x] 创建 `SystemRequirements` 数据类
- [x] 创建 `LoggingConfig` 数据类
- [x] 创建 `FileAssociation` 数据类
- [x] 扩展 `FileEntry`：
  - `download_url: str`
  - `checksum_type: str`
  - `checksum_value: str`
  - `decompress: bool`
- [x] 更新所有解析函数
- [x] 单元测试

说明：

- `SystemRequirements`：支持 `min_windows_version`、`min_free_space_mb`、`min_ram_mb` 与 `require_admin`，可在安装前做基础检查（当前仅作为配置与占位，后续可把检查逻辑加入安装脚本）。
- `LoggingConfig`：用于记录安装过程的日志路径和日志级别（已解析为 `PackageConfig.logging`，可用于未来在安装器中启用日志写入）。
- `FileAssociation`：支持完整注册（写入 `ProgID` 描述、`DefaultIcon`、verbs 命令）并区分 system (`HKCR`) 与 per-user (`HKCU\\Software\\Classes`) 注册。卸载时会删除对应键。
- `FileEntry` 扩展：增加 `download_url`、`checksum_type`/`checksum_value` 与 `decompress` 字段；转换器会在生成的 NSIS 脚本中对这些字段添加说明性注释（后续可以集成实际下载/校验/解压实现）。

---

## 🔧 未完成的 Converter 实现（需优先跟进） ✅

以下是目前 config 层已就绪但转换器仍需要实现或完善的关键功能：

- [ ] 网络下载与完整性校验（高优先）
  - 状态：**部分实现** — 生成器现在会输出 `inetc::get` 下载调用，并生成 `VerifyChecksum` / `ExtractArchive` 占位函数；已添加单元测试验证脚本包含下载和占位调用。但占位函数尚未执行真实的哈希校验或解压。
  - 下一步（建议）：集成真实的校验实现（例如使用 NSIS hash 插件或调用外部校验工具），并集成解压工具（`nsisunz` 或 7-Zip），补充集成测试。
  - 预估：2-4 小时（实现校验和/解压并添加集成测试）。验收条件：生成的 NSIS 脚本能下载 URL、验证 SHA256/MD5 并在失败时中止安装；支持自动解压并在失败时报错。

- [x] 安装时的签名验证（高优先）
  - 状态：**已实现（PowerShell + signtool 回退）** — 生成器在 `.onInit` 中添加了 PowerShell `Get-AuthenticodeSignature` 的调用，并在失败时检测并调用 `signtool.exe verify /pa "$EXEPATH"`；如两者均不可用或验证失败则 `MessageBox` + `Abort`。已添加单元测试以验证脚本中包含相关验证逻辑与回退代码。
  - 下一步（建议）：在环境/策略受限的机器上做集成验证，并考虑增加 WinVerifyTrust API 调用作为更稳健的本地回退（可选）。
  - 预估：0.5-1.5 小时（额外回退方案与集成测试）。验收条件：在可用工具下正确验证并在失败时中止安装；在工具缺失时提供友好提示并中止。

- [x] 安装前系统要求强制检查（中优先）
  - 状态：**已实现** — 生成器在 `.onInit` 中添加了 Windows 版本、磁盘空间与内存检查（使用 PowerShell），并在不满足时提示并中止安装。
  - 下一步（建议）：在无 PowerShell 或策略受限的系统上做集成测试，并考虑添加 NSIS 插件作为可选回退以减少依赖。
  - 预估：0.5-1.5 小时（集成测试与可选插件实现）。验收条件：检测按配置生效，不满足时中止安装；集成测试覆盖主要 Windows 版本。

- [ ] 依赖组件检测与自动安装（中优先）
  - 状态：无 `install.dependencies` 条目与生成逻辑（需新增 schema 和转换器支持）。
  - 预估：3-5 小时。验收条件：能在安装开始时检测依赖是否存在并根据配置有条件地执行下载/安装命令（或跳过）。

- [x] 日志记录（低到中优先）
  - 状态：**已实现** — 支持 `PackageConfig.logging`，生成器会输出 `LogSet on` 以及日志路径/级别的注释；卸载段也包含日志启用注释。已添加单元测试验证输出。
  - 下一步（建议）：在真实 Windows 机器上验证日志文件位置/权限并添加可选的日志轮换或包含卸载日志的选项。
  - 预估：0.5-1 小时（集成验证与额外选项）。验收条件：可配置日志路径并在安装/卸载过程中记录基本日志事件。

- [ ] 安装结束“立即运行应用”复选框（低优先）
  - 状态：当前可通过 `post_install` 变通执行，但缺少 Finish 页面复选框与专用 `run_after_install` 字段。
  - 预估：1-2 小时。验收条件：支持 `install.run_after_install` 字段并在 Finish 页面呈现可勾选的“立即运行”选项。

> 建议后续动作：为上述每项创建 GitHub Issue（标注优先级与验收条件），按重要性依次实现并通过单元测试验证（优先实现下载/校验与签名验证）。

---

## 🎯 立即建议

### 本周（立即）

1. ✅ **完成本评审**（已做）
2. ☐ **启动 Phase 0**（0.5-1h，快速赢）
3. ☐ **规划 Phase 1-3** 优先级（与团队讨论）

### 下周（1 周内）

1. ☐ **完成 Phase 0-1** 的 config.py 改动（~4h）
2. ☐ 编写测试和示例
3. ☐ **发布 v1.1** 或 **v2.0-beta**（新增配置字段）

### 后续

1. ☐ Phase 2-3 逐步实现
2. ☐ Converter 适配跟上
3. ☐ 发布完整版本

---

## 💡 实现提示

- 参考现有 `AppInfo`, `FileEntry` 等的实现模式（类型一致）
- 使用 `field(default_factory=...)` 处理列表和复杂对象
- 更新 `from_dict()` 方法解析 YAML 中的新字段
- 编写对应的单元测试（见 [tests/test_config.py](../tests/test_config.py)）
- 更新示例 YAML 文件展示新配置

---

**文档**: 完整版评审见 [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md)
