"""Restore split files after git lfs pull, verifying every part and final SHA-256."""
import hashlib
import json
import os
from pathlib import Path

root = Path(__file__).resolve().parent
for item in json.loads((root / 'large-files-manifest.json').read_text(encoding='utf-8')):
    target = (root / item['path']).resolve()
    if not target.is_relative_to(root):
        raise RuntimeError('Manifest path escapes repository')
    if target.exists():
        raise RuntimeError(f'Refusing to overwrite existing file: {target}')
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + '.restoring')
    total = hashlib.sha256()
    size = 0
    try:
        with temp.open('xb') as out:
            for part in item['parts']:
                source = (root / part['path']).resolve()
                if not source.is_relative_to(root):
                    raise RuntimeError('Part path escapes repository')
                h = hashlib.sha256()
                count = 0
                with source.open('rb') as inp:
                    while block := inp.read(8*1024**2):
                        h.update(block)
                        total.update(block)
                        out.write(block)
                        count += len(block)
                if count != part['bytes'] or h.hexdigest() != part['sha256']:
                    raise RuntimeError(f'Part verification failed: {source}. Run git lfs pull first.')
                size += count
        if size != item['bytes'] or total.hexdigest() != item['sha256']:
            raise RuntimeError(f'File verification failed: {target}')
        os.rename(temp, target)
        print(f'Restored and verified: {item["path"]}')
    except BaseException:
        if temp.exists():
            temp.unlink()
        raise
