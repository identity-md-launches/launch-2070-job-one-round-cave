#!/usr/bin/env python3
"""Verify analyzer selection and refusal before analysis, including directories."""
import copy
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib
import api_bundle as bundle
from contains_demo import documents
from tuple_demo import archive
from key_demo import insert_gap


def with_directory(document, method=zipfile.ZIP_STORED, stream=None):
    """Approved API plus a directory whose stream may lie about empty output."""
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, 'w', compression=method) as writer:
        writer.writestr('docs/openapi.json', json.dumps(document))
        writer.writestr('empty/', b'')
    raw = bytearray(memory.getvalue())
    with zipfile.ZipFile(io.BytesIO(raw)) as reader:
        info = reader.getinfo('empty/')
        local, central = info.header_offset, reader.start_dir
        start = local + 30 + len(info.filename.encode())
        end = start + info.compress_size
    first_name, first_extra, first_comment = struct.unpack_from('<HHH', raw, central+28)
    entry = central + 46 + first_name + first_extra + first_comment
    if stream is not None:
        delta = len(stream) - (end-start)
        raw[start:end] = stream
        entry += delta
        struct.pack_into('<I', raw, len(raw)-22+16, central+delta)
        struct.pack_into('<III', raw, local+14, 0, len(stream), 0)
        struct.pack_into('<III', raw, entry+16, 0, len(stream), 0)
    return raw, local, entry


class ContainsBundleTests(unittest.TestCase):
    def setUp(self):
        scratch = Path('test/scratch').resolve()
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='contains-tests-', dir=scratch)
        self.root = Path(self.temp.name)
        _, self.old, self.new = documents()

    def tearDown(self):
        self.temp.cleanup()

    def pair(self, old=None, new=None):
        a, b = self.root/'old.zip', self.root/'new.zip'
        ah = archive(a, self.old if old is None else old)
        bh = archive(b, self.new if new is None else new)
        return a, b, dict(member='docs/openapi.json', old_sha256=ah,
                         new_sha256=bh, strict_layout=True)

    def test_reference_and_retained_findings(self):
        a, b, opts = self.pair()
        before = bundle.compare(a, b, tuples=True, **opts)
        after = bundle.compare(a, b, contains=True, **opts)
        self.assertEqual(before['status'], 'review_required')
        self.assertEqual(after['status'], 'breaking')
        self.assertEqual(len(after['contains_pairs']), 1)
        self.assertTrue(all(f in after['findings'] for f in before['findings']))
        self.assertTrue(any('/contains/enum' in f['location'] for f in after['findings']))
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), ['new.zip', 'old.zip'])

    def test_unchanged_real_capture(self):
        real = json.loads(Path(__file__).with_name('imd-openapi.json').read_bytes())
        a, b, opts = self.pair(real, real)
        result = bundle.compare(a, b, contains=True, **opts)
        self.assertEqual(result['status'], 'no_detected_breakage')
        self.assertEqual(result['operations_compared'], 5)
        self.assertEqual(result['contains_pairs'], [])

    def test_request_direction_and_mixed_policy_review(self):
        old, new = copy.deepcopy(self.new), copy.deepcopy(self.old)
        for doc in (old, new):
            op = doc['paths']['/requests/quote']['post']
            op['requestBody'] = op['responses']['200']
            op['responses'] = {}
            doc['paths'] = {'/requests/quote': {'post': op}}
        a, b, opts = self.pair(old, new)
        report = bundle.compare(a, b, contains=True, **opts)
        self.assertEqual(report['status'], 'breaking')
        self.assertEqual(report['contains_pairs'][0]['direction'], 'request')
        for doc in (old, new):
            doc['paths']['/requests/quote']['post']['requestBody']['content']['application/json']['schema']['maxContains'] = 2
        a, b, opts = self.pair(old, new)
        report = bundle.compare(a, b, contains=True, **opts)
        self.assertEqual(report['status'], 'review_required')
        self.assertIn('contains_combination_unchecked', {f['code'] for f in report['findings']})

    def test_digest_crc_and_layout_refusal_precede_analysis(self):
        a, b, opts = self.pair()
        with patch.object(bundle.zipseal, 'layout') as layout:
            with self.assertRaisesRegex(ValueError, 'approved digest'):
                bundle.compare(a, b, contains=True, **{**opts, 'old_sha256': '0'*64})
            layout.assert_not_called()
        for mutate in (insert_gap, lambda raw: raw.replace(b'inert payload', b'INERT PAYLOAD')):
            a, b, opts = self.pair()
            b.write_bytes(mutate(b.read_bytes()))
            with patch.object(bundle.containscheck, 'compare') as analyzer:
                with self.assertRaises((ValueError, zipfile.BadZipFile)):
                    bundle.compare(a, b, contains=True, **{**opts, 'new_sha256': None})
                analyzer.assert_not_called()

    def test_valid_directories_all_analyzer_modes(self):
        for method in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raw, _, _ = with_directory(self.old, method)
            a = self.root/'dirs.zip'
            a.write_bytes(raw)
            for strict in (False, True):
                for options in ({}, {'tuples': True}, {'contains': True}):
                    result = bundle.compare(a, a, member='docs/openapi.json',
                        old_sha256=hashlib.sha256(raw).hexdigest(), strict_layout=strict, **options)
                    self.assertEqual(result['status'], 'no_detected_breakage')
                    for side in result['bundle_inputs'].values():
                        self.assertEqual(side['checked_directories'], ['empty'])
                        self.assertTrue(side['all_directories_checked'])

    def test_approved_corrupt_directory_never_reaches_analysis(self):
        cases = []
        for corruption in ('crc', 'name', 'signature'):
            raw, local, entry = with_directory(self.old)
            if corruption == 'crc':
                struct.pack_into('<I', raw, local+14, 1)
                struct.pack_into('<I', raw, entry+16, 1)
            elif corruption == 'name': raw[local+30] = ord('X')
            else: raw[local:local+4] = b'FAIL'
            cases.append(raw)
        for method, stream in ((zipfile.ZIP_STORED, b'x'),
                (zipfile.ZIP_DEFLATED, b'\x73\x04\x00'),  # produces A
                (zipfile.ZIP_DEFLATED, b'\x03'),          # truncated
                (zipfile.ZIP_DEFLATED, b'\x03\x00tail')):
            cases.append(with_directory(self.old, method, stream)[0])
        a = self.root/'corrupt.zip'
        for raw in cases:
            a.write_bytes(raw)
            digest = hashlib.sha256(raw).hexdigest()
            for strict in (False, True):
                with self.subTest(strict=strict, digest=digest), patch.object(bundle.containscheck, 'compare') as analyzer:
                    with self.assertRaises((ValueError, zipfile.BadZipFile, zlib.error)):
                        bundle.compare(a, a, member='docs/openapi.json', contains=True,
                                       old_sha256=digest, strict_layout=strict)
                    analyzer.assert_not_called()

    def test_directory_checks_observe_cancellation(self):
        raw, _, _ = with_directory(self.old, zipfile.ZIP_DEFLATED)
        a = self.root/'dirs.zip'; a.write_bytes(raw)
        entered = False
        original = bundle.safezip.check_directory
        def check(*args):
            nonlocal entered
            entered = True
            return original(*args)
        with patch.object(bundle.safezip, 'check_directory', check):
            with self.assertRaisesRegex(ValueError, 'cancelled'):
                bundle.compare(a, a, member='docs/openapi.json', contains=True,
                               cancelled=lambda: entered)
        self.assertTrue(entered)

    def test_remote_reference_pair_budget_and_flag_refuse(self):
        old = copy.deepcopy(self.old)
        old['components']['schemas']['MatchedState'] = {'$ref': 'https://example.invalid/schema'}
        a, b, opts = self.pair(old, old)
        with self.assertRaises(ValueError): bundle.compare(a, b, contains=True, **opts)
        a, b, opts = self.pair()
        with patch.object(bundle.containscheck, 'MAX_CONTAINS_PAIRS', 0):
            with self.assertRaisesRegex(ValueError, 'contains pair limit'):
                bundle.compare(a, b, contains=True, **opts)
        for value in (1, None, 'true'):
            with self.assertRaisesRegex(ValueError, 'booleans'):
                bundle.compare(a, b, contains=value, **opts)

    def test_cli_exits_precedence_and_determinism(self):
        review = copy.deepcopy(self.old)
        review['components']['schemas']['MatchedState']['pattern'] = '^p'
        for document, code in ((self.old, 0), (self.new, 1), ({}, 2), (review, 3)):
            a, b, opts = self.pair(self.old, document)
            done = subprocess.run([sys.executable, '-B', bundle.__file__, str(a), str(b),
                '--contains', '--tuples', '--keys', '--strict-layout',
                '--member', opts['member'], '--old-sha256', opts['old_sha256'],
                '--new-sha256', opts['new_sha256']], capture_output=True, text=True, timeout=20)
            self.assertEqual(done.returncode, code, done.stdout+done.stderr)
            if code != 2:
                self.assertTrue(json.loads(done.stdout)['extension'].startswith('containscheck-v1'))
        a, b, opts = self.pair()
        self.assertEqual(bundle.compare(a,b,contains=True,**opts), bundle.compare(a,b,contains=True,**opts))


if __name__ == '__main__':
    unittest.main(verbosity=2)
