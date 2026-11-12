#!/usr/bin/env python3
"""Safe no-op for an already-published, publisher-managed identical source/build release."""
from __future__ import annotations
import argparse
import json
import os
import urllib.request
import urllib.error

MARKER = '<!-- portable-release-publisher:managed:v2 -->'
p = argparse.ArgumentParser()
p.add_argument('--tag', required=True)
a = p.parse_args()
repo = os.environ.get('GITHUB_REPOSITORY', '')
if '/' not in repo: raise RuntimeError('Cannot identify calling builder repository')
url = f'https://api.github.com/repos/{repo}/releases/tags/{a.tag}'
headers = {'Accept': 'application/vnd.github+json', 'User-Agent': 'GitHubDesktop-PortableApps-Builder-Kit'}
if os.environ.get('GITHUB_TOKEN'): headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
req = urllib.request.Request(url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=25) as r: record = json.load(r)
except urllib.error.HTTPError as e:
    if e.code == 404: record = None
    else: raise RuntimeError(f'Existing release check failed (HTTP {e.code}), NOT treating as missing') from e
if record:
    if record.get('draft'): raise RuntimeError('Identical tag exists as draft; inspect before retrying')
    if MARKER not in record.get('body',''): raise RuntimeError('Identical tag belongs to a different/manual release')
    names = {x.get('name') for x in record.get('assets', [])}
    if not any(str(x).endswith('.zip') for x in names) or not any(str(x).endswith('.paf.exe') for x in names):
        raise RuntimeError('Matching tag incomplete: refusing to silently skip or overwrite')
    skip = True
else: skip = False
print(f'Identical already-published release: {"SKIP" if skip else "BUILD"}')
if os.environ.get('GITHUB_OUTPUT'):
    with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:
        f.write(f'skip={str(skip).lower()}\n')
