#!/usr/bin/env python3
"""Fail-closed, upstream-version-specific source modifications. No fuzzy replacements."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def replace_exact(path: Path, old: str, new: str) -> dict:
    original = path.read_text(encoding='utf-8')
    count = original.count(old)
    if count != 1:
        raise RuntimeError(f"Refusing source drift: {path}: expected one {old!r}, found {count}")
    updated = original.replace(old, new)
    path.write_text(updated, encoding='utf-8', newline='\n')
    return {'file': path.as_posix(), 'before_sha256': hashlib.sha256(original.encode()).hexdigest(),
            'after_sha256': hashlib.sha256(updated.encode()).hexdigest(), 'anchor': old}


def apply(source: Path, patch_dir: Path) -> list[dict]:
    root = source.resolve(strict=True)
    pkg = json.loads((root / 'app' / 'package.json').read_text(encoding='utf-8'))
    version = pkg['version']
    # 3.6.10 has been source-inspected. New stable releases STOP unless deliberately audited.
    if version != '3.6.10':
        raise RuntimeError(f'No audited patch adapter for {version}; supported upstream version: 3.6.10. '
                           'Choose 3.6.10 explicitly, or audit and update the source adapter.')
    main = root / 'app/src/main-process/main.ts'
    window = root / 'app/src/main-process/app-window.ts'
    notifications = root / 'app/src/main-process/notifications.ts'
    build = root / 'script/build.ts'
    manifest = []
    manifest.append(replace_exact(main,
        "import '../lib/logging/main/install'",
        "import './portable-bootstrap'\nimport '../lib/logging/main/install'"))
    manifest.append(replace_exact(main,
        '  possibleProtocols.forEach(protocol => setAsDefaultProtocolClient(protocol))',
        '  // Portable mode must not override installed application URL handlers.\n'
        '  if (!process.env.GHD_PORTABLE_ROOT) {\n'
        '    possibleProtocols.forEach(protocol => setAsDefaultProtocolClient(protocol))\n'
        '  }'))
    manifest.append(replace_exact(window,
        '    this.setupAutoUpdater()',
        '    // Squirrel updates cannot safely replace a PortableApps installation.\n'
        '    if (!process.env.GHD_PORTABLE_ROOT) this.setupAutoUpdater()'))
    manifest.append(replace_exact(window,
        '  public async checkForUpdates(url: string) {',
        '  public async checkForUpdates(url: string) {\n'
        '    if (process.env.GHD_PORTABLE_ROOT) {\n'
        '      return new Error("Portable updates are managed by replacing App, preserving Data")\n'
        '    }'))
    manifest.append(replace_exact(window,
        '  public quitAndInstallUpdate() {\n    autoUpdater.quitAndInstall()',
        '  public quitAndInstallUpdate() {\n'
        '    if (process.env.GHD_PORTABLE_ROOT) return\n'
        '    autoUpdater.quitAndInstall()'))
    # Portable notifications must not borrow the installed Squirrel CLSID.
    # Native click-to-open requires explicit separate Windows registration, not enabled by default.
    manifest.append(replace_exact(notifications,
        '  windowsToastActivatorClsid = findToastActivatorClsid()',
        "  windowsToastActivatorClsid = process.env.GHD_PORTABLE_ROOT\n"
        "    ? '{8FD8B901-28BA-4BBA-A281-43A0BE60179E}'\n"
        '    : findToastActivatorClsid()'))
    manifest.append(replace_exact(build,
        'const isPublishableBuild = isPublishable()',
        "// This unofficial source build has no GitHub, Inc. code signing credentials.\n"
        "const isPublishableBuild = isPublishable() && process.env.GHD_PORTABLE_SOURCE_BUILD !== '1'"))
    boot = root / 'app/src/main-process/portable-bootstrap.ts'
    if boot.exists():
        raise RuntimeError('Refusing to overwrite existing upstream portable-bootstrap.ts')
    shutil.copy2(patch_dir / 'portable-bootstrap.ts', boot)
    manifest.append({'file': boot.as_posix(), 'created_sha256': hashlib.sha256(boot.read_bytes()).hexdigest()})
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--patches', default='patches', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = apply(args.source, args.patches)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Patched {len(result)} source locations, fail-closed version: 3.6.10')
