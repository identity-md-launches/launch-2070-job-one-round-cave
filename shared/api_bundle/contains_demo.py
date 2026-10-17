#!/usr/bin/env python3
"""Check a referenced matching-item rule inside approved ZIP snapshots."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import api_bundle
from tuple_demo import archive


def documents():
    capture = Path(__file__).with_name('imd-openapi.json').read_bytes()
    old = json.loads(capture)
    old['openapi'] = '3.1.0'
    old.setdefault('components', {}).setdefault('schemas', {})['MatchedState'] = {
        'type': 'string', 'enum': ['pending', 'done']}
    old['paths']['/requests/quote']['post']['responses'] = {
        '200': {'description': 'Hypothetical matched result', 'content': {
            'application/json': {'schema': {'type': 'array',
                'contains': {'$ref': '#/components/schemas/MatchedState'}}}}}}
    new = copy.deepcopy(old)
    new['components']['schemas']['MatchedState']['enum'].append('retry')
    return capture, old, new


def demo():
    capture, old, new = documents()
    scratch = Path('test/scratch')
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='contains-bundle-', dir=scratch) as name:
        root = Path(name)
        a, b = root/'old.zip', root/'new.zip'
        ah, bh = archive(a, old), archive(b, new)
        options = dict(member='docs/openapi.json', old_sha256=ah,
                       new_sha256=bh, strict_layout=True)
        prior = api_bundle.compare(a, b, tuples=True, **options)
        changed = api_bundle.compare(a, b, contains=True, **options)
        same = api_bundle.compare(a, a, contains=True,
                                 **{**options, 'new_sha256': ah})
        assert prior['status'] == 'review_required'
        assert changed['status'] == 'breaking'
        assert any(f['code'] == 'schema_enum_incompatible' and '/contains/' in f['location']
                   for f in changed['findings'])
        assert all(f in changed['findings'] for f in prior['findings'])
        assert same['status'] == 'no_detected_breakage'
        assert sorted(p.name for p in root.iterdir()) == ['new.zip', 'old.zip']
        return dict(baseline_source='https://api.imd.fun/openapi.json',
            capture_sha256=hashlib.sha256(capture).hexdigest(),
            illustration='Saved real operation with a hypothetical OpenAPI 3.1 contains rule; no observed service change.',
            previous_status=prior['status'], changed_status=changed['status'],
            unchanged_status=same['status'], matching_regions=len(changed['contains_pairs']),
            findings=changed['findings'],
            inputs=changed['bundle_inputs'], extracted=False, network_used=False)


if __name__ == '__main__':
    print(json.dumps(demo(), indent=2))
