#!/usr/bin/env python3
"""Check output bytes, preserved pixels, complete gallery and untouched lines."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from check_delivery_35 import Gallery, GROUPS, jpeg, png, sha
from check_delivery_39 import export_budget

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads((ROOT/path).read_text())


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    wall = ROOT/'artifacts/gathering/wall-v21.png'
    previous = ROOT/'artifacts/gathering/wall-v20.png'
    record = read('dist/gathering/40.json')
    assert set(record) == {'name', 'image', 'attributes'}
    attrs = {a['trait_type']: a['value'] for a in record['attributes']}
    assert len(record['attributes']) == 6
    assert set(attrs) == {'Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing'}
    assert (attrs['Cave'], attrs['Wall'], attrs['Number'], attrs['One thing']) == ('Lava', 'Gathering', 40, 'Gathering')
    assert type(attrs['Number']) is int
    assert record['image'] == 'https://api.imd.fun/artifacts/'+sha(wall.read_bytes())
    assert not git('ls-files', '--', 'artifacts/gathering/wall-v21.png')
    assert (ROOT/'artifacts/gathering/wall.png').read_bytes() == wall.read_bytes()
    assert read('dist/gathering/39.json')['image'].endswith(sha(previous.read_bytes()))
    dimensions, pixels = png(wall)
    old_dimensions, old = png(previous)
    assert dimensions == old_dimensions == [1254, 1254]
    preservation = read('gathering/preservation-40.json')
    assert preservation['previous_sha256'] == sha(previous.read_bytes())
    assert preservation['wall_sha256'] == sha(wall.read_bytes())
    x, y, w, h = preservation['mark_rectangle']
    changed = outside = 0
    for row in range(dimensions[1]):
        for col in range(dimensions[0]):
            at = (row*dimensions[0]+col)*3
            if pixels[at:at+3] != old[at:at+3]:
                changed += 1
                outside += not (x <= col < x+w and y <= row < y+h)
    assert changed == preservation['changed_pixels'] == 5209
    assert outside == preservation['pixels_changed_outside'] == 0
    assert jpeg(ROOT/'dist/gathering/40.jpg') == [512, 512]
    assert read('dist/goals.json') == [
        {'line': n, 'goal': (ROOT/f'line-{n}/GOAL.md').read_text().strip()}
        for n in range(1, 5)]
    parser = Gallery()
    parser.feed((ROOT/'dist/index.html').read_text())
    assert parser.sections == GROUPS
    expected = []
    painted = placeholders = 0
    for folder in GROUPS:
        for path in sorted((ROOT/'dist'/folder).glob('[0-9][0-9].json'), reverse=True):
            item = json.loads(path.read_text())
            expected.append(folder+'/'+path.name)
            assert re.fullmatch(r'https://api\.imd\.fun/artifacts/[0-9a-f]{64}', item['image'])
            if item['name'] == 'Not painted yet':
                placeholders += 1
                assert not path.with_suffix('.jpg').exists()
            else:
                painted += 1
                assert path.with_suffix('.jpg').is_file()
        actual = [p for p in parser.records if p.startswith(folder+'/') and
                  read('dist/'+p)['name'] != 'Not painted yet']
        assert actual == sorted(actual, reverse=True)
    assert sorted(parser.records) == sorted(expected)
    for target, item in read('shared/api_bundle/SOURCES.json').items():
        assert sha((ROOT/'shared/api_bundle'/target).read_bytes()) == item['sha256']
        assert sha((ROOT/item['source']).read_bytes()) == item['source_sha256']
    audit = read('gathering/audit-lines-40.json')
    assert len(audit['commands']) == 146 and all(r['passed'] for r in audit['commands'])
    assert sum(r['unittest_cases'] for r in audit['commands']) == 966
    shared = read('gathering/shared-check-results-40.json')
    assert shared['passed'] and shared['tests'] == 122 and shared['demos'] == 10
    assert len(shared['in_place']) == len(shared['standalone']) == 19
    live = read('gathering/public-trial-40.json')
    assert live['http_status'] == 200 and live['operations'] == 5
    assert live['status'] == 'no_detected_breakage' and not live['described_operations_invoked']
    assert all(s['checked_directories'] == ['empty'] and s['all_directories_checked']
               for s in live['inputs'].values())
    baseline = {r['path']: r['sha256'] for r in read('gathering/line-integrity-40.json')}
    current = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for n in range(1, 5)
               for p in (ROOT/f'line-{n}').rglob('*') if p.is_file()}
    assert baseline == current, 'line files changed'
    review = read('gathering/review-40.json')
    assert review['wall_sha256'] == sha(wall.read_bytes())
    assert review['visual_requirements_unmet'] == []
    assert (ROOT/'gathering/COINS.md').read_text().startswith('none\n')
    compression = read('gathering/preview-compression-40.json')
    assert len(compression['previews']) == 19
    for item in compression['previews']:
        path = ROOT/item['path']
        assert sha(path.read_bytes()) == item['after_sha256']
        assert path.stat().st_size == item['after_bytes']
        assert sha((ROOT/item['source']).read_bytes()) == item['source_sha256']
        assert jpeg(path) == [512, 512]
    paths = set((git('diff', '--name-only', '-z', 'HEAD') +
                 git('ls-files', '--others', '--exclude-standard', '-z')).decode().split('\0'))-{''}
    for name in paths:
        assert name.startswith(('gathering/', 'shared/', 'dist/', 'artifacts/gathering/', 'test/scratch/')), name
        assert not re.match(r'(?:dist/)?line-[1-4]/', name), name
        path = ROOT/name
        if path.is_file() and not name.startswith(('artifacts/', 'test/scratch/')):
            assert path.stat().st_size <= 100000, name
    budget = export_budget()
    assert budget['margin'] > 0, budget
    result = dict(passed=True, wall_sha256=sha(wall.read_bytes()), png_dimensions=dimensions,
        png_format='RGB PNG', png_bytes=wall.stat().st_size, jpeg_dimensions=[512,512],
        jpeg_format='JPEG', jpeg_bytes=(ROOT/'dist/gathering/40.jpg').stat().st_size,
        records=len(expected), painted=painted, placeholders=placeholders,
        changed_pixels=changed, pixels_changed_outside=outside,
        line_files_unchanged=len(current), line_commands=146, line_unittest_cases=966,
        shared_tests_each=122, shared_demos_each=10, previews_reencoded=19,
        preview_bytes_saved=compression['saved_bytes'], export=budget,
        unmet_visual_requirements=[], visual_review='Local manual inspection; byte checks do not certify visual quality.')
    (ROOT/'gathering/delivery-check-40.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
