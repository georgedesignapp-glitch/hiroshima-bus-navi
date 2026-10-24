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
patch = root/'site-update.json'
if patch.exists():
    if patch.stat().st_size > 2_000_000: raise ValueError('Shell update too large')
    update = json.loads(patch.read_text(encoding='utf-8'))
    allowed = {'js/transit-app.js', 'pwa-boot.js', 'relay-client.js', 'sw.js'}
    files = update['files']
    if update['version'] != 1 or len(files) != len(allowed) or {f['path'] for f in files} != allowed:
        raise ValueError('Unexpected shell update files')
    for item in files:
        data = item['content'].encode('utf-8')
        if hashlib.sha256(data).hexdigest() != item['sha256']: raise ValueError('Shell checksum mismatch')
        (root/'_site'/item['path']).write_bytes(data)
    print(f'Applied {len(files)} verified shell updates')
