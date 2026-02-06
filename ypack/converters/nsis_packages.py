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
    """Emit ``.onInit`` — signature verification, system-requirements checks, section flags."""
    cfg = ctx.config
    lines: List[str] = [
        "; ===========================================================================",
        "; Initialization",
        "; ===========================================================================",
        "Function .onInit",
        "",
    ]

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
    # with NSIS_CONFIG_LOG.  Our LogInit/LogWrite/LogClose macros provide
    # a file-based fallback that always works, so LogSet is optional.
    if cfg.logging and cfg.logging.enabled:
        lines.extend([
            '!ifdef NSIS_CONFIG_LOG',
            '  LogSet on',
            '!endif',
            "",
        ])

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
