#!/usr/bin/env python3
"""Offline handoff and refusal tests; no network or recipient fixtures."""
import contextlib
import copy
import io
from pathlib import Path
import random
import tempfile
import unittest
import rewardbundle as rb


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.request = rb.read(rb.rr.ROOT / 'example.json')
        self.metadata = rb.read(rb.DEFAULT_METADATA)
        self.report = rb.rs.allocate(self.request, self.metadata)
        self.bundle = rb.pack(self.request, self.report, self.metadata)

    def test_serialized_roundtrip(self):
        bundle = rb.rs.parse_json(rb.encoded(self.bundle))
        result = rb.verify(bundle, rb.rr.digest(self.bundle))
        self.assertEqual(result['budget_units'], '1000000000000000000')
        self.assertTrue(result['expected_digest_matched'])
        self.assertFalse(rb.verify(bundle)['expected_digest_matched'])

    def test_tampered_components(self):
        for field in ('request', 'metadata', 'report', 'receipt'):
            changed = copy.deepcopy(self.bundle)
            if field == 'request': changed[field]['budget'] = '2'
            elif field == 'metadata': changed[field]['block_number'] += 1
            elif field == 'report': changed[field]['allocations'][0]['units'] = '0'
            else: changed[field]['contributors'] = 3.0
            with self.subTest(field=field), self.assertRaises(rb.rs.Invalid):
                rb.verify(changed)

    def test_extra_fields_and_schemas(self):
        for changed in (None, [], {}, dict(self.bundle, paid=True),
                        dict(self.bundle, schema='unknown')):
            with self.assertRaises(rb.rs.Invalid): rb.verify(changed)

    def test_digest_refusals(self):
        for digest in ('0'*64, 'A'*64, 'abc', 1):
            with self.assertRaises(rb.rs.Invalid): rb.verify(self.bundle, digest)

    def test_consistent_replacement_needs_external_digest(self):
        request = dict(self.request, budget='2')
        replacement = rb.pack(request, rb.rs.allocate(request, self.metadata), self.metadata)
        self.assertEqual(rb.verify(replacement)['budget_units'], '2000000000000000000')
        with self.assertRaises(rb.rs.Invalid):
            rb.verify(replacement, rb.rr.digest(self.bundle))

    def test_json_order_whitespace_and_type(self):
        import json
        pretty = json.dumps(self.bundle, indent=2, sort_keys=True)
        self.assertEqual(rb.verify(rb.rs.parse_json(pretty)), rb.verify(self.bundle))
        altered = copy.deepcopy(self.bundle)
        altered['report']['rounding_units_distributed'] = 1.0
        with self.assertRaises(rb.rs.Invalid): rb.verify(altered)

    def test_duplicate_keys_nonfinite_and_deep_json(self):
        for raw in ('{"schema":1,"schema":2}', '{"a":NaN}', '['*1500+'0'+']'*1500):
            with self.assertRaises(rb.rs.Invalid): rb.parse(raw)

    def test_budget_extremes_and_zero_shares(self):
        for units in (1, rb.rs.UINT256_MAX):
            request = copy.deepcopy(self.request)
            request['budget'] = rb.rs.display_units(units, 18)
            request['contributors'][0]['weight'] = '0'
            bundle = rb.pack(request, rb.rs.allocate(request, self.metadata), self.metadata)
            self.assertEqual(int(rb.verify(bundle)['budget_units']), units)
            self.assertEqual(bundle['report']['allocations'][0]['units'], '0')

    def test_seeded_handoffs(self):
        rng = random.Random(73738)
        for _ in range(200):
            rows = [{'id': 'worker%d' % i, 'weight': str(rng.randrange(100))}
                    for i in range(rng.randint(1, 40))]
            rows[0]['weight'] = '1'
            units = rng.randint(1, 10**30)
            request = {'budget': rb.rs.display_units(units, 18), 'contributors': rows}
            bundle = rb.pack(request, rb.rs.allocate(request, self.metadata), self.metadata)
            received = rb.rs.parse_json(rb.encoded(bundle))
            rb.verify(received, rb.rr.digest(bundle))
            self.assertEqual(sum(int(r['units']) for r in received['report']['allocations']), units)

    def test_size_refused_before_write(self):
        changed = copy.deepcopy(self.bundle)
        changed['metadata']['note'] = 'x' * rb.MAX_BYTES
        with self.assertRaises(rb.rs.Invalid): rb.verify(changed)
        with self.assertRaises(rb.rs.Invalid):
            rb.pack(self.request, self.report, changed['metadata'])

    def test_cli_files_and_overwrite(self):
        scratch = Path('test/scratch')
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            root = Path(directory)
            for name, value in (('request', self.request), ('report', self.report)):
                rb.rs.write_json(value, root/name)
            target = root/'bundle'
            args = ['pack', '--request', str(root/'request'), '--report', str(root/'report'),
                    '--output', str(target)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(rb.main(args), 0)
                self.assertEqual(rb.main(['verify', '--bundle', str(target),
                                          '--sha256', rb.rr.digest(self.bundle)]), 0)
            before = target.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(rb.main(args), 2)
            self.assertEqual(before, target.read_bytes())
            large = root/'large'
            large.write_bytes(b' '*(rb.MAX_BYTES+1))
            with self.assertRaises(rb.rs.Invalid): rb.read(large)
            target.unlink()
            bad = copy.deepcopy(self.bundle)
            bad['receipt']['contributors'] = 100
            with self.assertRaises(rb.rs.Invalid): rb.write_new(bad, target)
            self.assertFalse(target.exists())

    def test_workspace_escape_refused(self):
        with self.assertRaises(rb.rs.Invalid): rb.read('../outside-workspace')
        with self.assertRaises(rb.rs.Invalid): rb.write_new(self.bundle, '../outside-workspace')


if __name__ == '__main__':
    unittest.main()
