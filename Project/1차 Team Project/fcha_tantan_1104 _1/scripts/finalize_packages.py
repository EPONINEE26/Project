"""Refresh small source entries while preserving compressed DB/data blocks."""
import copy
from pathlib import Path
import zipfile

from package_project import ROOT, variant_content


def finalize(archive, variant):
    replacements = {}
    paths = [ROOT / 'scripts/package_project.py', ROOT / 'scripts/finalize_packages.py', ROOT / 'scripts/verify_community_package.py',
             ROOT / 'community/tests.py', ROOT / 'COMMUNITY_FIX_20261104.md',
             ROOT / 'brands/templates/base.html']
    paths += list((ROOT / 'community/templates/community').rglob('*.html'))
    for path in paths:
        relative = path.relative_to(ROOT)
        overlay = variant_content(relative, variant)
        replacements['fcha_tantan_windows/' + relative.as_posix()] = overlay if overlay is not None else path.read_bytes()
    temporary = archive.with_suffix('.refresh.zip')
    with zipfile.ZipFile(archive) as source, zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as target:
        entries = source.infolist()
        for index, entry in enumerate(entries):
            if entry.filename in replacements:
                target.writestr(entry.filename, replacements.pop(entry.filename))
                continue
            end = entries[index + 1].header_offset if index + 1 < len(entries) else source.start_dir
            length = end - entry.header_offset
            source.fp.seek(entry.header_offset)
            copied = copy.copy(entry)
            copied.header_offset = target.fp.tell()
            while length:
                block = source.fp.read(min(length, 8 * 1024 * 1024))
                if not block:
                    raise RuntimeError('Unexpected end of ZIP')
                target.fp.write(block)
                length -= len(block)
            target.filelist.append(copied)
            target.NameToInfo[copied.filename] = copied
            target.start_dir = target.fp.tell()
            target._didModify = True
        for name, content in replacements.items():
            target.writestr(name, content)
    with zipfile.ZipFile(temporary) as bundle:
        assert len(bundle.namelist()) == len(set(bundle.namelist())), 'Duplicate entries'
        assert bundle.testzip() is None, 'CRC failure'
    temporary.replace(archive)
    print('FINAL_ZIP_OK:', archive.name, archive.stat().st_size, flush=True)


if __name__ == '__main__':
    import sys
    finalize(Path(sys.argv[1]).resolve(), sys.argv[2])
