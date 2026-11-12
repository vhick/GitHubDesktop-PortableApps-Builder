#!/usr/bin/env python3
"""Verify ZIP from a release in the calling repository, then extract for installer-only build."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
import zipfile
from stage import verify_zip, FOLDER

p = argparse.ArgumentParser()
p.add_argument('--zip', type=Path, required=True)
p.add_argument('--checksums', type=Path, required=True)
p.add_argument('--destination', type=Path, default=Path('work'))
p.add_argument('--output', type=Path, default=Path('dist'))
a = p.parse_args()
source_zip = a.zip.resolve(strict=True)
checksums = a.checksums.read_text(encoding='utf-8-sig').splitlines()
rows = [line.split(None,1) for line in checksums if line.strip()]
expected = [parts[0].lower() for parts in rows if len(parts)==2 and parts[1].strip(' *') == source_zip.name]
if len(expected) != 1 or len(expected[0]) != 64 or any(c not in '0123456789abcdef' for c in expected[0]):
    raise RuntimeError('Exact ZIP filename not found once in source SHA256SUMS.txt')
h = hashlib.sha256()
with source_zip.open('rb') as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(chunk)
actual = h.hexdigest()
if actual != expected[0]: raise RuntimeError('Downloaded source release ZIP does not match published SHA256')
verify_zip(source_zip)
root = a.destination.resolve() / FOLDER
if root.exists(): raise RuntimeError(f'Refusing overwrite of staging: {root}')
with zipfile.ZipFile(source_zip) as z:
    for entry in z.infolist():
        name = entry.filename
        if name.startswith('/') or '\\' in name or '..' in name.split('/') or ':' in name:
            raise RuntimeError('Unsafe ZIP member')
        # Reject ZIP symlink entries (Unix mode symbolic link)
        if ((entry.external_attr >> 16) & 0o170000) == 0o120000: raise RuntimeError('ZIP symlink disallowed')
    z.extractall(a.destination)
a.output.mkdir(parents=True, exist_ok=True)
shutil.copy2(source_zip, a.output/source_zip.name)
print(f'PACKAGING-ONLY: verified source ZIP {source_zip.name} SHA256={actual}, extracted for installer')
