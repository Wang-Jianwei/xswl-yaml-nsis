"""Run SigVNA conversion: read tmp/sigvna_installer.yaml, validate icon/license,
split app_deploy into packages, generate NSIS and inject components (app + PXI).

Usage:
  python examples/run_sigvna_converter.py [-c tmp/sigvna_installer.yaml] [-v]
"""
import os
import sys
import shutil
from pathlib import Path
import yaml
import argparse

from xswl_yaml_nsis.config import PackageConfig
from xswl_yaml_nsis.converter import YamlToNsisConverter


def find_existing(path_candidates):
    for p in path_candidates:
        if os.path.exists(p):
            return p
    return None


def split_into_packages(src_dir: Path, out_root: Path):
    packages_dir = out_root / "app_installer" / "packages"
    app_pkg = packages_dir / "app"
    pxi_pkg = packages_dir / "PXI_driver"
    app_pkg.mkdir(parents=True, exist_ok=True)
    pxi_pkg.mkdir(parents=True, exist_ok=True)

    if not src_dir.exists():
        print(f"Warning: source deploy dir not found: {src_dir}")
        return app_pkg, pxi_pkg

    for p in src_dir.rglob('*'):
        if p.is_file():
            rel = p.relative_to(src_dir)
            name_lower = str(rel).lower()
            if 'pxi' in name_lower or 'pxi_driver' in name_lower:
                target = pxi_pkg / rel.name
            else:
                target = app_pkg / rel.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)
    return app_pkg, pxi_pkg


def build_package_config(cfg: dict, app_pkg: Path, license_path: str = None):
    # Normalize icon/license to exist
    app = cfg.get('app', {})
    install = cfg.get('install', {})

    files = []
    files.append({
        'source': str(app_pkg / '*'),
        'destination': '$INSTDIR',
        'recursive': True
    })
    if license_path:
        # Include license into installer files so MUI license page can use it
        files.append({
            'source': license_path,
            'destination': '$INSTDIR',
            'recursive': False
        })

    package_dict = {
        'app': app,
        'install': install,
        'files': files,
        'signing': cfg.get('signing', {}),
        'update': cfg.get('update', {})
    }
    return PackageConfig.from_dict(package_dict)


def insert_components_and_sections(base_nsi: Path, out_nsi: Path, app_pkg: Path, pxi_pkg: Path):
    with open(base_nsi, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Insert components page before directory page
    for idx, line in enumerate(lines):
        if '!insertmacro MUI_PAGE_DIRECTORY' in line:
            lines.insert(idx, '!insertmacro MUI_PAGE_COMPONENTS\n')
            break

    # Remove File lines inside the generated Section "Install" to avoid duplication
    out_lines = []
    in_install_section = False
    for line in lines:
        if line.strip().startswith('Section "Install"'):
            in_install_section = True
            out_lines.append(line)
            continue
        if in_install_section:
            if line.strip().startswith('SectionEnd'):
                in_install_section = False
                out_lines.append(line)
            else:
                if line.strip().startswith('File '):
                    continue
                else:
                    out_lines.append(line)
        else:
            out_lines.append(line)

    # Prepare injected component sections
    injection = []
    injection.append('\n; --- Component Sections (injected by examples/run_sigvna_converter.py) ---\n')
    injection.append('Section "App" SEC_APP\n')
    injection.append('  SetOutPath $INSTDIR\n')
    injection.append(f'  File /r "{os.path.join(str(Path('app_installer'), 'packages', 'app', '*'))}"\n')
    injection.append('SectionEnd\n\n')
    injection.append('Section "PXI Driver" SEC_PXI\n')
    injection.append('  SetOutPath "$INSTDIR\\drivers\\PXI"\n')
    injection.append(f'  File /r "{os.path.join(str(Path('app_installer'), 'packages', 'PXI_driver', '*'))}"\n')
    injection.append('SectionEnd\n\n')

    # Insert before Uninstaller section
    final_lines = []
    inserted = False
    for line in out_lines:
        if (not inserted) and line.strip().startswith('Section "Uninstall"'):
            final_lines.extend(injection)
            inserted = True
        final_lines.append(line)

    # Add PXI cleanup in Uninstaller before SectionEnd
    result = []
    in_uninstall = False
    for line in final_lines:
        if line.strip().startswith('Section "Uninstall"'):
            in_uninstall = True
            result.append(line)
            continue
        if in_uninstall:
            if line.strip().startswith('SectionEnd'):
                result.append('  ; Remove PXI driver files\n')
                result.append('  RMDir /r "$INSTDIR\\drivers\\PXI"\n\n')
                in_uninstall = False
                result.append(line)
            else:
                result.append(line)
        else:
            result.append(line)

    with open(out_nsi, 'w', encoding='utf-8') as f:
        f.writelines(result)

    print(f'Wrote final NSIS script to {out_nsi}')


def main():
    parser = argparse.ArgumentParser(description='Generate SigVNA NSIS with optional PXI component')
    parser.add_argument('-c', '--config', default='tmp/sigvna_installer.yaml')
    parser.add_argument('--src', default='tmp/build-20260123-cascade/app_deploy')
    parser.add_argument('--work', default='tmp/build-20260123-cascade')
    parser.add_argument('-o', '--output', default='tmp/sigvna_installer.nsi')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    cfg_path = Path(args.config)

    if not cfg_path.exists():
        print(f"Error: config file not found: {cfg_path}")
        sys.exit(1)

    cfg = yaml.safe_load(cfg_path.read_text(encoding='utf-8'))

    # Validate/auto-fix icon
    icon = cfg.get('app', {}).get('icon')
    icon_candidates = []
    if icon:
        icon_candidates.append(icon)
        icon_candidates.append(str(repo_root / icon))
    # common locations in tmp data
    icon_candidates += [
        'tmp/SigVNA-20260123-cascade/logo.ico',
        'tmp/SigVNA-20260123-cascade/logo.png',
        'tmp/SigVNA-20260123-cascade/logo.PNG',
        'tmp/SigVNA-20260123-cascade/logo.ico'
    ]
    found_icon = find_existing(icon_candidates)
    if found_icon:
        # set relative path from repo root
        rel_icon = os.path.relpath(found_icon, start=str(repo_root))
        cfg.setdefault('app', {})['icon'] = rel_icon
        if args.verbose:
            print(f'Using icon: {rel_icon}')
    else:
        # remove icon if not found
        cfg.setdefault('app', {})['icon'] = ''
        print('Warning: icon not found; icon will be omitted from NSIS')

    # Validate/auto-fix license
    license_candidate = cfg.get('app', {}).get('license')
    license_found = None
    if license_candidate and os.path.exists(license_candidate):
        license_found = license_candidate
    elif os.path.exists('LICENSE'):
        license_found = 'LICENSE'
    if license_found:
        cfg.setdefault('app', {})['license'] = license_found
        if args.verbose:
            print(f'Using license: {license_found}')
    else:
        cfg.setdefault('app', {})['license'] = ''
        print('Warning: license not found; license page will be omitted')

    # Split into packages
    app_pkg, pxi_pkg = split_into_packages(Path(args.src), Path(args.work))

    # Build PackageConfig
    license_path = cfg['app'].get('license') if cfg['app'].get('license') else None
    package_config = build_package_config(cfg, app_pkg, license_path)

    # Convert and save base NSIS
    converter = YamlToNsisConverter(package_config)
    base_nsi = Path(args.work) / 'installer_base.nsi'
    converter.save(str(base_nsi))
    print(f'Generated base NSIS: {base_nsi}')

    # Inject components and produce final NSIS
    insert_components_and_sections(base_nsi, Path(args.output), app_pkg, pxi_pkg)
    print('Done.')


if __name__ == '__main__':
    main()
