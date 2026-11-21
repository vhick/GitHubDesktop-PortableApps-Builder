#!/usr/bin/env python3
"""Version-adaptive, strict, preflighted GitHub Desktop portable source adapter.

Accept a published stable source tag's actual source (verified by get_source.ps1),
not just a hard-coded version string. Fail before ANY modifications when source
structure, OAuth callback contract, license, or a required anchor drifts.
The post-patch Windows build+stage validation is independent of these static gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil


MIN_AUDITED_VERSION = (3, 6, 10)
OAUTH_DEV_SCHEME = 'x-github-desktop-dev-auth'


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def assert_unique(text: str, anchor: str, where: Path) -> None:
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"Refusing source drift: {where}: expected one {anchor!r}, found {count}")


def replace_exact(path: Path, old: str, new: str) -> dict:
    """Small unit-testable replacement, with exact uniqueness checking."""
    original = read(path)
    assert_unique(original, old, path)
    updated = original.replace(old, new)
    path.write_text(updated, encoding='utf-8', newline='\n')
    return {'file': path.as_posix(), 'before_sha256': sha(original.encode('utf-8')),
            'after_sha256': sha(updated.encode('utf-8')), 'anchor': old}


def check_source_contract(root: Path) -> str:
    pkg_path = root / 'app/package.json'
    pkg = json.loads(read(pkg_path))
    version = pkg.get('version')
    if not isinstance(version, str) or not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise RuntimeError('Refusing upstream version: expected stable X.Y.Z in app/package.json')
    if tuple(int(x) for x in version.split('.')) < MIN_AUDITED_VERSION:
        raise RuntimeError(f'Unsupported old upstream version {version}; minimum audited baseline 3.6.10')
    if pkg.get('name') != 'desktop' or pkg.get('productName') != 'GitHub Desktop' or pkg.get('license') != 'MIT':
        raise RuntimeError('Upstream package identity/license drift: manual review required')
    # Ensure the public development OAuth client and callback are still tied
    # together. A changed flow is unsafe to paper over with broad URL/registry edits.
    app_info = read(root / 'app/app-info.ts')
    main = read(root / 'app/src/main-process/main.ts')
    required_oauth = [
        "__DEV_SECRETS__: isDevBuild || !process.env.DESKTOP_OAUTH_CLIENT_SECRET",
        'process.env.DESKTOP_OAUTH_CLIENT_ID || devClientId',
        'process.env.DESKTOP_OAUTH_CLIENT_SECRET || devClientSecret',
    ]
    for token in required_oauth:
        if token not in app_info:
            raise RuntimeError(f'Upstream development OAuth contract changed: {token}')
    for token in [
        "if (__DEV_SECRETS__) {\n  possibleProtocols.add('x-github-desktop-dev-auth')",
        "} else {\n  possibleProtocols.add('x-github-desktop-auth')",
        "const protocolLauncherArg = '--protocol-launcher'",
        'app.requestSingleInstanceLock()',
        "args['protocol-launcher'] === true",
    ]:
        if token not in main:
            raise RuntimeError(f'Upstream browser callback/single-instance contract changed: {token}')
    # The first import must be the logging one; the source patch puts our
    # Electron path init BEFORE it so logging and the framework cannot race it.
    if not main.startswith("import '../lib/logging/main/install'"):
        raise RuntimeError('Upstream main.ts initialization order changed; manual early-portability audit required')
    return version


def operations(root: Path):
    main = root / 'app/src/main-process/main.ts'
    window = root / 'app/src/main-process/app-window.ts'
    notifications = root / 'app/src/main-process/notifications.ts'
    build = root / 'script/build.ts'
    return [
        (main, "import '../lib/logging/main/install'",
         "import './portable-bootstrap'\nimport '../lib/logging/main/install'"),
        (main, '  possibleProtocols.forEach(protocol => setAsDefaultProtocolClient(protocol))',
         '  // Portable mode must not override installed application URL handlers.\n'
         '  if (!process.env.GHD_PORTABLE_ROOT) {\n'
         '    possibleProtocols.forEach(protocol => setAsDefaultProtocolClient(protocol))\n'
         '  }'),
        (window, '    this.setupAutoUpdater()',
         '    // Squirrel updates cannot safely replace a PortableApps installation.\n'
         '    if (!process.env.GHD_PORTABLE_ROOT) this.setupAutoUpdater()'),
        (window, '  public async checkForUpdates(url: string) {',
         '  public async checkForUpdates(url: string) {\n'
         '    if (process.env.GHD_PORTABLE_ROOT) {\n'
         '      return new Error("Portable updates are managed by replacing App, preserving Data")\n'
         '    }'),
        (window, '  public quitAndInstallUpdate() {\n    autoUpdater.quitAndInstall()',
         '  public quitAndInstallUpdate() {\n'
         '    if (process.env.GHD_PORTABLE_ROOT) return\n'
         '    autoUpdater.quitAndInstall()'),
        (notifications, '  windowsToastActivatorClsid = findToastActivatorClsid()',
         '  windowsToastActivatorClsid = process.env.GHD_PORTABLE_ROOT\n'
         "    ? '{8FD8B901-28BA-4BBA-A281-43A0BE60179E}'\n"
         '    : findToastActivatorClsid()'),
        (build, 'const isPublishableBuild = isPublishable()',
         '// This unofficial source build has no GitHub, Inc. code signing credentials.\n'
         "const isPublishableBuild = isPublishable() && process.env.GHD_PORTABLE_SOURCE_BUILD !== '1'"),
    ]


def apply(source: Path, patch_dir: Path) -> list[dict]:
    root = source.resolve(strict=True)
    version = check_source_contract(root)
    boot = root / 'app/src/main-process/portable-bootstrap.ts'
    if boot.exists():
        raise RuntimeError('Refusing to overwrite existing upstream portable-bootstrap.ts')
    bootstrap = patch_dir / 'portable-bootstrap.ts'
    if not bootstrap.is_file():
        raise RuntimeError(f'Missing application-specific portable bootstrap: {bootstrap}')
    bootstrap_text = read(bootstrap)
    for required in ("app.setPath('userData'", "app.setPath('sessionData'", 'app.setAppLogsPath('):
        if required not in bootstrap_text:
            raise RuntimeError(f'Portable bootstrap is missing mandatory pre-launch path: {required}')

    # Preflight ALL expected source files/anchors, before mutating ANY source.
    # Read each original only once; staged replacement also checks duplicates.
    edits = operations(root)
    originals: dict[Path, str] = {}
    updated: dict[Path, str] = {}
    manifest = []
    for path, old, new in edits:
        if path not in originals:
            originals[path] = read(path)
            updated[path] = originals[path]
        assert_unique(originals[path], old, path)
        assert_unique(updated[path], old, path)
        updated[path] = updated[path].replace(old, new)
        manifest.append({'file': path.relative_to(root).as_posix(),
                         'upstream_version': version, 'anchor': old,
                         'before_file_sha256': sha(originals[path].encode('utf-8'))})
    for path, text in updated.items():
        path.write_text(text, encoding='utf-8', newline='\n')
    shutil.copy2(bootstrap, boot)
    for entry in manifest:
        changed = root / entry['file']
        entry['after_file_sha256'] = sha(changed.read_bytes())
    manifest.append({'file': boot.relative_to(root).as_posix(),
                     'upstream_version': version, 'created_sha256': sha(boot.read_bytes())})
    print(f'Adapted GitHub Desktop {version}: {len(manifest)} strict source changes; preflight passed. '
          'A later Windows source build and runtime tests are still required.')
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
