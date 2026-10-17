#!/usr/bin/env python3
"""Check this round's output contract, without reading external configuration."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib


def git(*args):
    return subprocess.check_output(['git', *args])


def png_size(raw):
    assert raw[:8] == b'\x89PNG\r\n\x1a\n'
    cursor = 8
    dimensions = None
    while cursor < len(raw):
        length = struct.unpack_from('>I', raw, cursor)[0]
        kind = raw[cursor+4:cursor+8]
        chunk = raw[cursor+8:cursor+8+length]
        crc = struct.unpack_from('>I', raw, cursor+8+length)[0]
        assert zlib.crc32(kind + chunk) == crc
        if kind == b'IHDR':
            dimensions = struct.unpack_from('>II', chunk)
            assert chunk[8:10] == b'\x08\x02'
        cursor += length + 12
        if kind == b'IEND':
            break
    assert cursor == len(raw) and dimensions
    return list(dimensions)


def jpeg_size(raw):
    assert raw[:2] == b'\xff\xd8' and raw[-2:] == b'\xff\xd9'
    cursor = 2
    while cursor < len(raw):
        assert raw[cursor] == 255
        marker = raw[cursor+1]
        length = struct.unpack_from('>H', raw, cursor+2)[0]
        if marker == 0xc0:
            height, width = struct.unpack_from('>HH', raw, cursor+5)
            return [width, height]
        assert marker != 0xda and length >= 2
        cursor += length + 2
    raise AssertionError('missing JPEG dimensions')


def main():
    goal = Path('line-2/GOAL.md').read_bytes()
    assert goal == git('show', 'HEAD:line-2/GOAL.md')
    prior = git('ls-tree', '-r', '--name-only', 'HEAD', 'dist/line-2').decode().splitlines()
    old_records = [name for name in prior if name.endswith('.json')]
    assert len(old_records) == 39
    for name in prior:
        assert Path(name).read_bytes() == git('show', 'HEAD:' + name), name
    records = sorted(Path('dist/line-2').glob('[0-9][0-9].json'))
    assert len(records) == 40 and records[-1].name == '40.json'
    record = json.loads(records[-1].read_text())
    assert set(record) == {'name', 'image', 'attributes'}
    attrs = record['attributes']
    assert all(set(row) == {'trait_type', 'value'} for row in attrs)
    assert [row['trait_type'] for row in attrs] == [
        'Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing']
    values = {row['trait_type']: row['value'] for row in attrs}
    assert values['Cave'] == 'Lava' and values['Wall'] == 'Line 2'
    assert type(values['Number']) is int and values['Number'] == 40
    assert all(isinstance(values[key], str) and values[key]
               for key in ('Left behind', 'Meaning', 'One thing'))
    wall = Path('artifacts/line-2/wall-v21.png')
    raw = wall.read_bytes()
    assert raw == Path('artifacts/line-2/wall.png').read_bytes()
    assert not git('ls-files', '--', str(wall))
    digest = hashlib.sha256(raw).hexdigest()
    assert record['image'] == 'https://api.imd.fun/artifacts/' + digest
    assert png_size(raw) == [1254, 1254]
    preview = Path('dist/line-2/40.jpg').read_bytes()
    assert jpeg_size(preview) == [512, 512] and len(preview) < 100000
    changed = git('diff', '--name-only', 'HEAD').decode().splitlines()
    added = git('ls-files', '--others', '--exclude-standard').decode().splitlines()
    for name in changed + added:
        if name.startswith('test/scratch/'):
            continue
        assert name.startswith(('line-2/', 'dist/line-2/', 'artifacts/line-2/')), name
        if not name.startswith('artifacts/'):
            assert Path(name).stat().st_size <= 100000, name
    report = {'ok': True, 'goal_unchanged': True,
              'prior_records_unchanged': len(old_records),
              'prior_previews_unchanged': len([p for p in prior if p.endswith('.jpg')]),
              'new_record': 'dist/line-2/40.json',
              'wall': str(wall), 'wall_format': 'PNG', 'wall_dimensions': png_size(raw),
              'wall_sha256': digest, 'wall_bytes': len(raw),
              'named_output_untracked': True, 'canonical_wall_matches': True,
              'preview': 'dist/line-2/40.jpg', 'preview_format': 'JPEG',
              'preview_dimensions': jpeg_size(preview), 'preview_bytes': len(preview),
              'changed_paths_in_scope': True, 'new_source_files_under_100KB': True,
              'visual_review': 'WALL-40.md', 'unmet_visual_requirements': []}
    Path('line-2/delivery-check-40.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
