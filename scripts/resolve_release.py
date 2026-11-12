#!/usr/bin/env python3
"""Resolve public GitHub Desktop stable release with numeric semantic ordering."""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

RX = re.compile(r'^release-(\d+)\.(\d+)\.(\d+)$')

def get_json(url: str) -> object:
    hdr = {'Accept': 'application/vnd.github+json', 'User-Agent': 'GitHubDesktop-PortableApps-Builder-Kit',
           'X-GitHub-Api-Version': '2022-11-28'}
    token = os.environ.get('GITHUB_TOKEN')
    if token: hdr['Authorization'] = f'Bearer {token}'
    request = urllib.request.Request(url, headers=hdr)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as e:
        if e.code == 404: raise RuntimeError(f'Release/API endpoint not found (404): {url}') from e
        if e.code in (401, 403, 429): raise RuntimeError(f'GitHub API authentication or rate limit (HTTP {e.code}): {url}') from e
        raise RuntimeError(f'GitHub API HTTP {e.code}: {url}') from e

def resolve(version: str, adapter_max: str = '3.6.10'):
    if version != 'latest':
        ver = version.removeprefix('release-')
        if not re.fullmatch(r'\d+\.\d+\.\d+', ver): raise ValueError('Explicit version must be stable X.Y.Z')
        tag = f'release-{ver}'
        record = get_json(f'https://api.github.com/repos/desktop/desktop/releases/tags/{tag}')
        if record.get('draft') or record.get('prerelease') or record.get('tag_name') != tag:
            raise RuntimeError(f'Explicit release is not a published stable tag: {tag}')
        return {'version': ver, 'tag': tag, 'release_url': record.get('html_url')}
    max_tuple = tuple(map(int, adapter_max.split('.')))
    candidates = []
    for page in range(1, 6):
        releases = get_json(f'https://api.github.com/repos/desktop/desktop/releases?per_page=100&page={page}')
        if not isinstance(releases, list): raise RuntimeError('Expected GitHub releases API list')
        for r in releases:
            tag = r.get('tag_name', '')
            m = RX.fullmatch(tag)
            if m and not r.get('draft') and not r.get('prerelease'):
                parts = tuple(map(int, m.groups()))
                if parts <= max_tuple:
                    candidates.append((parts, r))
        if len(releases) < 100: break
    if not candidates: raise RuntimeError('No stable GitHub Desktop releases found')
    k, r = max(candidates, key=lambda pair: pair[0])
    return {'version': '.'.join(map(str, k)), 'tag': r['tag_name'], 'release_url': r.get('html_url')}

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--version', default='latest'); p.add_argument('--adapter-max', default='3.6.10'); p.add_argument('--output', type=Path, required=True)
    a = p.parse_args(); record = resolve(a.version, a.adapter_max)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record))
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
            for key in ('version','tag'): f.write(f'{key}={record[key]}\n')
