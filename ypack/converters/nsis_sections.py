"""
NSIS Install / Uninstall section generation.

Fixes over the original implementation:
- Correct ``SetOutPath`` before every ``File`` directive.
- Proper uninstall manifest (tracks what was installed).
- inetc plugin include for remote downloads.
- Correct helper function calls for PATH append/remove.
"""

from __future__ import annotations

import os
import re
from typing import List, Set, Optional

from .context import BuildContext


# -----------------------------------------------------------------------
# Path utilities
# -----------------------------------------------------------------------

def _normalize_path(path: str) -> str:
    """Convert glob-style paths to NSIS-compatible Windows paths."""
    path = path.replace("/**/", "\\")
    path = path.replace("**/", "")
    path = path.replace("/", "\\")
    return path


def _should_use_recursive(source: str) -> bool:
    return bool(source) and "**" in source


# -----------------------------------------------------------------------
# Installer Section
# -----------------------------------------------------------------------

def generate_installer_section(ctx: BuildContext) -> List[str]:
    """Emit the main ``Section "Install"``."""
    cfg = ctx.config
    has_logging = cfg.logging and cfg.logging.enabled
    lines: List[str] = [
        "; ===========================================================================",
        '; Installer Section',
        "; ===========================================================================",
        'Section "Install"',
        "",
    ]

    # --- Logging: begin ---
    if has_logging:
        lines.append('  !insertmacro LogInit "Install"')
        lines.append('  !insertmacro LogWrite "Install directory: $INSTDIR"')
        lines.append("")

    # Track whether we need the inetc plugin
    has_remote = any(fe.is_remote for fe in cfg.files)
    if has_remote:
        lines.insert(0, '!include "inetc.nsh"')
        lines.insert(0, "; Plugin: inetc for HTTP downloads")

    # --- Files ---
    if has_logging:
        lines.append('  !insertmacro LogWrite "Copying files ..."')
    current_outpath: Optional[str] = None
    for fe in cfg.files:
        dest = fe.destination or "$INSTDIR"

        if fe.is_remote:
            # Remote download
            url = fe.source
            filename = url.rsplit("/", 1)[-1] or "download"
            if dest != current_outpath:
                lines.append(f'  SetOutPath "{dest}"')
                current_outpath = dest
            lines.append(f"  ; Download: {url}")
            lines.append(f'  inetc::get /SILENT "{url}" "$OUTDIR\\{filename}" /END')
            lines.append("  Pop $0")
            lines.append('  StrCmp $0 "OK" +3 0')
            lines.append('  MessageBox MB_OK|MB_ICONSTOP "Download failed: $0"')
            lines.append("  Abort")
            if fe.checksum_type:
                lines.append(f"  ; Verify checksum: {fe.checksum_type} {fe.checksum_value}")
                lines.append(f'  Push "$OUTDIR\\{filename}"')
                lines.append(f'  Push "{fe.checksum_type}"')
                lines.append(f'  Push "{fe.checksum_value}"')
                lines.append("  Call VerifyChecksum")
                lines.append("  Pop $0")
                lines.append('  StrCmp $0 "0" +3 0')
                lines.append('  MessageBox MB_OK|MB_ICONSTOP "Checksum verification failed"')
                lines.append("  Abort")
            if fe.decompress:
                lines.append(f'  Push "$OUTDIR\\{filename}"')
                lines.append(f'  Push "{dest}"')
                lines.append("  Call ExtractArchive")
        else:
            # Local file / directory
            if dest != current_outpath:
                lines.append(f'  SetOutPath "{dest}"')
                current_outpath = dest
            norm = _normalize_path(fe.source)
            if _should_use_recursive(fe.source) or fe.recursive:
                lines.append(f'  File /r "{norm}"')
            else:
                lines.append(f'  File "{norm}"')

    lines.append("")

    # --- Uninstaller ---
    lines.extend([
        "  ; Write uninstaller",
        "  SetOutPath $INSTDIR",
        '  WriteUninstaller "$INSTDIR\\Uninstall.exe"',
        "",
    ])
    if has_logging:
        lines.append('  !insertmacro LogWrite "Uninstaller created."')
        lines.append("")

    # --- Standard registry (Add/Remove Programs) ---
    reg_view = ctx.effective_reg_view
    lines.extend([
        f"  ; Application registry entries (using {reg_view}-bit registry view)",
        f'  SetRegView {reg_view}',
        '  WriteRegStr HKLM "${REG_KEY}" "InstallPath" "$INSTDIR"',
        '  WriteRegStr HKLM "${REG_KEY}" "Version" "${APP_VERSION}"',
        '',
        '  ; Add/Remove Programs (ARP) registry entries',
        '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayName" "${APP_NAME}"',
        '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"',
        '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"',
        '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "UninstallString" "$\\\"$INSTDIR\\Uninstall.exe$\\\""',
        '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "QuietUninstallString" "$\\\"$INSTDIR\\Uninstall.exe$\\\" /S"',
        '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "InstallLocation" "$INSTDIR"',
        '  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "NoModify" 1',
        '  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "NoRepair" 1',
    ])
    # DisplayIcon — use install icon if available, else the main exe
    if cfg.app.install_icon:
        lines.append('  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayIcon" "$INSTDIR\\${MUI_ICON}"')
    else:
        lines.append('  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayIcon" "$INSTDIR\\Uninstall.exe,0"')
    lines.append('  SetRegView lastused')
    lines.append('')

    if has_logging:
        lines.append('  !insertmacro LogWrite "Registry entries written."')
        lines.append("")

    # --- Custom registry entries ---
    _emit_registry_writes(ctx, lines)

    # --- Environment variables ---
    _emit_env_var_writes(ctx, lines)

    # --- Shortcuts ---
    _emit_shortcuts(ctx, lines)
    if has_logging and (cfg.install.desktop_shortcut_target or cfg.install.start_menu_shortcut_target):
        lines.append('  !insertmacro LogWrite "Shortcuts created."')
        lines.append("")

    # --- File associations ---
    _emit_file_associations(ctx, lines)

    # Estimated install size
    lines.append("  ; Calculate installed size")
    lines.append('  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2')
    lines.append('  IntFmt $0 "0x%08X" $0')
    lines.append(f'  SetRegView {reg_view}')
    lines.append('  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "EstimatedSize" $0')
    lines.append('  SetRegView lastused')
    lines.append("")

    # --- Logging: end ---
    if has_logging:
        lines.append('  !insertmacro LogWrite "Installation completed successfully."')
        lines.append('  !insertmacro LogClose')
        lines.append("")

    lines.append("SectionEnd")
    lines.append("")
    return lines


# -----------------------------------------------------------------------
# Uninstaller Section
# -----------------------------------------------------------------------

def generate_uninstaller_section(ctx: BuildContext) -> List[str]:
    """Emit ``Section "Uninstall"``."""
    cfg = ctx.config
    has_logging = cfg.logging and cfg.logging.enabled
    lines: List[str] = [
        "; ===========================================================================",
        "; Uninstaller Section",
        "; ===========================================================================",
        'Section "Uninstall"',
        "",
    ]

    # --- Logging: begin ---
    if has_logging:
        lines.append('  !insertmacro LogInit "Uninstall"')
        lines.append("")

    # Remove files (reverse order)
    if has_logging:
        lines.append('  !insertmacro LogWrite "Removing installed files ..."')
    lines.append("  ; Remove installed files")
    for fe in reversed(cfg.files):
        dest = fe.destination or "$INSTDIR"
        if fe.is_remote:
            filename = fe.source.rsplit("/", 1)[-1] or "download"
            lines.append(f'  Delete "{dest}\\{filename}"')
        elif _should_use_recursive(fe.source) or fe.recursive:
            dirname = os.path.basename(_normalize_path(fe.source).rstrip("\\*"))
            if dirname and dirname != "*":
                lines.append(f'  RMDir /r "{dest}\\{dirname}"')
            else:
                lines.append(f'  RMDir /r "{dest}"')
        else:
            filename = os.path.basename(_normalize_path(fe.source))
            lines.append(f'  Delete "{dest}\\{filename}"')

    # Remove packages files
    if cfg.packages:
        lines.append("")
        lines.append("  ; Remove package files")
        for pkg in _flatten_packages(cfg.packages):
            for src_entry in pkg.sources:
                dest = src_entry.get("destination", "$INSTDIR")
                lines.append(f'  RMDir /r "{dest}"')

    lines.extend([
        "",
        "  ; Remove uninstaller",
        '  Delete "$INSTDIR\\Uninstall.exe"',
        "",
        "  ; Remove install directory (only if empty)",
        '  RMDir "$INSTDIR"',
        "",
    ])

    # Remove shortcuts
    if cfg.install.desktop_shortcut_target:
        lines.append("  ; Remove desktop shortcut")
        lines.append('  Delete "$DESKTOP\\${APP_NAME}.lnk"')
        lines.append("")

    if cfg.install.start_menu_shortcut_target:
        lines.append("  ; Remove start menu shortcuts")
        lines.append('  Delete "$SMPROGRAMS\\${APP_NAME}\\${APP_NAME}.lnk"')
        lines.append('  Delete "$SMPROGRAMS\\${APP_NAME}\\Uninstall.lnk"')
        lines.append('  RMDir "$SMPROGRAMS\\${APP_NAME}"')
        lines.append("")

    if has_logging and (cfg.install.desktop_shortcut_target or cfg.install.start_menu_shortcut_target):
        lines.append('  !insertmacro LogWrite "Shortcuts removed."')
        lines.append("")

    # Remove standard registry keys
    if has_logging:
        lines.append('  !insertmacro LogWrite "Removing registry entries ..."')
    reg_view = ctx.effective_reg_view
    lines.extend([
        "  ; Remove registry entries",
        f'  SetRegView {reg_view}',
        '  DeleteRegKey HKLM "${REG_KEY}"',
        '  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}"',
        '  SetRegView lastused',
        "",
    ])

    # Remove custom registry values
    if cfg.install.registry_entries:
        lines.append("  ; Remove custom registry entries")
        current_view: Optional[str] = None
        # Track which keys we've deleted values from, so we can clean empty keys
        keys_to_clean: List[tuple] = []  # (hive, key)
        for entry in cfg.install.registry_entries:
            key = ctx.resolve(entry.key)
            target_view = entry.view if entry.view in ("32", "64") else None
            if target_view != current_view:
                if current_view is not None:
                    lines.append("  SetRegView lastused")
                if target_view is not None:
                    lines.append(f"  SetRegView {target_view}")
                current_view = target_view
            lines.append(f'  DeleteRegValue {entry.hive} "{key}" "{entry.name}"')
            if (entry.hive, key) not in keys_to_clean:
                keys_to_clean.append((entry.hive, key))
        if current_view is not None:
            lines.append("  SetRegView lastused")
        # Clean up empty registry keys left behind
        if keys_to_clean:
            lines.append("  ; Remove empty registry keys (only if no remaining values)")
            for hive, key in keys_to_clean:
                lines.append(f'  DeleteRegKey /ifempty {hive} "{key}"')
        lines.append("")

    # Remove file associations
    for fa in cfg.install.file_associations:
        hive, prefix = _fa_hive_prefix(fa)
        lines.append(f"  ; Remove file association: {fa.extension}")
        lines.append(f'  DeleteRegKey {hive} "{prefix}{fa.extension}"')
        if fa.prog_id:
            lines.append(f'  DeleteRegKey {hive} "{prefix}{fa.prog_id}"')

    # Remove environment variables
    _emit_env_var_removes(ctx, lines)

    # --- Logging: end ---
    if has_logging:
        lines.append('  !insertmacro LogWrite "Uninstallation completed."')
        lines.append('  !insertmacro LogClose')
        lines.append("")

    lines.extend([
        "SectionEnd",
        "",
    ])
    return lines


# -----------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------

def _emit_registry_writes(ctx: BuildContext, lines: List[str]) -> None:
    """Emit WriteRegStr / WriteRegDWORD for custom registry entries.

    Groups entries by registry view to minimize ``SetRegView`` toggles.
    """
    entries = ctx.config.install.registry_entries
    if not entries:
        return

    lines.append("  ; Custom registry entries")
    current_view: Optional[str] = None
    for entry in entries:
        key = ctx.resolve(entry.key)
        value = ctx.resolve(entry.value)
        target_view = entry.view if entry.view in ("32", "64") else None
        if target_view != current_view:
            if current_view is not None:
                lines.append("  SetRegView lastused")
            if target_view is not None:
                lines.append(f"  SetRegView {target_view}")
            current_view = target_view
        if entry.type == "dword":
            lines.append(f'  WriteRegDWORD {entry.hive} "{key}" "{entry.name}" {value}')
        elif entry.type == "expand":
            lines.append(f'  WriteRegExpandStr {entry.hive} "{key}" "{entry.name}" "{value}"')
        else:
            lines.append(f'  WriteRegStr {entry.hive} "{key}" "{entry.name}" "{value}"')
    if current_view is not None:
        lines.append("  SetRegView lastused")
    lines.append("")


def _emit_env_var_writes(ctx: BuildContext, lines: List[str]) -> None:
    """Emit environment variable writes (installer side)."""
    for env in ctx.config.install.env_vars:
        env_value = ctx.resolve(env.value)
        hive, key = _env_hive_key(env)
        lines.append(f"  ; Environment variable: {env.name} ({env.scope})")

        if env.append and env.name.upper() == "PATH":
            lines.extend([
                f'  ReadRegStr $0 {hive} "{key}" "{env.name}"',
                f'  StrCpy $1 "{env_value}"',
                "",
                '  ; Check whether the entry already exists',
                '  Push $0',
                '  Push $1',
                "  Call _StrContains",
                '  StrCmp $R9 "1" _skip_path_append',
                "",
                '  ; Append entry',
                '  StrCmp $0 "" 0 +2',
                f'    StrCpy $0 "{env_value}"',
                '  Goto +2',
                f'    StrCpy $0 "$0;{env_value}"',
                f'  WriteRegExpandStr {hive} "{key}" "{env.name}" "$0"',
                "",
                '  ; Broadcast WM_SETTINGCHANGE',
                '  SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=500',
                "",
                "_skip_path_append:",
            ])
        else:
            lines.append(f'  WriteRegStr {hive} "{key}" "{env.name}" "{env_value}"')
        lines.append("")


def _emit_env_var_removes(ctx: BuildContext, lines: List[str]) -> None:
    """Emit environment variable removal (uninstaller side)."""
    for env in ctx.config.install.env_vars:
        if not env.remove_on_uninstall:
            continue
        hive, key = _env_hive_key(env)

        if env.append and env.name.upper() == "PATH":
            env_value = ctx.resolve(env.value)
            lines.extend([
                f"  ; Remove PATH entry: {env_value}",
                f'  ReadRegStr $0 {hive} "{key}" "{env.name}"',
                f'  StrCpy $1 "{env_value}"',
                "  Call un._RemovePathEntry",
                f'  WriteRegExpandStr {hive} "{key}" "{env.name}" "$0"',
                '  SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=500',
                "",
            ])
        else:
            lines.append(f'  DeleteRegValue {hive} "{key}" "{env.name}"')


def _emit_shortcuts(ctx: BuildContext, lines: List[str]) -> None:
    """Emit CreateShortCut for desktop and start menu."""
    cfg = ctx.config

    desktop_target = cfg.install.desktop_shortcut_target
    if desktop_target:
        target = ctx.resolve(desktop_target)
        if not (target.startswith("$") or re.match(r"^[A-Za-z]:\\", target)):
            target = f"$INSTDIR\\{target}"
        lines.append("  ; Desktop shortcut")
        lines.append(f'  CreateShortCut "$DESKTOP\\${{APP_NAME}}.lnk" "{target}"')
        lines.append("")

    start_target = cfg.install.start_menu_shortcut_target
    if start_target:
        target = ctx.resolve(start_target)
        if not (target.startswith("$") or re.match(r"^[A-Za-z]:\\", target)):
            target = f"$INSTDIR\\{target}"
        lines.extend([
            "  ; Start menu shortcuts",
            '  CreateDirectory "$SMPROGRAMS\\${APP_NAME}"',
            f'  CreateShortCut "$SMPROGRAMS\\${{APP_NAME}}\\${{APP_NAME}}.lnk" "{target}"',
            '  CreateShortCut "$SMPROGRAMS\\${APP_NAME}\\Uninstall.lnk" "$INSTDIR\\Uninstall.exe"',
            "",
        ])


def _emit_file_associations(ctx: BuildContext, lines: List[str]) -> None:
    """Emit WriteRegStr for file associations."""
    for fa in ctx.config.install.file_associations:
        hive, prefix = _fa_hive_prefix(fa)
        lines.append(f"  ; File association: {fa.extension} -> {fa.application}")
        lines.append(f'  WriteRegStr {hive} "{prefix}{fa.extension}" "" "{fa.prog_id}"')
        if fa.prog_id:
            lines.append(f'  WriteRegStr {hive} "{prefix}{fa.prog_id}" "" "{fa.description}"')
        if fa.default_icon:
            lines.append(f'  WriteRegStr {hive} "{prefix}{fa.prog_id}\\DefaultIcon" "" "{fa.default_icon}"')
        verbs = fa.verbs or {}
        if verbs:
            for verb, cmd in verbs.items():
                lines.append(f'  WriteRegStr {hive} "{prefix}{fa.prog_id}\\Shell\\{verb}\\Command" "" "{cmd}"')
        elif fa.application:
            lines.append(f'  WriteRegStr {hive} "{prefix}{fa.prog_id}\\Shell\\Open\\Command" "" "{fa.application} \\"%1\\""')
        lines.append("")


# -----------------------------------------------------------------------
# Tiny shared utilities
# -----------------------------------------------------------------------

def _env_hive_key(env) -> tuple[str, str]:
    scope = (env.scope or "system").lower()
    if scope == "system":
        return "HKLM", "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment"
    return "HKCU", "Environment"


def _fa_hive_prefix(fa) -> tuple[str, str]:
    if getattr(fa, "register_for_all_users", True):
        return "HKCR", ""
    return "HKCU", "Software\\Classes\\"


def _flatten_packages(packages) -> list:
    flat = []
    for pkg in packages:
        if pkg.children:
            flat.extend(_flatten_packages(pkg.children))
        else:
            flat.append(pkg)
    return flat
