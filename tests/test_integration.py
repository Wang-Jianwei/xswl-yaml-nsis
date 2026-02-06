"""End-to-end integration tests.

Each test writes a YAML config, runs the full conversion pipeline,
and verifies the generated .nsi script.
"""

from __future__ import annotations

import os
import textwrap

import pytest

from ypack.config import PackageConfig
from ypack.converters import YamlToNsisConverter


@pytest.fixture()
def simple_yaml(tmp_path):
    p = tmp_path / "simple.yaml"
    p.write_text(
        textwrap.dedent("""\
            app:
              name: IntegApp
              version: "2.3.4"
              publisher: "IntegPub"
              description: "Integration test"
            install:
              install_dir: "$PROGRAMFILES64\\\\IntegApp"
              desktop_shortcut_target: "$INSTDIR\\\\IntegApp.exe"
            files:
              - IntegApp.exe
              - source: "data/*"
                destination: "$INSTDIR\\\\data"
                recursive: true
            languages:
              - English
              - SimplifiedChinese
        """),
        encoding="utf-8",
    )
    return str(p)


@pytest.fixture()
def full_yaml(tmp_path):
    p = tmp_path / "full.yaml"
    p.write_text(
        textwrap.dedent("""\
            app:
              name: FullApp
              version: "1.0.0"
              publisher: "FullPub"
              description: "Full test"
              license: "LICENSE.txt"
            install:
              install_dir: "$PROGRAMFILES64\\\\FullApp"
              desktop_shortcut_target: "$INSTDIR\\\\FullApp.exe"
              start_menu_shortcut_target: "$INSTDIR\\\\FullApp.exe"
              registry_entries:
                - hive: HKLM
                  key: "Software\\\\FullApp"
                  name: InstallPath
                  value: "$INSTDIR"
                  type: string
                  view: "64"
              env_vars:
                - name: FULLAPP_HOME
                  value: "$INSTDIR"
                  scope: system
                - name: PATH
                  value: "$INSTDIR\\\\bin"
                  scope: system
                  append: true
              file_associations:
                - extension: ".fa"
                  prog_id: FullApp.File
                  description: "FullApp Document"
                  application: "$INSTDIR\\\\FullApp.exe"
                  default_icon: "$INSTDIR\\\\icons\\\\doc.ico"
                  verbs:
                    open: '$INSTDIR\\\\FullApp.exe "%1"'
              system_requirements:
                min_windows_version: "10.0"
                min_free_space_mb: 200
                min_ram_mb: 1024
                require_admin: true
              launch_on_finish: "$INSTDIR\\\\FullApp.exe"
              launch_on_finish_label: "Launch FullApp"
            files:
              - FullApp.exe
              - source: "lib/*"
                destination: "$INSTDIR\\\\lib"
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
                        destination: "$INSTDIR\\\\pxi"
                    optional: true
                    default: false
                    post_install:
                      - "$INSTDIR\\\\pxi\\\\setup.cmd"
            signing:
              enabled: true
              certificate: "cert.pfx"
              password: "secret"
              timestamp_url: "http://ts.example.com"
              verify_signature: true
            update:
              enabled: true
              update_url: "https://example.com/latest.json"
              download_url: "https://example.com/download"
              backup_on_upgrade: true
            logging:
              enabled: true
              path: "$APPDATA\\\\FullApp\\\\install.log"
              level: DEBUG
            languages:
              - English
              - SimplifiedChinese
        """),
        encoding="utf-8",
    )
    return str(p)


class TestSimpleIntegration:
    def test_load_and_convert(self, simple_yaml, tmp_path):
        cfg = PackageConfig.from_yaml(simple_yaml)
        assert cfg.app.name == "IntegApp"
        assert len(cfg.files) == 2

        conv = YamlToNsisConverter(cfg, cfg._raw_dict)
        nsi = conv.convert()

        # Basic output checks
        assert "Unicode true" in nsi
        assert '!define APP_NAME "IntegApp"' in nsi
        assert '!define APP_VERSION "2.3.4"' in nsi
        assert 'MUI_LANGUAGE "English"' in nsi
        assert 'MUI_LANGUAGE "SimplifiedChinese"' in nsi
        assert 'File "IntegApp.exe"' in nsi
        assert 'SetOutPath "$INSTDIR\\data"' in nsi
        assert "CreateShortCut" in nsi

    def test_save_file(self, simple_yaml, tmp_path):
        cfg = PackageConfig.from_yaml(simple_yaml)
        conv = YamlToNsisConverter(cfg, cfg._raw_dict)
        out = str(tmp_path / "installer.nsi")
        conv.save(out)
        assert os.path.isfile(out)
        # NSIS requires UTF-8 with BOM for Unicode handling — check BOM bytes
        with open(out, "rb") as fh:
            assert fh.read(3) == b'\xef\xbb\xbf'
        content = open(out, encoding="utf-8").read()
        assert "IntegApp" in content


class TestFullIntegration:
    def test_full_features(self, full_yaml, tmp_path):
        cfg = PackageConfig.from_yaml(full_yaml)
        conv = YamlToNsisConverter(cfg, cfg._raw_dict)
        nsi = conv.convert()

        # Header
        assert "Unicode true" in nsi
        assert '!define APP_NAME "FullApp"' in nsi

        # License
        assert "MUI_PAGE_LICENSE" in nsi

        # Registry
        assert 'WriteRegStr HKLM "Software\\FullApp" "InstallPath"' in nsi
        assert "SetRegView 64" in nsi

        # Env vars
        assert '"FULLAPP_HOME"' in nsi
        assert "Function _StrContains" in nsi  # PATH append helper
        assert "Function un._RemovePathEntry" in nsi

        # File associations
        assert 'WriteRegStr HKCR ".fa"' in nsi
        assert "FullApp.File" in nsi
        assert "DefaultIcon" in nsi

        # System requirements
        assert "Requires Windows 10.0" in nsi
        assert "200 MB" in nsi
        assert "UserInfo::GetAccountType" in nsi

        # Finish page
        assert "MUI_FINISHPAGE_RUN" in nsi
        assert "Launch FullApp" in nsi

        # Packages
        assert 'Section "App"' in nsi
        assert 'SectionGroup "Drivers"' in nsi
        assert 'Section "PXI"' in nsi
        assert 'ExecWait "$INSTDIR\\pxi\\setup.cmd"' in nsi

        # Signing
        assert "!finalize" in nsi

        # Update
        assert "UPDATE_URL" in nsi
        assert "DOWNLOAD_URL" in nsi

        # Logging
        assert "LogSet on" in nsi
        # Logging should be enabled inside .onInit (in addition to uninstall logging)
        start = nsi.index('Function .onInit')
        end = nsi.index('FunctionEnd', start)
        assert 'LogSet on' in nsi[start:end]
        # Ensure we include compile-time guard for LogSet
        assert '!ifdef NSIS_CONFIG_LOG' in nsi

        # Uninstall
        assert 'Section "Uninstall"' in nsi
        assert 'DeleteRegValue HKLM "Software\\FullApp" "InstallPath"' in nsi
        assert 'DeleteRegKey HKCR ".fa"' in nsi


class TestVariableResolution:
    def test_config_references(self, tmp_path):
        p = tmp_path / "vars.yaml"
        p.write_text(
            textwrap.dedent("""\
                app:
                  name: VarApp
                  version: "1.0"
                install:
                  install_dir: "$PROGRAMFILES64\\\\${app.name}"
                files:
                  - source: "app.exe"
                variables:
                  DATA_DIR: "$APPDATA\\\\${app.name}"
            """),
            encoding="utf-8",
        )
        cfg = PackageConfig.from_yaml(str(p))
        conv = YamlToNsisConverter(cfg, cfg._raw_dict)
        nsi = conv.convert()
        # ${app.name} should be resolved to VarApp where the converter resolves it
        assert "VarApp" in nsi
