"""
NSIS helper functions emitted into the generated script.

Contains:
- Logging macros (LogInit / LogWrite / LogClose) — fallback file-based
  logging when the NSIS build does not support ``LogSet``.
- PATH manipulation helpers (_Contains, _NormalizePathEntry,
  _RemovePathEntry) that are only included when ``append=True`` env vars
  are present.
- VerifyChecksum / ExtractArchive stubs.
"""

from __future__ import annotations

from typing import List

from .context import BuildContext


# -----------------------------------------------------------------------
# Logging macros
# -----------------------------------------------------------------------

def generate_log_macros() -> List[str]:
    r"""Emit reusable ``!macro`` blocks for structured install/uninstall logging.

    Three macros are generated:

    * **LogInit** – opens (or creates) the log file and writes a header.
    * **LogWrite** ``<message>`` – appends one timestamped line.
    * **LogClose** – writes a footer and closes the file handle.

    The macros use compile-time ``!ifdef LOG_FILE`` guards so they
    silently become no-ops when logging is not configured.  They are
    safe to call from *any* Section or Function (installer **and**
    uninstaller) because ``!macro`` expansion is context-free.

    The file handle ``$_LOG_HANDLE`` is stored in ``$R9`` (callers
    should not clobber it between LogInit and LogClose).
    """
    return [
        "; ===========================================================================",
        "; Logging Macros",
        "; ===========================================================================",
        "",
        "; --- Var for log file handle ---",
        "Var _LOG_HANDLE",
        "",
        "; ---------------------------------------------------------------------------",
        "; LogInit – open log file and write header",
        ";   Usage: !insertmacro LogInit <title>",
        ";          e.g.  !insertmacro LogInit \"Install\"",
        ";   Note: Installer uses 'w' (write/truncate) to start fresh; Uninstaller",
        ";         uses 'a' (append) so both install and uninstall logs are kept.",
        "; ---------------------------------------------------------------------------",
        "!macro LogInit _title",
        "!ifdef LOG_FILE",
        '  CreateDirectory "$INSTDIR"',
        '  !ifdef __UNINSTALL__',
        '    ; Uninstaller: append to existing log',
        '    FileOpen $_LOG_HANDLE "${LOG_FILE}" a',
        '  !else',
        '    ; Installer: start fresh (truncate old log)',
        '    FileOpen $_LOG_HANDLE "${LOG_FILE}" w',
        '  !endif',
        '  FileSeek $_LOG_HANDLE 0 END',
        '  FileWrite $_LOG_HANDLE "=======================================================$\\r$\\n"',
        '  FileWrite $_LOG_HANDLE "${APP_NAME} ${APP_VERSION} - ${_title}$\\r$\\n"',
        '  FileWrite $_LOG_HANDLE "Date: ${__DATE__} ${__TIME__}$\\r$\\n"',
        '  FileWrite $_LOG_HANDLE "=======================================================$\\r$\\n"',
        "!endif",
        "!macroend",
        "",
        "; ---------------------------------------------------------------------------",
        "; LogWrite – append a single message line",
        ";   Usage: !insertmacro LogWrite <message>",
        "; ---------------------------------------------------------------------------",
        "!macro LogWrite _msg",
        "!ifdef LOG_FILE",
        '  FileWrite $_LOG_HANDLE "[${__DATE__} ${__TIME__}] ${_msg}$\\r$\\n"',
        "!endif",
        "!macroend",
        "",
        "; ---------------------------------------------------------------------------",
        "; LogClose – write footer and close the file",
        "; ---------------------------------------------------------------------------",
        "!macro LogClose",
        "!ifdef LOG_FILE",
        '  FileWrite $_LOG_HANDLE "-------------------------------------------------------$\\r$\\n"',
        '  FileWrite $_LOG_HANDLE "Completed.$\\r$\\n$\\r$\\n"',
        '  FileClose $_LOG_HANDLE',
        "!endif",
        "!macroend",
        "",
    ]


def generate_path_helpers(ctx: BuildContext) -> List[str]:
    """Emit NSIS helper functions for PATH append / remove.

    These helpers are correct pure-NSIS and do NOT rely on
    ``StrRep.nsh`` or any third-party includes.
    """
    lines: List[str] = []

    lines.extend([
        "; ---------------------------------------------------------------------------",
        "; Helper: _StrContains — check if $1 (needle) is in $0 (haystack)",
        ";   Returns $R9 = 1 if found, 0 otherwise; $R8 = index of match",
        "; ---------------------------------------------------------------------------",
        "Function _StrContains",
        "  Push $R0",
        "  Push $R1",
        "  Push $R2",
        "  Push $R3",
        "  Push $R4",
        "",
        "  StrLen $R2 $0  ; haystack length",
        "  StrLen $R3 $1  ; needle length",
        "  StrCpy $R9 0   ; default: not found",
        "  StrCpy $R8 -1",
        "",
        "  ; Edge case: empty needle always matches at 0",
        "  IntCmp $R3 0 _sc_found 0 0",
        "",
        "  ; If needle is longer than haystack, cannot match",
        "  IntCmp $R3 $R2 0 0 _sc_done",
        "",
        "  IntOp $R4 $R2 - $R3  ; last valid start index",
        "  StrCpy $R0 0          ; current index",
        "",
        "_sc_loop:",
        "  IntCmp $R0 $R4 0 0 _sc_done    ; index > last valid → done",
        "  StrCpy $R1 $0 $R3 $R0          ; extract substring",
        "  StrCmp $R1 $1 _sc_found",
        "  IntOp $R0 $R0 + 1",
        "  Goto _sc_loop",
        "",
        "_sc_found:",
        "  StrCpy $R9 1",
        "  StrCpy $R8 $R0",
        "",
        "_sc_done:",
        "  Pop $R4",
        "  Pop $R3",
        "  Pop $R2",
        "  Pop $R1",
        "  Pop $R0",
        "FunctionEnd",
        "",
    ])

    lines.extend([
        "; ---------------------------------------------------------------------------",
        "; Helper: _RemovePathEntry — remove exact semicolon-delimited entry $1 from $0",
        ";   Modifies $0 in-place.",
        "; ---------------------------------------------------------------------------",
        "Function _RemovePathEntry",
        "  Push $R0",
        "  Push $R1",
        "  Push $R2",
        "  Push $R3",
        "",
        '  StrCpy $0 ";$0;"   ; wrap so every entry has ; on both sides',
        '  StrCpy $1 ";$1;"',
        "",
        "_rpe_loop:",
        "  ; Check if $1 exists in $0",
        "  Push $0",
        "  Push $1",
        "  Call _StrContains",
        '  StrCmp $R9 "0" _rpe_done',
        "",
        "  ; Found at $R8 — splice it out",
        "  StrLen $R2 $1",
        "  StrCpy $R0 $0 $R8          ; prefix",
        "  IntOp $R3 $R8 + $R2",
        "  StrCpy $R1 $0 '' $R3       ; suffix",
        '  StrCpy $0 "$R0$R1"',
        "  Goto _rpe_loop",
        "",
        "_rpe_done:",
        "  ; Strip wrapping semicolons",
        "  StrLen $R2 $0",
        "  IntOp $R2 $R2 - 2",
        "  IntCmp $R2 0 _rpe_empty 0 0",
        "  StrCpy $0 $0 $R2 1",
        "  Goto _rpe_exit",
        "",
        "_rpe_empty:",
        '  StrCpy $0 ""',
        "",
        "_rpe_exit:",
        "  Pop $R3",
        "  Pop $R2",
        "  Pop $R1",
        "  Pop $R0",
        "FunctionEnd",
        "",
    ])

    # Uninstaller copies — NSIS requires un.Function for uninstaller
    lines.extend([
        "; Uninstaller copies of the above helpers",
        "Function un._StrContains",
        "  Push $R0",
        "  Push $R1",
        "  Push $R2",
        "  Push $R3",
        "  Push $R4",
        "  StrLen $R2 $0",
        "  StrLen $R3 $1",
        "  StrCpy $R9 0",
        "  StrCpy $R8 -1",
        "  IntCmp $R3 0 _usc_found 0 0",
        "  IntCmp $R3 $R2 0 0 _usc_done",
        "  IntOp $R4 $R2 - $R3",
        "  StrCpy $R0 0",
        "_usc_loop:",
        "  IntCmp $R0 $R4 0 0 _usc_done",
        "  StrCpy $R1 $0 $R3 $R0",
        "  StrCmp $R1 $1 _usc_found",
        "  IntOp $R0 $R0 + 1",
        "  Goto _usc_loop",
        "_usc_found:",
        "  StrCpy $R9 1",
        "  StrCpy $R8 $R0",
        "_usc_done:",
        "  Pop $R4",
        "  Pop $R3",
        "  Pop $R2",
        "  Pop $R1",
        "  Pop $R0",
        "FunctionEnd",
        "",
        "Function un._RemovePathEntry",
        "  Push $R0",
        "  Push $R1",
        "  Push $R2",
        "  Push $R3",
        '  StrCpy $0 ";$0;"',
        '  StrCpy $1 ";$1;"',
        "_urpe_loop:",
        "  Push $0",
        "  Push $1",
        "  Call un._StrContains",
        '  StrCmp $R9 "0" _urpe_done',
        "  StrLen $R2 $1",
        "  StrCpy $R0 $0 $R8",
        "  IntOp $R3 $R8 + $R2",
        "  StrCpy $R1 $0 '' $R3",
        '  StrCpy $0 "$R0$R1"',
        "  Goto _urpe_loop",
        "_urpe_done:",
        "  StrLen $R2 $0",
        "  IntOp $R2 $R2 - 2",
        "  IntCmp $R2 0 _urpe_empty 0 0",
        "  StrCpy $0 $0 $R2 1",
        "  Goto _urpe_exit",
        "_urpe_empty:",
        '  StrCpy $0 ""',
        "_urpe_exit:",
        "  Pop $R3",
        "  Pop $R2",
        "  Pop $R1",
        "  Pop $R0",
        "FunctionEnd",
        "",
    ])

    return lines


def generate_checksum_helper() -> List[str]:
    """Emit placeholder VerifyChecksum / ExtractArchive functions."""
    return [
        "; ---------------------------------------------------------------------------",
        "; Helper: VerifyChecksum (placeholder — needs a proper plugin)",
        "; ---------------------------------------------------------------------------",
        "Function VerifyChecksum",
        "  ; Stack: file_path, checksum_type, checksum_value",
        "  Pop $R2  ; checksum_value",
        "  Pop $R1  ; checksum_type",
        "  Pop $R0  ; file_path",
        "  ; TODO: Implement using Crypto plugin or PowerShell Get-FileHash.",
        '  StrCpy $0 "0"  ; 0 = success',
        "  Push $0",
        "FunctionEnd",
        "",
        "; ---------------------------------------------------------------------------",
        "; Helper: ExtractArchive (placeholder)",
        "; ---------------------------------------------------------------------------",
        "Function ExtractArchive",
        "  ; Stack: archive_path, dest_dir",
        "  Pop $R1  ; dest_dir",
        "  Pop $R0  ; archive_path",
        "  ; TODO: Implement using nsisunz or 7z plugin.",
        "FunctionEnd",
        "",
    ]
