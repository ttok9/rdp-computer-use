"""Inspect wheel/sdist/source ZIP metadata, member paths, and wheel RECORD hashes."""
import argparse
import base64
import csv
import hashlib
import io
import json
import re
import tarfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]


def inspect(path: Path) -> dict:
    expected_version = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version']
    if path.name.endswith(('.whl', '.zip')):
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError('archive CRC mismatch')
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError('duplicate archive paths')
            contents = {name: archive.read(name) for name in names if not name.endswith('/')}
    elif path.name.endswith('.tar.gz'):
        with tarfile.open(path) as archive:
            members = archive.getmembers()
            if any(not (member.isfile() or member.isdir()) for member in members):
                raise ValueError('archive contains non-regular members')
            if len({member.name for member in members}) != len(members):
                raise ValueError('duplicate archive paths')
            contents = {member.name: archive.extractfile(member).read() for member in members if member.isfile()}
    else:
        raise ValueError('unsupported archive type')
    for name, data in contents.items():
        member = PurePosixPath(name)
        if member.is_absolute() or '..' in member.parts or '\\' in name:
            raise ValueError('unsafe member path')
        if any(part in {'.git', '.venv', '__pycache__', 'screenshots', 'traces', 'secrets'} or (part.startswith('.env') and part != '.env.example') for part in member.parts):
            raise ValueError('private/runtime file in release')
        if not name.endswith('.png') and re.search(rb'/Use' + rb'rs/[^/\s]+/', data):
            raise ValueError('local user path in artifact')
    for required in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
        if not any(PurePosixPath(name).name == required for name in contents):
            raise ValueError('missing license notice')
    if path.suffix == '.whl':
        metadata_paths = [name for name in contents if name.endswith('.dist-info/METADATA')]
        if len(metadata_paths) != 1:
            raise ValueError('expected one wheel metadata file')
        metadata = BytesParser().parsebytes(contents[metadata_paths[0]])
        if metadata['Version'] != expected_version or metadata['License-Expression'] != 'MIT':
            raise ValueError('package metadata does not match source')
        record_path = metadata_paths[0].replace('/METADATA', '/RECORD')
        records = list(csv.reader(io.StringIO(contents[record_path].decode())))
        if {row[0] for row in records} != set(contents) or len(records) != len(contents):
            raise ValueError('RECORD membership mismatch')
        for name, digest, size in records:
            if name == record_path:
                if digest or size:
                    raise ValueError('RECORD must not hash itself')
                continue
            calculated = base64.urlsafe_b64encode(hashlib.sha256(contents[name]).digest()).decode().rstrip('=')
            if digest != 'sha256=' + calculated or int(size) != len(contents[name]):
                raise ValueError('wheel RECORD digest mismatch')
    else:
        configurations = [data for name, data in contents.items() if name.endswith('/pyproject.toml')]
        if len(configurations) != 1 or tomllib.loads(configurations[0].decode())['project']['version'] != expected_version:
            raise ValueError('source archive version mismatch')
    return {'file': path.name, 'files': len(contents), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'status': 'passed'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('artifacts', nargs='+', type=Path)
    args = parser.parse_args()
    print(json.dumps([inspect(path) for path in args.artifacts], indent=2))
