"""
NSIS component / package section generation.

Handles SectionGroup nesting, optional/default flags, post_install
commands, and the .onInit section-flag setup.
"""

from __future__ import annotations

import os
from typing import List

from .context import BuildContext
from .nsis_sections import _normalize_path, _should_use_recursive, _flatten_packages


def generate_package_sections(ctx: BuildContext) -> List[str]:
    """Emit ``Section`` / ``SectionGroup`` blocks for every package."""
    if not ctx.config.packages:
        return []

    has_logging = ctx.config.logging and ctx.config.logging.enabled
    lines: List[str] = [
        "; ===========================================================================",
        "; Package / Component Sections",
        "; ===========================================================================",
        "",
    ]

    idx_ref = [0]  # mutable counter shared across recursion

    def _emit(pkg_list: list) -> None:
        for pkg in pkg_list:
            if pkg.children:
                lines.append(f'SectionGroup "{pkg.name}"')
                _emit(pkg.children)
                lines.append("SectionGroupEnd")
                lines.append("")
            else:
                sec_name = f"SEC_PKG_{idx_ref[0]}"
                idx_ref[0] += 1
                lines.append(f'Section "{pkg.name}" {sec_name}')

                if has_logging:
                    lines.append(f'  !insertmacro LogWrite "Installing component: {pkg.name}"')

                for src_entry in pkg.sources:
                    src_val = src_entry.get("source", "")
                    dest = src_entry.get("destination", "$INSTDIR")
                    lines.append(f'  SetOutPath "{dest}"')

                    if isinstance(src_val, list):
                        for s in src_val:
                            lines.append(_file_line(ctx, s))
                    else:
                        lines.append(_file_line(ctx, src_val))

                if pkg.post_install:
                    lines.append("")
                    lines.append("  ; Post-install commands")
                    for cmd in pkg.post_install:
                        if has_logging:
                            lines.append(f'  !insertmacro LogWrite "Running: {cmd}"')
                        lines.append(f'  ExecWait "{cmd}"')

                if has_logging:
                    lines.append(f'  !insertmacro LogWrite "Component {pkg.name} done."')
                lines.append("SectionEnd")
                lines.append("")

    _emit(ctx.config.packages)
    return lines


def generate_signing_section(ctx: BuildContext) -> List[str]:
    """Emit ``!finalize`` code-signing directive."""
    signing = ctx.config.signing
    if not signing or not signing.enabled:
        return []
    return [
        "; --- Code Signing ---",
        f"; Certificate: {signing.certificate}",
        f"; Timestamp:   {signing.timestamp_url}",
        f"; Verify after build: {signing.verify_signature}",
        f"; Checksum: {signing.checksum_type} {signing.checksum_value}",
        f'!finalize \'signtool sign /f "{signing.certificate}" /p "{signing.password}" /t "{signing.timestamp_url}" "%1"\'',
        "",
    ]


def generate_update_section(ctx: BuildContext) -> List[str]:
    """Emit update-metadata registry writes."""
    upd = ctx.config.update
    if not upd or not upd.enabled:
        return []
    return [
        "; --- Auto-Update Configuration ---",
        f'!define UPDATE_URL "{upd.update_url}"',
        f'!define DOWNLOAD_URL "{upd.download_url}"',
        f'!define CHECK_ON_STARTUP "{str(upd.check_on_startup).lower()}"',
        f'!define BACKUP_ON_UPGRADE "{str(upd.backup_on_upgrade).lower()}"',
        f'!define REPAIR_ENABLED "{str(upd.repair_enabled).lower()}"',
        "",
        'Section "Update Configuration"',
        f'  WriteRegStr {upd.registry_hive} "{upd.registry_key}" "UpdateURL" "${{UPDATE_URL}}"',
        f'  WriteRegStr {upd.registry_hive} "{upd.registry_key}" "DownloadURL" "${{DOWNLOAD_URL}}"',
        f'  WriteRegStr {upd.registry_hive} "{upd.registry_key}" "CheckOnStartup" "${{CHECK_ON_STARTUP}}"',
        f'  WriteRegStr {upd.registry_hive} "{upd.registry_key}" "BackupOnUpgrade" "${{BACKUP_ON_UPGRADE}}"',
        f'  WriteRegStr {upd.registry_hive} "{upd.registry_key}" "RepairEnabled" "${{REPAIR_ENABLED}}"',
        "SectionEnd",
        "",
    ]


def generate_oninit(ctx: BuildContext) -> List[str]:
    """Emit ``.onInit`` — mutex, signature, sysreq, existing-install, section flags."""
    cfg = ctx.config
    lines: List[str] = [
        "; ===========================================================================",
        "; Initialization",
        "; ===========================================================================",
        "Function .onInit",
        "",
    ]

    # ------------------------------------------------------------------
    # Installer Mutex — prevent running two installers at the same time
    # ------------------------------------------------------------------
    lines.extend([
        '  ; Prevent multiple installer instances',
        '  System::Call \'kernel32::CreateMutex(p 0, i 0, t "${APP_NAME}_InstallerMutex") p .r1 ?e\'',
        '  Pop $R0',
        '  StrCmp $R0 "0" +3 0',
        '  MessageBox MB_OK|MB_ICONEXCLAMATION "The installer is already running."',
        '  Abort',
        '',
    ])

    # Signature verification
    if cfg.signing and cfg.signing.verify_signature:
        lines.extend([
            "  ; Verify installer digital signature",
            '  nsExec::ExecToStack \'powershell -NoProfile -Command "& { $s = Get-AuthenticodeSignature -LiteralPath $env:__COMPAT_LAYER; if ($s.Status -ne [System.Management.Automation.SignatureStatus]::Valid) { exit 1 } }"\'',
            "  Pop $0",
            '  StrCmp $0 "0" _sig_ok',
            '  MessageBox MB_OK|MB_ICONSTOP "Signature verification failed. Installation aborted."',
            "  Abort",
            "_sig_ok:",
            "",
        ])

    # System requirements
    sysreq = cfg.install.system_requirements
    if sysreq:
        if sysreq.min_windows_version:
            mv = sysreq.min_windows_version
            lines.extend([
                f"  ; Check minimum Windows version: {mv}",
                f'  nsExec::ExecToStack \'powershell -NoProfile -Command "& {{ $v = (Get-CimInstance Win32_OperatingSystem).Version; if ([Version]$v -lt [Version]\'{mv}\') {{ exit 1 }} }}"\'',
                "  Pop $0",
                '  StrCmp $0 "0" +3 0',
                f'  MessageBox MB_OK|MB_ICONSTOP "Requires Windows {mv} or higher."',
                "  Abort",
                "",
            ])
        if sysreq.min_free_space_mb:
            mb = sysreq.min_free_space_mb
            lines.extend([
                f"  ; Check free disk space >= {mb} MB",
                f'  nsExec::ExecToStack \'powershell -NoProfile -Command "& {{ $d = (Get-PSDrive ($env:SystemDrive[0])); if ($d.Free / 1MB -lt {mb}) {{ exit 1 }} }}"\'',
                "  Pop $0",
                '  StrCmp $0 "0" +3 0',
                f'  MessageBox MB_OK|MB_ICONSTOP "Not enough free disk space. Require at least {mb} MB."',
                "  Abort",
                "",
            ])
        if sysreq.min_ram_mb:
            mb = sysreq.min_ram_mb
            lines.extend([
                f"  ; Check physical memory >= {mb} MB",
                f'  nsExec::ExecToStack \'powershell -NoProfile -Command "& {{ $m = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1MB; if ($m -lt {mb}) {{ exit 1 }} }}"\'',
                "  Pop $0",
                '  StrCmp $0 "0" +3 0',
                f'  MessageBox MB_OK|MB_ICONSTOP "Not enough physical memory. Require at least {mb} MB."',
                "  Abort",
                "",
            ])
        if sysreq.require_admin:
            lines.extend([
                "  ; Ensure running as administrator (UAC check)",
                "  UserInfo::GetAccountType",
                "  Pop $0",
                '  StrCmp $0 "Admin" +3 0',
                '  MessageBox MB_OK|MB_ICONSTOP "This installer requires administrator privileges."',
                "  Abort",
                "",
            ])

    # Installer logging — LogSet is only available when NSIS was compiled
    # with NSIS_CONFIG_LOG.
    if cfg.logging and cfg.logging.enabled:
        lines.extend([
            '!ifdef NSIS_CONFIG_LOG',
            '  LogSet on',
            '!endif',
        ])

    # ------------------------------------------------------------------
    # Existing-install detection and behavior
    # ------------------------------------------------------------------
    lines.extend(_generate_existing_install_check(ctx))

    # Section flags for packages
    flat = _flatten_packages(cfg.packages)
    for idx, pkg in enumerate(flat):
        sec = f"SEC_PKG_{idx}"
        if pkg.optional and not pkg.default:
            lines.append(f"  SectionSetFlags ${{{sec}}} 0")
        elif not pkg.optional:
            lines.append(f"  SectionSetFlags ${{{sec}}} ${{SF_SELECTED}}")

    lines.extend([
        "FunctionEnd",
        "",
    ])
    return lines


def _generate_existing_install_check(ctx: BuildContext) -> List[str]:
    """Generate NSIS code for existing-install detection and handling.

    Uses ``ExistingInstallConfig`` to drive the behavior.  Supports:
    * version comparison (skip detection when same version is installed)
    * allow_multiple (only detect if same $INSTDIR)
    * configurable uninstaller args
    * proper _wait_uninstall loop
    * show_version_info in prompt
    """
    ei = ctx.config.install.existing_install
    if not ei or ei.mode == "none":
        return []

    cfg = ctx.config
    has_logging = bool(cfg.logging and cfg.logging.enabled)

    # When allow_multiple is True we intentionally DO NOT perform a
    # directory-specific existence check in .onInit (because $INSTDIR is
    # still the default path). Instead we defer the check until the user
    # has chosen an installation directory (directory page leave callback).
    if ei.allow_multiple:
        lines: List[str] = [
            "",
            "  ; ------------------------------------------------------------------",
            "  ; Existing-install detection (deferred to directory page because allow_multiple=true)",
            "  ; ------------------------------------------------------------------",
            "  ; NOTE: Actual path collision detection will run in Function ExistingInstall_DirLeave",
        ]
        return lines

    lines: List[str] = [
        "",
        "  ; ------------------------------------------------------------------",
        "  ; Existing-install detection",
        "  ; ------------------------------------------------------------------",
        f'  SetRegView {ctx.effective_reg_view}',
        '  ReadRegStr $R0 HKLM "${REG_KEY}" "InstallPath"',
        '  StrCmp $R0 "" _ei_done  ; No previous install registered',
    ]

    # Version check: read installed version into $R2
    if ei.version_check or ei.show_version_info:
        lines.extend([
            '  ReadRegStr $R2 HKLM "${REG_KEY}" "Version"',
        ])

    # Version check: skip detection when installed version matches
    if ei.version_check:
        lines.extend([
            '  ; Skip if same version is already installed',
            '  StrCmp $R2 "${APP_VERSION}" _ei_done',
        ])

    # allow_multiple: only treat as conflict if same directory
    if ei.allow_multiple:
        lines.extend([
            '  ; allow_multiple: only conflict when installing to the same directory',
            '  StrCmp $R0 "$INSTDIR" 0 _ei_done',
        ])

    # $R1 = install path for messages / uninstaller call
    lines.extend([
        '  StrCpy $R1 $R0',
    ])

    # Check for uninstaller
    lines.extend([
        '  IfFileExists "$R1\\Uninstall.exe" _ei_has_uninst _ei_overwrite_only',
    ])

    # --- _ei_has_uninst ---
    lines.append('_ei_has_uninst:')

    if ei.mode == "prompt_uninstall":
        if ei.show_version_info:
            lines.extend([
                '  StrCmp $R2 "" _ei_prompt_no_ver 0',
                '  MessageBox MB_YESNO|MB_ICONQUESTION "An existing installation (version $R2) was found at:$\\r$\\n$R1$\\r$\\n$\\r$\\nUninstall it first and continue?" IDYES _ei_do_uninstall IDNO _ei_cancel',
                '  Goto _ei_prompt_done',
                '_ei_prompt_no_ver:',
                '  MessageBox MB_YESNO|MB_ICONQUESTION "An existing installation was found at:$\\r$\\n$R1$\\r$\\n$\\r$\\nUninstall it first and continue?" IDYES _ei_do_uninstall IDNO _ei_cancel',
                '_ei_prompt_done:',
            ])
        else:
            lines.extend([
                '  MessageBox MB_YESNO|MB_ICONQUESTION "An existing installation was found at:$\\r$\\n$R1$\\r$\\n$\\r$\\nUninstall it first and continue?" IDYES _ei_do_uninstall IDNO _ei_cancel',
            ])
    elif ei.mode == "auto_uninstall":
        lines.append('  Goto _ei_do_uninstall')
    elif ei.mode == "abort":
        if ei.show_version_info:
            lines.extend([
                '  StrCmp $R2 "" _ei_abort_no_ver 0',
                '  MessageBox MB_OK|MB_ICONSTOP "An existing installation (version $R2) was found at $R1. Installation aborted."',
                '  Goto _ei_cancel',
                '_ei_abort_no_ver:',
                '  MessageBox MB_OK|MB_ICONSTOP "An existing installation was found at $R1. Installation aborted."',
                '  Goto _ei_cancel',
            ])
        else:
            lines.extend([
                '  MessageBox MB_OK|MB_ICONSTOP "An existing installation was found at $R1. Installation aborted."',
                '  Goto _ei_cancel',
            ])
    elif ei.mode == "overwrite":
        lines.append('  Goto _ei_done  ; Overwrite mode: skip uninstall')

    # --- _ei_do_uninstall ---
    uninst_args = ei.uninstaller_args or "/S"
    wait_ms = ei.uninstall_wait_ms

    # If wait_ms < 0, perform an infinite wait (no timeout). Otherwise use a timed loop.
    if wait_ms is not None and int(wait_ms) < 0:
        lines.extend([
            '_ei_do_uninstall:',
        ])
        if has_logging:
            lines.append(f'  !insertmacro LogWrite "Running existing uninstaller: $R1\\Uninstall.exe {uninst_args}"')
            lines.append('  !insertmacro LogWrite "Waiting for uninstaller to finish (no timeout)"')
        lines.extend([
            f'  ExecWait \'$R1\\Uninstall.exe {uninst_args}\'',
            "  ; Wait for uninstaller to finish (no timeout)",
            "_ei_wait_loop:",
            "  Sleep 500",
            '  IfFileExists "$R1\\Uninstall.exe" _ei_wait_loop _ei_wait_done',
            "_ei_wait_done:",
        ])
        if has_logging:
            lines.append('  !insertmacro LogWrite "Uninstaller finished."')
        lines.extend([
            "  ; Verify uninstaller is gone",
            '  IfFileExists "$R1\\Uninstall.exe" 0 _ei_done',
            '  MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "The previous uninstaller did not finish.  Retry or cancel installation?" IDRETRY _ei_do_uninstall',
            '  ; Fall through to cancel',
        ])
    else:
        # Timed wait loop (default behaviour)
        lines.extend([
            '_ei_do_uninstall:',
        ])
        if has_logging:
            lines.append(f'  !insertmacro LogWrite "Running existing uninstaller: $R1\\Uninstall.exe {uninst_args}"')
            lines.append(f'  !insertmacro LogWrite "Waiting for uninstaller to finish (up to {wait_ms}ms)"')
        lines.extend([
            f'  ExecWait \'$R1\\Uninstall.exe {uninst_args}\'',
            f'  ; Wait for uninstaller to finish (up to {wait_ms}ms)',
            '  StrCpy $R3 0',
            "_ei_wait_loop:",
            f'  ; Loop: if $R3 >= {wait_ms} goto _ei_wait_done, else continue waiting',
            f'  IntCmp $R3 {wait_ms} _ei_wait_done _ei_wait_done _ei_wait_continue',
            '_ei_wait_continue:',
            '  Sleep 500',
            '  IntOp $R3 $R3 + 500',
            '  IfFileExists "$R1\\Uninstall.exe" _ei_wait_loop _ei_wait_done',
            '_ei_wait_done:',
        ])
        if has_logging:
            lines.append('  !insertmacro LogWrite "Uninstaller finished."')
        lines.extend([
            '  ; Verify uninstaller is gone',
            '  IfFileExists "$R1\\Uninstall.exe" 0 _ei_done',
            '  !insertmacro LogWrite "Uninstaller did not finish within timeout."',
            '  MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "The previous uninstaller did not finish.  Retry or cancel installation?" IDRETRY _ei_do_uninstall',
            '  ; Fall through to cancel',
        ])

    # --- _ei_cancel ---
    lines.extend([
        '_ei_cancel:',
        '  Abort',
    ])

    # --- _ei_overwrite_only ---
    lines.extend([
        '_ei_overwrite_only:',
        '  ; No uninstaller found \u2014 files will be overwritten',
    ])

    lines.append('_ei_done:')
    lines.append(f'  SetRegView lastused')
    lines.append('')
    return lines


def generate_existing_install_helpers(ctx: BuildContext) -> List[str]:
    """Emit helper functions for existing-install handling.

    When ``allow_multiple`` is true we generate a directory-page leave
    callback function that checks the *selected* $INSTDIR for an existing
    installation and performs the same prompting/uninstall logic used in
    the .onInit flow.
    """
    ei = ctx.config.install.existing_install
    if not ei or ei.mode == "none" or not ei.allow_multiple:
        return []

    cfg = ctx.config
    has_logging = bool(cfg.logging and cfg.logging.enabled)

    lines: List[str] = [
        "",
        "  ; ------------------------------------------------------------------",
        "  ; Existing-install helpers (directory page leave callback)",
        "  ; ------------------------------------------------------------------",
        "Function ExistingInstall_DirLeave",
        "",
        f'  SetRegView {ctx.effective_reg_view}',
        "  ; Check the user-selected directory ($INSTDIR) for an uninstaller",
        '  StrCpy $R1 $INSTDIR',
        '  IfFileExists "$R1\\Uninstall.exe" _eid_has_uninst _eid_check_reg',
        '  Goto _eid_done',
        '',
        '_eid_check_reg:',
        '  ; Also consider the registered install path as a match',
        '  ReadRegStr $R0 HKLM "${REG_KEY}" "InstallPath"',
        '  StrCmp $R0 "$R1" 0 _eid_done',
        '',
        '_eid_has_uninst:',
    ]

    # Optionally read installed version for prompts / version check
    if ei.version_check or ei.show_version_info:
        lines.append('  ReadRegStr $R2 HKLM "${REG_KEY}" "Version"')

    # Prompt / behavior
    if ei.mode == "prompt_uninstall":
        if ei.show_version_info:
            lines.extend([
                '  StrCmp $R2 "" _eid_prompt_no_ver 0',
                '  MessageBox MB_YESNO|MB_ICONQUESTION "An existing installation (version $R2) was found at:$\\r$\\n$R1$\\r$\\n\\r$\\nUninstall it first and continue?" IDYES _eid_do_uninstall IDNO _eid_cancel',
                '  Goto _eid_prompt_done',
                '_eid_prompt_no_ver:',
                '  MessageBox MB_YESNO|MB_ICONQUESTION "An existing installation was found at:$\\r$\\n$R1$\\r$\\n\\r$\\nUninstall it first and continue?" IDYES _eid_do_uninstall IDNO _eid_cancel',
                '_eid_prompt_done:',
            ])
        else:
            lines.append('  MessageBox MB_YESNO|MB_ICONQUESTION "An existing installation was found at:$\\r$\\n$R1$\\r$\\n\\r$\\nUninstall it first and continue?" IDYES _eid_do_uninstall IDNO _eid_cancel')
    elif ei.mode == "auto_uninstall":
        lines.append('  Goto _eid_do_uninstall')
    elif ei.mode == "abort":
        if ei.show_version_info:
            lines.extend([
                '  StrCmp $R2 "" _eid_abort_no_ver 0',
                '  MessageBox MB_OK|MB_ICONSTOP "An existing installation (version $R2) was found at $R1. Installation aborted."',
                '  Goto _eid_cancel',
                '_eid_abort_no_ver:',
                '  MessageBox MB_OK|MB_ICONSTOP "An existing installation was found at $R1. Installation aborted."',
                '  Goto _eid_cancel',
            ])
        else:
            lines.extend([
                '  MessageBox MB_OK|MB_ICONSTOP "An existing installation was found at $R1. Installation aborted."',
                '  Goto _eid_cancel',
            ])
    elif ei.mode == "overwrite":
        lines.append('  Goto _eid_done  ; Overwrite mode: skip uninstall')

    # Uninstall execution and wait loop
    uninst_args = ei.uninstaller_args or "/S"
    wait_ms = ei.uninstall_wait_ms

    if wait_ms is not None and int(wait_ms) < 0:
        lines.extend([
            '_eid_do_uninstall:',
        ])
        if has_logging:
            lines.append(f'  !insertmacro LogWrite "Running existing uninstaller: $R1\\Uninstall.exe {uninst_args}"')
            lines.append('  !insertmacro LogWrite "Waiting for uninstaller to finish (no timeout)"')
        lines.extend([
            f'  ExecWait \'$R1\\Uninstall.exe {uninst_args}\'',
            '  ; Wait for uninstaller to finish (no timeout)',
            '_eid_wait_loop:',
            '  Sleep 500',
            '  IfFileExists "$R1\\Uninstall.exe" _eid_wait_loop _eid_wait_done',
            '_eid_wait_done:',
        ])
        if has_logging:
            lines.append('  !insertmacro LogWrite "Uninstaller finished."')
        lines.extend([
            '  ; Verify uninstaller is gone',
            '  IfFileExists "$R1\\Uninstall.exe" 0 _eid_done',
            '  MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "The previous uninstaller did not finish.  Retry or cancel installation?" IDRETRY _eid_do_uninstall IDCANCEL _eid_cancel',
        ])
    else:
        lines.extend([
            '_eid_do_uninstall:',
        ])
        if has_logging:
            lines.append(f'  !insertmacro LogWrite "Running existing uninstaller: $R1\\Uninstall.exe {uninst_args}"')
            lines.append(f'  !insertmacro LogWrite "Waiting for uninstaller to finish (up to {wait_ms}ms)"')
        lines.extend([
            f'  ExecWait \'$R1\\Uninstall.exe {uninst_args}\'',
            f'  ; Wait for uninstaller to finish (up to {wait_ms}ms)',
            '  StrCpy $R3 0',
            "_eid_wait_loop:",
            f'  ; Loop: if $R3 >= {wait_ms} goto _eid_wait_done, else continue waiting',
            f'  IntCmp $R3 {wait_ms} _eid_wait_done _eid_wait_done _eid_wait_continue',
            '_eid_wait_continue:',
            '  Sleep 500',
            '  IntOp $R3 $R3 + 500',
            '  IfFileExists "$R1\\Uninstall.exe" _eid_wait_loop _eid_wait_done',
            '_eid_wait_done:',
        ])
        if has_logging:
            lines.append('  !insertmacro LogWrite "Uninstaller finished."')
        lines.extend([
            '  ; Verify uninstaller is gone',
            '  IfFileExists "$R1\\Uninstall.exe" 0 _eid_done',
            '  !insertmacro LogWrite "Uninstaller did not finish within timeout."',
            '  MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "The previous uninstaller did not finish.  Retry or cancel installation?" IDRETRY _eid_do_uninstall IDCANCEL _eid_cancel',
        ])

    lines.extend([
        '',
        '_eid_cancel:',
        '  Abort',
        '',
        '_eid_done:',
        '  SetRegView lastused',
        '',
        'FunctionEnd',
        '',
    ])

    return lines


def generate_uninit(ctx: BuildContext) -> List[str]:
    """Emit ``un.onInit`` \u2014 uninstaller mutex and confirmation."""
    cfg = ctx.config
    lines: List[str] = [
        "; ===========================================================================",
        "; Uninstaller Initialization",
        "; ===========================================================================",
        "Function un.onInit",
        "",
        '  ; Prevent multiple uninstaller instances',
        '  System::Call \'kernel32::CreateMutex(p 0, i 0, t "${APP_NAME}_UninstallerMutex") p .r1 ?e\'',
        '  Pop $R0',
        '  StrCmp $R0 "0" +3 0',
        '  MessageBox MB_OK|MB_ICONEXCLAMATION "The uninstaller is already running."',
        '  Abort',
        '',
    ]

    # Logging
    if cfg.logging and cfg.logging.enabled:
        lines.extend([
            '!ifdef NSIS_CONFIG_LOG',
            '  LogSet on',
            '!endif',
        ])

    lines.extend([
        "FunctionEnd",
        "",
    ])
    return lines


# -----------------------------------------------------------------------
# Internal
# -----------------------------------------------------------------------

def _file_line(ctx: BuildContext, source: str) -> str:
    """Build a single ``File`` directive, choosing /r when appropriate."""
    resolved = ctx.resolve_path(source)
    if os.path.exists(resolved):
        path_for_nsi = resolved
    else:
        path_for_nsi = _normalize_path(source)
    if _should_use_recursive(source):
        return f'  File /r "{path_for_nsi}"'
    return f'  File "{path_for_nsi}"'
