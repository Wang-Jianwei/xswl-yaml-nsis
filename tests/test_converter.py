"""Tests for the NSIS converter — output correctness."""

from __future__ import annotations

import pytest

from ypack.config import (
    AppInfo,
    EnvVarEntry,
    ExistingInstallConfig,
    FileAssociation,
    FileEntry,
    InstallConfig,
    LoggingConfig,
    PackageConfig,
    PackageEntry,
    RegistryEntry,
    SigningConfig,
    SystemRequirements,
    UpdateConfig,
)
from ypack.converters.convert_nsis import YamlToNsisConverter


def _simple_config(**overrides) -> PackageConfig:
    """Return a minimal PackageConfig for testing."""
    base = {
        "app": {"name": "TestApp", "version": "1.0.0", "publisher": "Pub", "description": "Desc"},
        "install": {},
        "files": [{"source": "test.exe"}],
    }
    base.update(overrides)
    return PackageConfig.from_dict(base)


class TestConverterBasics:
    def test_init(self):
        c = YamlToNsisConverter(_simple_config())
        assert c.config.app.name == "TestApp"

    def test_convert_has_essentials(self):
        script = YamlToNsisConverter(_simple_config()).convert()
        assert "!define APP_NAME" in script
        assert "Unicode true" in script
        assert 'Section "Install"' in script
        assert 'Section "Uninstall"' in script
        assert "MUI2.nsh" in script

    def test_includes_filefunc(self):
        """Ensure helper macros used by the generator are included (regression test).
        """
        script = YamlToNsisConverter(_simple_config()).convert()
        assert '!include "FileFunc.nsh"' in script

    def test_license_define_in_header(self):
        """LICENSE_FILE should be defined in the header (before MUI2 include)."""
        cfg = _simple_config(app={"name": "T", "version": "1.0", "publisher": "P", "license": "./LICENSE"})
        script = YamlToNsisConverter(cfg).convert()
        assert '!define "LICENSE_FILE"' not in script  # sanity: no malformed define
        assert '!define LICENSE_FILE' in script
        assert 'LicenseData "${LICENSE_FILE}"' in script
        # Ensure both the define and LicenseData are present before the MUI include (general settings)
        assert script.index('!define LICENSE_FILE') < script.index('!include "MUI2.nsh"')
        assert script.index('LicenseData "${LICENSE_FILE}"') < script.index('!include "MUI2.nsh"')
        # Ensure license page insertion occurs after the MUI include
        assert script.index('!include "MUI2.nsh"') < script.index('!insertmacro MUI_PAGE_LICENSE "${LICENSE_FILE}"')

    def test_variable_resolution(self):
        cfg = _simple_config()
        conv = YamlToNsisConverter(cfg, cfg._raw_dict)
        assert conv.resolve_variables("$PROGRAMFILES64\\${app.name}") == "$PROGRAMFILES64\\TestApp"


class TestInstallerSection:
    def test_file_directive(self):
        script = YamlToNsisConverter(_simple_config()).convert()
        assert 'File "test.exe"' in script
        assert "WriteUninstaller" in script
        assert "WriteRegStr" in script

    def test_setoutpath_per_destination(self):
        """Files with different destinations should each get SetOutPath."""
        cfg = PackageConfig.from_dict({
            "app": {"name": "T", "version": "1"},
            "install": {},
            "files": [
                {"source": "a.exe", "destination": "$INSTDIR"},
                {"source": "b.dll", "destination": "$INSTDIR\\lib"},
            ],
        })
        script = YamlToNsisConverter(cfg).convert()
        assert 'SetOutPath "$INSTDIR"' in script
        assert 'SetOutPath "$INSTDIR\\lib"' in script

    def test_shortcuts(self):
        cfg = _simple_config()
        cfg.install.desktop_shortcut_target = "$INSTDIR\\TestApp.exe"
        cfg.install.start_menu_shortcut_target = "$INSTDIR\\TestApp.exe"
        script = YamlToNsisConverter(cfg).convert()
        assert "CreateShortCut" in script
        assert "$DESKTOP" in script
        assert "$SMPROGRAMS" in script

    def test_remote_file(self):
        cfg = _simple_config()
        cfg.files = [FileEntry(source="https://x.com/f.bin", checksum_type="sha256", checksum_value="abc", decompress=True)]
        script = YamlToNsisConverter(cfg).convert()
        assert "inetc" in script.lower() or "inetc::get" in script
        assert "https://x.com/f.bin" in script
        assert "VerifyChecksum" in script
        assert "ExtractArchive" in script

    def test_file_associations(self):
        cfg = _simple_config()
        cfg.install.file_associations = [
            FileAssociation(extension=".foo", prog_id="Foo.File", description="Foo", application="$INSTDIR\\Foo.exe", default_icon="$INSTDIR\\icons\\foo.ico", verbs={"open": '$INSTDIR\\Foo.exe "%1"'}),
        ]
        script = YamlToNsisConverter(cfg).convert()
        assert 'WriteRegStr HKCR ".foo"' in script
        assert "Foo.File" in script
        assert "DefaultIcon" in script
        # Uninstall removes it
        assert 'DeleteRegKey HKCR ".foo"' in script


class TestUninstallerSection:
    def test_removes_files(self):
        script = YamlToNsisConverter(_simple_config()).convert()
        assert "Delete" in script
        assert "DeleteRegKey" in script
        assert 'RMDir "$INSTDIR"' in script

    def test_removes_shortcuts(self):
        cfg = _simple_config()
        cfg.install.desktop_shortcut_target = "$INSTDIR\\T.exe"
        script = YamlToNsisConverter(cfg).convert()
        assert 'Delete "$DESKTOP\\${APP_NAME}.lnk"' in script


class TestSigningSection:
    def test_disabled(self):
        script = YamlToNsisConverter(_simple_config()).convert()
        assert "!finalize" not in script

    def test_enabled(self):
        cfg = _simple_config()
        cfg.signing = SigningConfig(enabled=True, certificate="c", password="p", timestamp_url="t", verify_signature=True, checksum_type="sha256", checksum_value="abc")
        script = YamlToNsisConverter(cfg).convert()
        assert "!finalize" in script
        assert "Verify after build: True" in script


class TestUpdateSection:
    def test_disabled(self):
        script = YamlToNsisConverter(_simple_config()).convert()
        assert "UPDATE_URL" not in script

    def test_enabled(self):
        cfg = _simple_config()
        cfg.update = UpdateConfig(enabled=True, update_url="https://u", download_url="https://d", backup_on_upgrade=True)
        script = YamlToNsisConverter(cfg).convert()
        assert '!define UPDATE_URL "https://u"' in script
        assert '!define DOWNLOAD_URL "https://d"' in script

    def test_custom_registry(self):
        cfg = _simple_config()
        cfg.update = UpdateConfig(enabled=True, update_url="https://u", download_url="https://d", registry_hive="HKCU", registry_key="Software\\MyUpdate")
        script = YamlToNsisConverter(cfg).convert()
        assert 'WriteRegStr HKCU "Software\\MyUpdate"' in script


class TestEnvVars:
    def test_simple_write_and_remove(self):
        cfg = _simple_config()
        cfg.install.env_vars = [EnvVarEntry(name="MYVAR", value="C:\\x", scope="system")]
        script = YamlToNsisConverter(cfg).convert()
        assert 'WriteRegStr HKLM' in script
        assert '"MYVAR"' in script
        assert 'DeleteRegValue HKLM' in script

    def test_path_append(self):
        cfg = _simple_config()
        cfg.install.env_vars = [EnvVarEntry(name="PATH", value="$INSTDIR\\bin", scope="system", append=True)]
        script = YamlToNsisConverter(cfg).convert()
        assert "Function _StrContains" in script
        assert "Function un._RemovePathEntry" in script
        assert "Call _StrContains" in script


class TestRegistryEntries:
    def test_string_and_dword(self):
        cfg = _simple_config()
        cfg.install.registry_entries = [
            RegistryEntry(hive="HKLM", key="Software\\T", name="URL", value="https://x", type="string", view="64"),
            RegistryEntry(hive="HKCU", key="Software\\T", name="On", value="1", type="dword", view="32"),
        ]
        script = YamlToNsisConverter(cfg).convert()
        assert 'WriteRegStr HKLM "Software\\T" "URL"' in script
        assert 'WriteRegDWORD HKCU "Software\\T" "On" 1' in script
        assert "SetRegView 64" in script
        assert "SetRegView 32" in script
        # Uninstall
        assert 'DeleteRegValue HKLM "Software\\T" "URL"' in script


class TestPackageSections:
    def test_no_packages(self):
        script = YamlToNsisConverter(_simple_config()).convert()
        assert "MUI_PAGE_COMPONENTS" not in script

    def test_with_packages(self):
        cfg = PackageConfig.from_dict({
            "app": {"name": "M", "version": "2"},
            "install": {},
            "files": [],
            "packages": {
                "app": {"sources": [{"source": "app/**/*", "destination": "$INSTDIR"}], "optional": False},
                "drv": {"sources": [{"source": "drv/*", "destination": "$INSTDIR\\drv"}], "optional": True, "default": False},
            },
        })
        script = YamlToNsisConverter(cfg).convert()
        assert "MUI_PAGE_COMPONENTS" in script
        assert 'Section "app"' in script
        assert 'Section "drv"' in script

    def test_post_install(self):
        cfg = PackageConfig.from_dict({
            "app": {"name": "P", "version": "1"},
            "install": {},
            "files": [],
            "packages": {"drv": {"sources": [{"source": "d/*", "destination": "$INSTDIR\\d"}], "post_install": ["$INSTDIR\\d\\install.cmd"]}},
        })
        script = YamlToNsisConverter(cfg).convert()
        assert 'ExecWait "$INSTDIR\\d\\install.cmd"' in script

    def test_section_groups(self):
        cfg = PackageConfig.from_dict({
            "app": {"name": "G", "version": "1"},
            "install": {},
            "files": [],
            "packages": {
                "Drivers": {
                    "children": {
                        "PXI": {"sources": [{"source": "pxi/*", "destination": "$INSTDIR\\pxi"}], "optional": True},
                    }
                }
            },
        })
        script = YamlToNsisConverter(cfg).convert()
        assert 'SectionGroup "Drivers"' in script
        assert 'Section "PXI"' in script


class TestLanguages:
    def test_multi_language(self):
        cfg = _simple_config()
        cfg.languages = ["English", "SimplifiedChinese"]
        script = YamlToNsisConverter(cfg).convert()
        assert 'MUI_LANGUAGE "English"' in script
        assert 'MUI_LANGUAGE "SimplifiedChinese"' in script


class TestLogging:
    def test_enabled(self):
        cfg = _simple_config()
        cfg.logging = LoggingConfig(enabled=True, path="$APPDATA\\${APP_NAME}\\install.log", level="DEBUG")
        script = YamlToNsisConverter(cfg).convert()
        assert "LogSet on" in script
        # Ensure the LogSet is enabled inside .onInit
        start = script.index('Function .onInit')
        end = script.index('FunctionEnd', start)
        assert 'LogSet on' in script[start:end]
        # Guard with compile-time check so builds without NSIS logging don't fail
        assert '!ifdef NSIS_CONFIG_LOG' in script
        # LOG_FILE define should be set
        assert '!define LOG_FILE' in script
        # Logging macros should be present
        assert '!macro LogInit' in script
        assert '!macro LogWrite' in script
        assert '!macro LogClose' in script
        # Install section should use the logging macros
        assert '!insertmacro LogInit "Install"' in script
        assert '!insertmacro LogWrite' in script
        assert '!insertmacro LogClose' in script
        # Uninstall section should also use logging macros
        assert '!insertmacro LogInit "Uninstall"' in script

    def test_log_macros_not_emitted_when_disabled(self):
        cfg = _simple_config()
        cfg.logging = LoggingConfig(enabled=False)
        script = YamlToNsisConverter(cfg).convert()
        assert '!macro LogInit' not in script
        assert '!insertmacro LogInit' not in script


class TestFinishRun:
    def test_finish_run(self):
        cfg = _simple_config()
        cfg.install.launch_on_finish = "$INSTDIR\\MyApp.exe"
        cfg.install.launch_on_finish_label = "Run MyApp"
        script = YamlToNsisConverter(cfg).convert()
        assert 'MUI_FINISHPAGE_RUN "$INSTDIR\\MyApp.exe"' in script
        assert 'MUI_FINISHPAGE_RUN_TEXT "Run MyApp"' in script

    def test_finish_run_label_resolution(self):
        cfg = _simple_config()
        cfg.install.launch_on_finish = "$INSTDIR\\MyApp.exe"
        cfg.install.launch_on_finish_label = "Run ${app.name}"
        script = YamlToNsisConverter(cfg).convert()
        assert 'MUI_FINISHPAGE_RUN_TEXT "Run TestApp"' in script


class TestOnInit:
    def test_signature_verification(self):
        cfg = _simple_config()
        cfg.signing = SigningConfig(enabled=True, certificate="c", password="p", verify_signature=True)
        script = YamlToNsisConverter(cfg).convert()
        assert "Signature verification failed" in script

    # --- Installer Mutex ---
    def test_installer_mutex(self):
        """Every installer should have a mutex to prevent concurrent runs."""
        script = YamlToNsisConverter(_simple_config()).convert()
        assert "CreateMutex" in script
        assert "${APP_NAME}_InstallerMutex" in script

    # --- Existing-install detection (string shorthand compat) ---
    def test_existing_install_prompt_uninstall(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="prompt_uninstall")
        script = YamlToNsisConverter(cfg).convert()
        assert 'ReadRegStr $R0 HKLM "${REG_KEY}" "InstallPath"' in script
        assert 'IfFileExists "$R1\\Uninstall.exe" _ei_has_uninst _ei_overwrite_only' in script
        assert 'IDYES _ei_do_uninstall IDNO _ei_cancel' in script

    def test_existing_install_auto_uninstall(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="auto_uninstall")
        script = YamlToNsisConverter(cfg).convert()
        assert 'Goto _ei_do_uninstall' in script
        assert 'ExecWait' in script

    def test_existing_install_overwrite(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="overwrite")
        script = YamlToNsisConverter(cfg).convert()
        assert 'Overwrite mode: skip uninstall' in script

    def test_existing_install_abort(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="abort")
        script = YamlToNsisConverter(cfg).convert()
        assert 'Installation aborted.' in script

    def test_existing_install_none_skips_check(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="none")
        script = YamlToNsisConverter(cfg).convert()
        assert 'Existing-install detection' not in script

    def test_existing_install_default_is_prompt(self):
        cfg = _simple_config()
        assert cfg.install.existing_install.mode == "prompt_uninstall"
        script = YamlToNsisConverter(cfg).convert()
        assert 'IDYES _ei_do_uninstall IDNO _ei_cancel' in script

    # --- String shorthand backward compat ---
    def test_string_shorthand_backward_compat(self):
        """existing_install: 'auto_uninstall' (plain string) should still work."""
        cfg = PackageConfig.from_dict({
            "app": {"name": "T", "version": "1.0.0"},
            "install": {"existing_install": "auto_uninstall"},
            "files": [{"source": "t.exe"}],
        })
        assert cfg.install.existing_install.mode == "auto_uninstall"

    # --- Version check ---
    def test_version_check_enabled(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="prompt_uninstall", version_check=True)
        script = YamlToNsisConverter(cfg).convert()
        assert 'ReadRegStr $R2 HKLM "${REG_KEY}" "Version"' in script
        assert 'StrCmp $R2 "${APP_VERSION}" _ei_done' in script

    def test_version_check_disabled_no_version_skip(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="prompt_uninstall", version_check=False)
        script = YamlToNsisConverter(cfg).convert()
        assert 'StrCmp $R2 "${APP_VERSION}" _ei_done' not in script

    # --- allow_multiple ---
    def test_allow_multiple_enabled(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="prompt_uninstall", allow_multiple=True)
        script = YamlToNsisConverter(cfg).convert()
        assert 'allow_multiple: only conflict when installing to the same directory' in script
        assert 'StrCmp $R0 "$INSTDIR" 0 _ei_done' in script

    def test_allow_multiple_legacy_field(self):
        """Legacy allow_multiple_installations should set allow_multiple."""
        cfg = PackageConfig.from_dict({
            "app": {"name": "T", "version": "1.0.0"},
            "install": {"allow_multiple_installations": True},
            "files": [{"source": "t.exe"}],
        })
        assert cfg.install.existing_install.allow_multiple is True

    # --- Show version info in prompt ---
    def test_show_version_info(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="prompt_uninstall", show_version_info=True)
        script = YamlToNsisConverter(cfg).convert()
        assert 'version $R2' in script

    def test_show_version_info_in_abort(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="abort", show_version_info=True)
        script = YamlToNsisConverter(cfg).convert()
        assert 'version $R2' in script

    # --- Wait loop ---
    def test_uninstall_wait_loop(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="auto_uninstall", uninstall_wait_ms=3000)
        cfg.logging = LoggingConfig(enabled=True, path="$INSTDIR\\install.log")
        script = YamlToNsisConverter(cfg).convert()
        assert '_ei_wait_loop:' in script
        assert 'IntCmp $R3 3000' in script
        assert 'Sleep 500' in script
        # Should log actions
        assert '!insertmacro LogWrite "Running existing uninstaller' in script
        assert f'!insertmacro LogWrite "Waiting for uninstaller to finish (up to 3000ms)"' in script
        # Retry dialog on failure
        assert 'MB_RETRYCANCEL' in script

    def test_uninstall_infinite_wait(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="auto_uninstall", uninstall_wait_ms=-1)
        script = YamlToNsisConverter(cfg).convert()
        assert '_ei_wait_loop:' in script
        # Infinite wait should not emit an IntCmp bound check
        assert 'IntCmp $R3' not in script
        assert 'no timeout' in script
        assert 'Sleep 500' in script
        # Should still include retry dialog if something goes wrong
        assert 'MB_RETRYCANCEL' in script
        # With logging enabled, we should log wait start and finish
        cfg.logging = LoggingConfig(enabled=True, path="$INSTDIR\\install.log")
        script = YamlToNsisConverter(cfg).convert()
        assert '!insertmacro LogWrite "Waiting for uninstaller to finish (no timeout)"' in script
        assert '!insertmacro LogWrite "Uninstaller finished."' in script

    # --- Custom uninstaller args ---
    def test_custom_uninstaller_args(self):
        cfg = _simple_config()
        cfg.install.existing_install = ExistingInstallConfig(mode="auto_uninstall", uninstaller_args='/S _?=$R1')
        script = YamlToNsisConverter(cfg).convert()
        assert '/S _?=$R1' in script

    def test_system_requirements(self):
        cfg = _simple_config()
        cfg.install.system_requirements = SystemRequirements(min_windows_version="10.0", min_free_space_mb=500, min_ram_mb=2048, require_admin=True)
        script = YamlToNsisConverter(cfg).convert()
        assert "Requires Windows 10.0 or higher" in script
        assert "500 MB" in script
        assert "2048 MB" in script
        assert "UserInfo::GetAccountType" in script


class TestUnOnInit:
    """Tests for the un.onInit function."""
    def test_uninstaller_mutex(self):
        script = YamlToNsisConverter(_simple_config()).convert()
        assert "Function un.onInit" in script
        assert "${APP_NAME}_UninstallerMutex" in script

    def test_uninstaller_logging(self):
        cfg = _simple_config()
        cfg.logging = LoggingConfig(enabled=True, path="$INSTDIR\\install.log")
        script = YamlToNsisConverter(cfg).convert()
        # un.onInit should contain LogSet
        start = script.index("Function un.onInit")
        end = script.index("FunctionEnd", start)
        uninit_block = script[start:end]
        assert "LogSet on" in uninit_block


class TestARPRegistry:
    """Tests for enhanced Add/Remove Programs registry entries."""
    def test_quiet_uninstall_string(self):
        script = YamlToNsisConverter(_simple_config()).convert()
        assert 'QuietUninstallString' in script

    def test_install_location(self):
        script = YamlToNsisConverter(_simple_config()).convert()
        assert '"InstallLocation" "$INSTDIR"' in script

    def test_no_modify_no_repair(self):
        script = YamlToNsisConverter(_simple_config()).convert()
        assert '"NoModify" 1' in script
        assert '"NoRepair" 1' in script

    def test_display_icon_with_icon(self):
        cfg = _simple_config(app={"name": "T", "version": "1", "install_icon": "logo.ico"})
        script = YamlToNsisConverter(cfg).convert()
        assert '"DisplayIcon"' in script


class TestConverterRegistry:
    def test_registry_has_nsis(self):
        from ypack.converters import CONVERTER_REGISTRY, get_converter_class
        assert "nsis" in CONVERTER_REGISTRY
        assert get_converter_class("nsis") is YamlToNsisConverter

    def test_unknown_format_raises(self):
        from ypack.converters import get_converter_class
        with pytest.raises(ValueError, match="Unknown format"):
            get_converter_class("unknown")

    def test_build_context_receives_tool_name(self):
        cfg = _simple_config()
        conv = YamlToNsisConverter(cfg)
        assert conv.ctx.target_tool == "nsis"

    def test_output_extension(self):
        from ypack.converters import OUTPUT_EXTENSIONS
        assert OUTPUT_EXTENSIONS["nsis"] == ".nsi"
