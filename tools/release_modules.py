#!/usr/bin/env python3
"""Build reproducible, independently downloadable module ZIPs and an offline registry."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

import build_registry

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = 'sherhn/Light-Modules'

def digest(data):
    return hashlib.sha256(data).hexdigest()

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8', newline='\n')

def archive(files):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as output:
        for name, data in sorted(files):
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
                raise ValueError(f'Unsafe package path: {name}')
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            output.writestr(info, data)
    return stream.getvalue()

def verify_registry(directory):
    index = json.loads((directory / 'index.json').read_text(encoding='utf-8'))
    ids = set()
    for module in index['modules']:
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', module['id']) or module['id'] in ids:
            raise ValueError('Invalid or duplicate module id')
        ids.add(module['id'])
        if module['path'] != 'modules/' + module['id']:
            raise ValueError('Invalid module path')
        folder = directory / module['path']
        names = {f['name'] for f in module['files']}
        if not {'module.json', 'LICENSE', 'THIRD_PARTY_NOTICES.md'} <= names:
            raise ValueError('Missing manifest or legal materials')
        if names != {p.name for p in folder.iterdir() if p.is_file()}:
            raise ValueError('Index does not cover all module files')
        for item in module['files']:
            if PurePosixPath(item['name']).name != item['name'] or '\\' in item['name']:
                raise ValueError('Invalid file name')
            data = (folder / item['name']).read_bytes()
            if len(data) != item['size'] or digest(data) != item['sha256']:
                raise ValueError('Module checksum mismatch: ' + module['id'])
        manifest = json.loads((folder / 'module.json').read_text(encoding='utf-8'))
        if any(manifest[k] != module[k] for k in ['id', 'name', 'version']):
            raise ValueError('Manifest does not match index')
    return index

def build():
    version = (ROOT / 'VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Invalid catalog version')
    build_registry.main([])
    registry = ROOT / 'registry'
    index = verify_registry(registry)
    index['version'] = 2
    index['catalog_version'] = version
    destination = ROOT / 'dist'
    destination.mkdir(exist_ok=True)
    base = f'https://github.com/{REPOSITORY}/releases/download/v{version}'
    assets = []
    for module in index['modules']:
        name = f"{module['id']}-{module['version']}.zip"
        data = archive([(f['name'], (registry / module['path'] / f['name']).read_bytes()) for f in module['files']])
        (destination / name).write_bytes(data)
        module['min_ide'] = '1.1.0'
        module['archive'] = {'url': f'{base}/{name}', 'size': len(data), 'sha256': digest(data)}
        assets.append({'name': name, 'sha256': digest(data), 'size': len(data)})
    write_json(registry / 'index.json', index)
    write_json(destination / 'index.json', index)
    verify_registry(registry)
    name = f'light-modules-{version}.zip'
    data = archive([('registry/' + p.relative_to(registry).as_posix(), p.read_bytes()) for p in registry.rglob('*') if p.is_file()])
    (destination / name).write_bytes(data)
    assets.append({'name': name, 'sha256': digest(data), 'size': len(data)})
    write_json(destination / 'release.json', {'version': version, 'repository': REPOSITORY, 'assets': assets})
    files = sorted(p for p in destination.iterdir() if p.is_file() and p.name != 'SHA256SUMS.txt')
    (destination / 'SHA256SUMS.txt').write_text(''.join(f'{digest(p.read_bytes())}  {p.name}\n' for p in files), encoding='utf-8', newline='\n')
    print(f'Built {len(index["modules"])} modules and pinned offline snapshot {name} ({digest(data)})')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['build', 'verify'])
    options = parser.parse_args()
    if options.command == 'build':
        build()
    else:
        print(f'Verified {len(verify_registry(ROOT / "registry")["modules"])} modules')
