"""Verify and unpack the static site for GitHub Pages. No external requests."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tarfile
import zipfile

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
    files = update['files']
    if update['version']==1:
        allowed = {'js/transit-app.js', 'pwa-boot.js', 'relay-client.js', 'sw.js'}
        if len(files) != len(allowed) or {f['path'] for f in files} != allowed:raise ValueError('Unexpected shell update files')
        for item in files:
            data = item['content'].encode('utf-8')
            if hashlib.sha256(data).hexdigest() != item['sha256']: raise ValueError('Shell checksum mismatch')
            (root/'_site'/item['path']).write_bytes(data)
    elif update['version']==2:
        if update['archive']!='site-update.zip':raise ValueError('Unexpected update archive')
        archive=root/'site-update.zip'
        if archive.stat().st_size>30*1024*1024:raise ValueError('Update archive too large')
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=update['archive_sha256']:raise ValueError('Update archive checksum mismatch')
        top={'index.html','manifest.webmanifest','data-worker.js','api-worker.js','pwa-boot.js','pwa.css','gtfs-rt.js','rt-model.js','relay-client.js','trip-support.js','operations-descriptor.js','sw.js'}
        def safe(name):
            return name in top or bool(re.fullmatch(r'(?:js|css|images/brand|vendor/images|vendor|map-styles)/[A-Za-z0-9_.-]+',name)) or bool(re.fullmatch(r'data/[a-f0-9]{64}\.json',name))
        names=[f['path'] for f in files]
        if len(names)>3000 or len(names)!=len(set(names)) or not all(safe(n) for n in names):raise ValueError('Unexpected update paths')
        with zipfile.ZipFile(archive) as z:
            if len(z.infolist())!=len(names) or set(z.namelist())!=set(names) or sum(i.file_size for i in z.infolist())>64*1024*1024:raise ValueError('Unexpected update contents')
            for item in files:
                data=z.read(item['path'])
                if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:raise ValueError('Update entry checksum mismatch')
                path=root/'_site'/item['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    else:raise ValueError('Unsupported update version')
    print(f'Applied {len(files)} verified shell updates')
