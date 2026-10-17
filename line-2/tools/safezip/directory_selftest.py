#!/usr/bin/env python3
"""Regression checks for directory records, using disposable workspace files."""
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile
import zlib

import safezip


def directory_zip(method=zipfile.ZIP_STORED, payload=b'', stream=None):
    """A good file followed by a directory, optionally lying about its payload."""
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, 'w', compression=method) as writer:
        writer.writestr('good.txt', b'already staged')
        writer.writestr('empty/', payload)
    raw = bytearray(memory.getvalue())
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        info = archive.getinfo('empty/')
        local = info.header_offset
        start = local + 30 + len(info.filename.encode()) + len(info.extra)
        end = start + info.compress_size
        central = archive.start_dir
    first_name, first_extra, first_comment = struct.unpack_from('<HHH', raw, central + 28)
    entry = central + 46 + first_name + first_extra + first_comment
    if stream is None:
        stream = bytes(raw[start:end])
    delta = len(stream) - (end - start)
    raw[start:end] = stream
    entry += delta
    eocd = len(raw) - 22
    struct.pack_into('<I', raw, eocd + 16, central + delta)
    # The directory declares zero output and CRC even if its bytes say otherwise.
    struct.pack_into('<III', raw, local + 14, 0, len(stream), 0)
    struct.pack_into('<III', raw, entry + 16, 0, len(stream), 0)
    return raw, local, entry


class DirectoryTests(unittest.TestCase):
    def setUp(self):
        scratch = Path('test/scratch').resolve()
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix='safezip-directory-', dir=scratch)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'input.zip'
        self.output = self.root / 'output'

    def tearDown(self):
        self.temp.cleanup()

    def refused(self, raw, **options):
        self.archive.write_bytes(raw)
        for output in (None, self.output):
            with self.subTest(extract=output is not None):
                with self.assertRaises((safezip.Rejected, zipfile.BadZipFile,
                                        zlib.error, NotImplementedError)):
                    safezip.process(self.archive, output, **options)
                self.assertFalse(self.output.exists())
                self.assertEqual(list(self.root.glob('.safezip-*')), [])

    def test_valid_stored_and_deflated_empty_directories(self):
        for method in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raw, _, _ = directory_zip(method)
            self.archive.write_bytes(raw)
            output = self.root / str(method)
            report = safezip.process(self.archive, output)
            self.assertTrue(report['content_checked'])
            self.assertEqual((output / 'good.txt').read_bytes(), b'already staged')
            self.assertEqual(list((output / 'empty').iterdir()), [])
            self.assertEqual(report['entries'][-1],
                             {'path': 'empty', 'kind': 'directory', 'bytes': 0})

    def test_unicode_explicit_parent_after_child(self):
        with zipfile.ZipFile(self.archive, 'w', compression=zipfile.ZIP_DEFLATED) as writer:
            writer.writestr('caf\u00e9/child', b'kept')
            writer.writestr('caf\u00e9/', b'')
        safezip.process(self.archive, self.output, nodes=2)
        self.assertEqual((self.output / 'caf\u00e9/child').read_bytes(), b'kept')

    def test_directory_stream_between_file_payloads(self):
        with zipfile.ZipFile(self.archive, 'w', compression=zipfile.ZIP_DEFLATED) as writer:
            writer.writestr('first', b'before')
            writer.writestr('folder/', b'')
            writer.writestr('folder/last', b'after')
        report = safezip.process(self.archive, self.output)
        self.assertEqual(report['total_bytes'], 11)
        self.assertEqual((self.output / 'first').read_bytes(), b'before')
        self.assertEqual((self.output / 'folder/last').read_bytes(), b'after')

    def test_directory_from_nonseekable_writer_with_descriptor(self):
        class NoSeek(io.BytesIO):
            def seek(self, *args):
                raise OSError('nonseekable output')
        memory = NoSeek()
        with zipfile.ZipFile(memory, 'w', compression=zipfile.ZIP_DEFLATED) as writer:
            writer.writestr('folder/', b'')
            writer.writestr('folder/child', b'kept')
        self.archive.write_bytes(memory.getvalue())
        report = safezip.process(self.archive, self.output)
        self.assertEqual(report['total_bytes'], 4)
        self.assertEqual((self.output / 'folder/child').read_bytes(), b'kept')

    def test_directory_local_name_mismatch(self):
        raw, local, _ = directory_zip()
        raw[local + 30] = ord('X')
        self.refused(raw)

    def test_directory_local_signature_corrupt(self):
        raw, local, _ = directory_zip()
        raw[local] = 0
        self.refused(raw)

    def test_nonzero_directory_crc_even_when_both_headers_agree(self):
        raw, local, central = directory_zip()
        struct.pack_into('<I', raw, local + 14, 1)
        struct.pack_into('<I', raw, central + 16, 1)
        self.refused(raw)

    def test_stored_hidden_data_with_declared_zero_output(self):
        raw, _, _ = directory_zip(payload=b'hidden')
        self.refused(raw)

    def test_deflate_hidden_expansion_with_declared_zero_output(self):
        raw, _, _ = directory_zip(zipfile.ZIP_DEFLATED, payload=b'X' * (2 * 1024 * 1024))
        self.assertLess(len(raw), 4096)
        self.refused(raw, file_bytes=100, total_bytes=100)

    def test_deflate_truncated_or_missing_stream(self):
        for stream in (b'', b'\x03'):
            raw, _, _ = directory_zip(zipfile.ZIP_DEFLATED, stream=stream)
            self.refused(raw)

    def test_deflate_trailing_bytes_and_second_stream(self):
        for stream in (b'\x03\x00hidden', b'\x03\x00\x03\x00'):
            raw, _, _ = directory_zip(zipfile.ZIP_DEFLATED, stream=stream)
            self.refused(raw)

    def test_deflate_invalid_block(self):
        raw, _, _ = directory_zip(zipfile.ZIP_DEFLATED, stream=b'\xff\xff')
        self.refused(raw)

    def test_valid_empty_stream_with_multiple_blocks(self):
        # Non-final zero-length stored blocks followed by a final empty block.
        stream = b'\x00\x00\x00\xff\xff' * 2000 + b'\x01\x00\x00\xff\xff'
        raw, _, _ = directory_zip(zipfile.ZIP_DEFLATED, stream=stream)
        self.archive.write_bytes(raw)
        self.assertTrue(safezip.process(self.archive, self.output)['ok'])
        self.assertTrue((self.output / 'empty').is_dir())

    def test_cancellation_during_directory_checks_cleans_staged_file(self):
        raw, _, _ = directory_zip(zipfile.ZIP_DEFLATED)
        self.archive.write_bytes(raw)
        entered = False
        original = safezip.check_directory

        def checking(*args):
            nonlocal entered
            entered = True
            self.assertTrue(any((stage / 'good.txt').exists()
                                for stage in self.root.glob('.safezip-*')))
            return original(*args)

        with mock.patch.object(safezip, 'check_directory', checking):
            with self.assertRaisesRegex(safezip.Rejected, 'cancelled'):
                safezip.process(self.archive, self.output, cancelled=lambda: entered)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.safezip-*')), [])

    def test_digest_approval_does_not_bypass_directory_validation(self):
        raw, local, _ = directory_zip()
        raw[local + 30] = ord('X')
        self.refused(raw, expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_cancellation_between_directory_compressed_chunks(self):
        stream = b'\x00\x00\x00\xff\xff' * 2000 + b'\x01\x00\x00\xff\xff'
        raw, _, _ = directory_zip(zipfile.ZIP_DEFLATED, stream=stream)
        self.archive.write_bytes(raw)
        original = safezip.check_directory
        checkpoints = 0

        def checking(archive, snapshot, info, checkpoint):
            def stop():
                nonlocal checkpoints
                checkpoints += 1
                if checkpoints == 3:
                    raise safezip.Rejected('cancelled between directory chunks')
                checkpoint()
            return original(archive, snapshot, info, stop)

        with mock.patch.object(safezip, 'check_directory', checking):
            with self.assertRaisesRegex(safezip.Rejected, 'between directory chunks'):
                safezip.process(self.archive, self.output)
        self.assertEqual(checkpoints, 3)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.safezip-*')), [])

    def test_cli_refuses_directory_corruption_without_traceback(self):
        raw, local, _ = directory_zip()
        raw[local + 30] = ord('X')
        self.archive.write_bytes(raw)
        result = subprocess.run(['python3', '-B', str(Path(safezip.__file__)),
                                 'extract', str(self.archive), str(self.output)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertNotIn('Traceback', result.stderr)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob('.safezip-*')), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
