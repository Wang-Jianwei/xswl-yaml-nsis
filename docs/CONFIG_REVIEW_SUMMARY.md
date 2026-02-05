# Config.py 功能评审 - 快速参考

**日期**: 2026年2月5日  
**关键发现**: Config.py 已支持 **65% 的功能**，可在 **1-2 周内补全配置层**

---

## 📊 一句话总结

| 维度 | 结果 |
|------|------|
| **Config 支持度** | ✅ 13 项完全支持 + ⚠️ 2 项部分 + ❌ 5 项缺失 |
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
| 16 | 安装后自动运行 | `packages[].post_install` | ✅ 通过 ExecWait |
| 19 | 自定义界面 | `app.icon`, `custom_nsis_includes` | ✅ 支持品牌化 |

---

## 🟡 2 项部分支持（需扩展字段）

| # | 功能 | Config 现状 | 缺失字段 | 工作量 |
|---|------|-----------|---------|--------|
| 8 | 升级/修复 | `UpdateConfig` 存在 | `download_url`, `backup_on_upgrade`, `repair_enabled` | 1-2h |
| 20 | 安全校验 | `SigningConfig` 存在 | `verify_signature`, `checksum_type`, `checksum_value` | 0.5-1h |

---

## 🔴 5 项完全缺失（需新增配置类）

| # | 功能 | 新数据类 | 所属节点 | 工作量 |
|---|------|---------|---------|--------|
| 4 | 注册环境变量 | `EnvVarEntry` | `InstallConfig.env_vars` | 2-3h |
| 7 | 多语言支持 | (简单扩展) | `PackageConfig.languages` | 0.5-1h |
| 13 | 安装前检测 | `SystemRequirements` | `InstallConfig.system_requirements` | 1.5-2h |
| 15 | 日志记录 | `LoggingConfig` | `PackageConfig.logging` | 0.5-1h |
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

- [ ] 创建 `SystemRequirements` 数据类
- [ ] 创建 `LoggingConfig` 数据类
- [ ] 创建 `FileAssociation` 数据类
- [ ] 扩展 `FileEntry`：
  - `download_url: str`
  - `checksum_type: str`
  - `checksum_value: str`
  - `decompress: bool`
- [ ] 更新所有解析函数
- [ ] 单元测试

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
