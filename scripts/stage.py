#!/usr/bin/env python3
"""Stage real source-built app, compiled launcher, metadata, and an independently checked ZIP."""
from __future__ import annotations
import argparse
import configparser
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import sys
import zipfile

APP_ID = 'GitHubDesktopPortableVhick'
FOLDER = 'GitHubDesktopPortable'

def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def check_pe(p: Path, machine: int | None = None):
    with p.open('rb') as f:
        if f.read(2) != b'MZ': raise RuntimeError(f'Not PE/MZ: {p}')
        f.seek(0x3c)
        offset = struct.unpack('<I', f.read(4))[0]
        if offset < 64 or offset > p.stat().st_size - 6: raise RuntimeError('Invalid PE offset')
        f.seek(offset)
        if f.read(4) != b'PE\0\0': raise RuntimeError(f'Not a PE: {p}')
        arch = struct.unpack('<H', f.read(2))[0]
        if machine is not None and arch != machine: raise RuntimeError(f'Wrong architecture {arch:#x}: {p}')

def walk_no_links(tree: Path):
    for p in [tree, *tree.rglob('*')]:
        if p.is_symlink(): raise RuntimeError(f'Symlink in package: {p}')

def build(args):
    source = args.source.resolve(strict=True)
    built = source / 'dist/GitHubDesktop-win32-x64'
    launcher = args.launcher.resolve(strict=True)
    icon = source / 'app/static/logos/prod/icon-logo.ico'
    if not icon.is_file(): raise RuntimeError(f'Vendor icon missing: {icon}')
    check_pe(built / 'GitHubDesktop.exe', 0x8664)
    check_pe(launcher, 0x8664)
    if not (built / 'resources/app/main.js').is_file():
        raise RuntimeError('Built resources/app/main.js missing; upstream output layout drift')
    identity = json.loads(args.identity.read_text(encoding='utf-8-sig'))
    ver = json.loads((source / 'app/package.json').read_text(encoding='utf-8'))['version']
    if identity['tag'] != f'release-{ver}': raise RuntimeError('Identity/tag mismatch')
    match = re.fullmatch(r'r(\d{1,4})', args.revision)
    if not match: raise RuntimeError('Revision must be r1 through r9999')
    package_revision = int(match.group(1))
    vparts = ver.split('.')
    if len(vparts) != 3: raise RuntimeError('Unexpected semantic version')
    package_version = f'{ver}.{package_revision}'
    root = args.workspace / FOLDER
    if root.exists(): raise RuntimeError(f'Refusing to overwrite staging {root}')
    (root / 'App').mkdir(parents=True)
    shutil.copytree(built, root / 'App/GitHubDesktop', symlinks=False)
    shutil.copy2(launcher, root / 'GitHubDesktopPortable.exe')
    ai = root / 'App/AppInfo'; ai.mkdir(parents=True)
    shutil.copy2(icon, ai / 'appicon.ico')
    from PIL import Image
    with Image.open(icon) as raw:
        for pixels in (16, 32):
            raw.resize((pixels, pixels), Image.Resampling.LANCZOS).save(ai / f'appicon_{pixels}.png')
    appinfo = f'''[Format]
Type=PortableApps.comFormat
Version=3.8

[Details]
Name=GitHub Desktop Portable (Unofficial)
AppID={APP_ID}
Publisher=GitHub, Inc. (upstream), community portable packaging
Homepage=https://github.com/desktop/desktop
Category=Development
Description=GitHub Desktop GUI with a launcher-managed portable profile
Language=Multilingual

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true

[Version]
PackageVersion={package_version}
DisplayVersion={ver} Portable r{package_revision}

[Control]
Icons=1
Start=GitHubDesktopPortable.exe
'''
    (ai / 'appinfo.ini').write_text(appinfo, encoding='utf-8', newline='\n')
    for p in ['Data/Profile/Chromium', 'Data/Profile/logs', 'Data/GitHome', 'Data/TraceGuard', 'Other/Source']:
        (root / p).mkdir(parents=True, exist_ok=True)
    other = root / 'Other/Source'
    for file in ['LICENSE', 'NOTICE.md']:
        path = source / file
        if path.is_file(): shutil.copy2(path, other / f'upstream-{file}')
    shutil.copy2(args.identity, other / 'source-identity.json')
    shutil.copy2(args.patch_manifest, other / 'source-patch-manifest.json')
    (other / 'PACKAGE-BUILD.txt').write_text(
        f'Upstream: https://github.com/desktop/desktop\nTag: {identity["tag"]}\n'
        f'Commit: {identity["commit"]}\nYarn lock SHA256: {identity["yarn_lock_sha256"]}\n'
        f'Builder SHA: {args.builder_sha}\nPackage revision: {args.revision}\n'
        'This is an unsigned, unofficial, source-modified build.\n', encoding='utf-8')
    (other / 'Configure-Browser-SignIn.cmd').write_text(
        '@echo off\n"%~dp0..\\..\\GitHubDesktopPortable.exe" --auth-redirect-settings\n',
        encoding='utf-8', newline='\r\n')
    (other / 'PORTABILITY-LIMITS.txt').write_text(
        'Electron profile is redirected to Data/Profile; global Git config to Data/GitHome.\n'
        'Browser OAuth temporarily uses HKCU x-github-desktop-auth only after explicit opt-in.\n'
        'Exact prior command/URL Protocol values saved to Data/TraceGuard/AuthProtocolRecovery.bin, restored after complete exit.\n'
        'Interrupted recovery is conditional on owned-command match and never overwrites newer host changes.\n'
        'Changing Windows Default Apps UserChoice, multiple concurrent portable copies, or a different privilege level can block redirects.\n'
        'Windows Credential Manager/keytar tokens are NOT confirmed portable or isolated.\n'
        'Notification click activation is NOT guaranteed without separate OS registration.\n'
        'Shell caches, Windows file dialogs, external editors, Git hooks, SSH may touch host.\n'
        'Do not run simultaneously with the installed app when testing sign-in.\n', encoding='utf-8')
    walk_no_links(root)
    zippath = args.output / f'GitHubDesktopPortable_{ver}_x64_{args.revision}.zip'
    args.output.mkdir(parents=True, exist_ok=True)
    if zippath.exists(): raise RuntimeError(f'Refusing ZIP overwrite: {zippath}')
    with zipfile.ZipFile(zippath, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
        for p in sorted(root.rglob('*')):
            arc = p.relative_to(root.parent).as_posix()
            if p.is_dir(): z.writestr(arc.rstrip('/') + '/', b'')
            else: z.write(p, arc)
    verify_zip(zippath, ver, package_version)
    report = {'zip': zippath.name, 'sha256': sha(zippath), 'size': zippath.stat().st_size,
              'source': identity, 'builder_sha': args.builder_sha, 'package_version': package_version,
              'app_path': str(root)}
    (args.output / 'build-manifest.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    if args.github_output:
        with args.github_output.open('a', encoding='utf-8') as f:
            f.write(f'zip_file={zippath.as_posix()}\n')
            f.write(f'package_version={package_version}\n')

def verify_zip(path: Path, version: str | None = None, pkg_version: str | None = None):
    with zipfile.ZipFile(path) as f:
        bad = f.testzip()
        if bad: raise RuntimeError(f'Corrupt ZIP member: {bad}')
        names = set(f.namelist())
        base = FOLDER + '/'
        needed = [base + 'GitHubDesktopPortable.exe', base + 'App/GitHubDesktop/GitHubDesktop.exe',
                  base + 'App/GitHubDesktop/resources/app/main.js', base + 'App/AppInfo/appinfo.ini',
                  base + 'App/AppInfo/appicon.ico', base + 'App/AppInfo/appicon_16.png',
                  base + 'App/AppInfo/appicon_32.png', base + 'Other/Source/source-identity.json',
                  base + 'Data/TraceGuard/', base + 'Other/Source/Configure-Browser-SignIn.cmd']
        if set(needed) - names: raise RuntimeError(f'ZIP missing: {sorted(set(needed)-names)}')
        if any(x.startswith('/') or '..' in x.split('/') or '\\' in x for x in names):
            raise RuntimeError('ZIP contains unsafe member names')
        for entry in [base+'GitHubDesktopPortable.exe', base+'App/GitHubDesktop/GitHubDesktop.exe']:
            data = f.read(entry)
            if data[:2] != b'MZ': raise RuntimeError(f'ZIP contains non-PE executable: {entry}')
            peoff = struct.unpack_from('<I', data, 0x3c)[0]
            if data[peoff:peoff+4] != b'PE\0\0': raise RuntimeError(f'ZIP invalid PE: {entry}')
            if struct.unpack_from('<H', data, peoff+4)[0] != 0x8664: raise RuntimeError('ZIP architecture wrong')
        text = f.read(base+'App/AppInfo/appinfo.ini').decode('utf-8')
        cfg = configparser.ConfigParser(); cfg.read_string(text)
        if cfg.get('Details','AppID') != APP_ID or cfg.get('Control','Start') != 'GitHubDesktopPortable.exe':
            raise RuntimeError('Incorrect PortableApps metadata')
        if pkg_version and cfg.get('Version','PackageVersion') != pkg_version: raise RuntimeError('PackageVersion mismatch')
        if version and not text.count(f'DisplayVersion={version}'): raise RuntimeError('DisplayVersion mismatch')
    print('STATIC-VALIDATED: PortableApps ZIP integrity, layout, PE headers, AppID, and metadata')

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source', type=Path)
    p.add_argument('--launcher', type=Path)
    p.add_argument('--identity', type=Path)
    p.add_argument('--patch-manifest', type=Path)
    p.add_argument('--revision', default='r1')
    p.add_argument('--builder-sha', default='unknown')
    p.add_argument('--workspace', type=Path, default=Path('work'))
    p.add_argument('--output', type=Path, default=Path('dist'))
    p.add_argument('--github-output', type=Path)
    p.add_argument('--verify-zip', type=Path)
    a=p.parse_args()
    if a.verify_zip: verify_zip(a.verify_zip)
    else:
        for field in ('source','launcher','identity','patch_manifest'):
            if getattr(a, field) is None: p.error(f'--{field.replace("_","-")} is required')
        build(a)
