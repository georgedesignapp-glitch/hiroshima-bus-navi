"""Verify and unpack the static site for GitHub Pages. No external requests."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile

root=Path.cwd()
manifest=json.loads((root/'site-manifest.json').read_text())
archive=root/'site.tar.gz'
digest=hashlib.sha256()
with archive.open('wb') as target:
    for part in manifest['parts']:
        name=part['file']
        if not re.fullmatch(r'site\.tar\.gz\.part\d{3}',name):raise ValueError('Invalid part name')
        path=root/name
        if path.stat().st_size!=part['bytes']:raise ValueError('Part size mismatch')
        check=hashlib.sha256()
        with path.open('rb') as source:
            while data:=source.read(1024*1024):check.update(data);digest.update(data);target.write(data)
        if check.hexdigest()!=part['sha256']:raise ValueError('Part checksum mismatch')
if digest.hexdigest()!=manifest['archive_sha256']:raise ValueError('Archive checksum mismatch')
with tarfile.open(archive,'r:gz') as tar:
    members=tar.getmembers()
    if len(members)>20000 or sum(m.size for m in members)>1_000_000_000:raise ValueError('Site exceeds preview limits')
    if any(not m.isfile() for m in members):raise ValueError('Only regular static files allowed')
    tar.extractall(root/'_site',filter='data')
print(f'Verified and unpacked {len(members)} static files')
