#!/usr/bin/env python3
"""Replay the public IMD capture; refuse a corrupt empty-directory record."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import zipfile

from safezip import Rejected, local_path, process


def main():
    sample = local_path(Path(__file__).with_name('imd-openapi.json'))
    payload = sample.read_bytes()
    expected = 'be142840c010710cb2a5b9e5c73e71d8e79ec4054c15661699d60bfa627be96a'
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError('public capture differs from its recorded digest')
    scratch = local_path('test/scratch')
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='directory-demo-', dir=scratch) as folder:
        root = Path(folder)
        source = root / 'capture.zip'
        with zipfile.ZipFile(source, 'w') as writer:
            for name, data in [('api/openapi.json', payload), ('empty/', b'')]:
                writer.writestr(zipfile.ZipInfo(name), data, compress_type=zipfile.ZIP_DEFLATED)
        report = process(source, root / 'accepted', nodes=3)
        assert (root / 'accepted/api/openapi.json').read_bytes() == payload
        assert list((root / 'accepted/empty').iterdir()) == []
        with zipfile.ZipFile(source) as reader:
            offset = reader.getinfo('empty/').header_offset
            central = reader.start_dir
        raw = bytearray(source.read_bytes())
        # Make both headers agree on an impossible CRC for an empty directory.
        cursor = central
        while raw[cursor:cursor+4] == b'PK\x01\x02':
            name_size, extra_size, comment_size = struct.unpack_from('<HHH', raw, cursor+28)
            if raw[cursor+46:cursor+46+name_size] == b'empty/':
                struct.pack_into('<I', raw, cursor+16, 1)
                break
            cursor += 46 + name_size + extra_size + comment_size
        else:
            raise AssertionError('directory entry missing')
        struct.pack_into('<I', raw, offset+14, 1)
        source.write_bytes(raw)
        refused = root / 'refused'
        try:
            process(source, refused, expected_sha256=hashlib.sha256(raw).hexdigest())
        except Rejected as error:
            assert not refused.exists() and not list(root.glob('.safezip-*'))
            print(json.dumps({'ok': True, 'network_used': False,
                              'historical_capture_bytes': len(payload),
                              'historical_capture_sha256': expected,
                              'accepted_archive_sha256': report['archive_sha256'],
                              'empty_directory_created': True,
                              'corrupt_directory_refused': str(error),
                              'failed_destination_created': False,
                              'failed_stage_removed': True}, indent=2))
        else:
            raise AssertionError('corrupt directory accepted')


if __name__ == '__main__':
    main()
