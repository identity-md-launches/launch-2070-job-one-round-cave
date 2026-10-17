#!/usr/bin/env python3
"""Carry a complete unsigned RewardSplit allocation for offline recomputation."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import re
import sys

SOURCE = Path(__file__).resolve().parents[1] / 'rewardreceipt' / 'rewardreceipt.py'
SPEC = importlib.util.spec_from_file_location('rewardbundle_receipt', SOURCE)
rr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rr)
rs = rr.rs
MAX_BYTES = 96000
DEFAULT_METADATA = Path(__file__).with_name('zto-observation.json')
FIELDS = {'schema', 'request', 'metadata', 'report', 'receipt'}
SCOPE = ('Unsigned offline arithmetic agreement only; no identity, entitlement, '
         'metadata authenticity, current balance or payment established.')


def bounded(value):
    pending, count = [(value, 0)], 0
    while pending:
        item, depth = pending.pop()
        count += 1
        rs.require(depth <= 64 and count <= 20000, 'JSON nesting or node limit exceeded')
        if isinstance(item, dict):
            pending.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            pending.extend((child, depth + 1) for child in item)
    return value


def parse(data):
    return bounded(rs.parse_json(data))


def encoded(value):
    bounded(value)
    data = rr.canonical_bytes(value)
    rs.require(len(data) + 1 <= MAX_BYTES, 'bundle exceeds 96000-byte limit')
    return data


def read(value):
    with rs.workspace_path(value).open('rb') as source:
        data = source.read(MAX_BYTES + 1)
    rs.require(len(data) <= MAX_BYTES, 'input exceeds 96000-byte limit')
    return parse(data)


def pack(request, report, metadata):
    receipt = rr.verify(request, report, metadata)
    bundle = {'schema': 'rewardbundle-v1', 'request': request, 'metadata': metadata,
              'report': report, 'receipt': receipt}
    encoded(bundle)
    return bundle


def verify(bundle, expected_sha256=None):
    rs.require(isinstance(bundle, dict) and set(bundle) == FIELDS,
               'bundle must contain exactly schema, request, metadata, report and receipt')
    rs.require(bundle['schema'] == 'rewardbundle-v1', 'unknown bundle schema')
    data = encoded(bundle)
    digest = hashlib.sha256(data).hexdigest()
    if expected_sha256 is not None:
        rs.require(isinstance(expected_sha256, str) and
                   re.fullmatch('[0-9a-f]{64}', expected_sha256),
                   'expected SHA-256 must be 64 lowercase hex digits')
        rs.require(digest == expected_sha256, 'bundle differs from expected SHA-256')
    receipt = rr.verify(bundle['request'], bundle['report'], bundle['metadata'])
    rs.require(rr.canonical_bytes(receipt) == rr.canonical_bytes(bundle['receipt']),
               'embedded receipt differs from recomputation')
    return {'schema': 'rewardbundle-check-v1', 'result': 'verified exact allocation bundle',
            'bundle_sha256': digest, 'expected_digest_matched': expected_sha256 is not None,
            'budget_units': receipt['budget_units'], 'contributors': receipt['contributors'],
            'token': receipt['token'], 'scope': SCOPE}


def write_new(bundle, destination):
    # Validate and encode before opening anything; refuse existing files and symlink escapes.
    verify(bundle)
    data = encoded(bundle) + b'\n'
    with rs.workspace_path(destination).open('xb') as output:
        output.write(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo')
    create = sub.add_parser('pack')
    create.add_argument('--request', required=True)
    create.add_argument('--report', required=True)
    create.add_argument('--metadata', default=str(DEFAULT_METADATA))
    create.add_argument('--output', required=True)
    check = sub.add_parser('verify')
    check.add_argument('--bundle', required=True)
    check.add_argument('--sha256', help='canonical digest received through a separate trusted channel')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            request = read(rr.ROOT / 'example.json')
            metadata = read(DEFAULT_METADATA)
            bundle = pack(request, rs.allocate(request, metadata), metadata)
            result = verify(bundle, rr.digest(bundle))
            # Exercise the actual serialized handoff, rather than only live Python objects.
            rs.require(verify(rs.parse_json(encoded(bundle)), rr.digest(bundle)) == result,
                       'serialized handoff mismatch')
        elif args.command == 'pack':
            bundle = pack(read(args.request), read(args.report), read(args.metadata))
            write_new(bundle, args.output)
            result = verify(bundle)
        else:
            result = verify(read(args.bundle), args.sha256)
        rs.write_json(result)
    except (rs.Invalid, OSError, ValueError, OverflowError, RecursionError) as exc:
        print('rewardbundle: ' + (str(exc) if isinstance(exc, rs.Invalid)
                                 else type(exc).__name__), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
