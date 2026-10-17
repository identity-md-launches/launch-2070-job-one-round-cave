#!/usr/bin/env python3
"""Bounded offline OpenAPI 3.1 array-contains compatibility analysis."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location(
    'containscheck_previous', Path(__file__).resolve().parent / 'tuplecheck.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
api = previous.api
MAX_CONTAINS_PAIRS = 1024


def policy(document, schema):
    """Return effective match-count bounds and a resolved predicate, if present."""
    minimum = schema.get('minContains', 1)
    maximum = schema.get('maxContains')
    api.require(type(minimum) is int and minimum >= 0,
                'minContains must be a nonnegative integer')
    api.require(maximum is None or (type(maximum) is int and maximum >= 0),
                'maxContains must be a nonnegative integer')
    if 'contains' not in schema:
        return None, minimum, maximum
    predicate = document.resolve(schema['contains'])
    api.require(isinstance(predicate, (dict, bool)),
                'contains must resolve to a schema')
    return predicate, minimum, maximum


class Analyzer(previous.Analyzer):
    def __init__(self, old, new):
        super().__init__(old, new)
        self.contains_pairs = []

    def predicate(self, old, new, loc, direction):
        if type(old) is bool or type(new) is bool:
            self.changed(old, new, loc, 'contains_boolean_policy_changed',
                         'Matching-item admission changed; check array reachability.')
            unsafe = (new is False and old is not False) if direction == 'request' else (
                     old is False and new is not False)
            if unsafe:
                self.emit('breaking', 'contains_predicate_incompatible', loc,
                          'Potential break in which items can satisfy contains.')
            if old is False or new is False:
                return
        self.schema({} if old is True else old, {} if new is True else new,
                    loc, direction)

    def _schema(self, old, new, loc, direction):
        super()._schema(old, new, loc, direction)
        keys = {'contains', 'minContains', 'maxContains'}
        if not (keys & old.keys() or keys & new.keys()):
            return
        where = loc + '/contains'
        if not (self.old.obj['openapi'].startswith('3.1.') and
                self.new.obj['openapi'].startswith('3.1.')):
            self.emit('review', 'contains_dialect_unchecked', where,
                      'Array contains analysis requires OpenAPI 3.1 on both sides.')
            return
        api.require(len(self.contains_pairs) < MAX_CONTAINS_PAIRS,
                    'contains pair limit exceeded; compare a smaller description')
        a, amin, amax = policy(self.old, old)
        b, bmin, bmax = policy(self.new, new)
        self.contains_pairs.append(dict(location=where, direction=direction,
            old_present=a is not None, new_present=b is not None,
            old_min=amin if a is not None else None,
            new_min=bmin if b is not None else None,
            old_max=amax if a is not None else None,
            new_max=bmax if b is not None else None))

        if a is None or b is None:
            active = b if direction == 'request' else a
            minimum = bmin if direction == 'request' else amin
            maximum = bmax if direction == 'request' else amax
            if active is not None and (minimum > 0 or
                                       (maximum is not None and active is not False)):
                self.emit('breaking', 'contains_presence_incompatible', where,
                          'A matching-item constraint was added to requests or removed from responses.')
            return

        same = api.canonical(a) == api.canonical(b)
        if same:
            # A false predicate always has zero matches. Positive minima are
            # all equivalent for it, and nonnegative maxima have no effect.
            if a is False:
                lower_changed = (amin == 0 and bmin > 0) if direction == 'request' else (
                                amin > 0 and bmin == 0)
            else:
                lower_changed = bmin > amin if direction == 'request' else bmin < amin
            if lower_changed:
                self.emit('breaking', 'min_contains_incompatible', loc + '/minContains',
                          'Matching-item minimum potentially changes accepted arrays incompatibly.')
            if a is not False and (amax is not None or bmax is not None):
                if (bmax is not None and (amax is None or bmax < amax)) if direction == 'request' else (
                    amax is not None and (bmax is None or bmax > amax)):
                    self.emit('breaking', 'max_contains_incompatible', loc + '/maxContains',
                              'Matching-item maximum potentially changes accepted arrays incompatibly.')
            return

        if amin == bmin and amin > 0 and amax is None and bmax is None:
            self.predicate(a, b, where, direction)
        else:
            # A changed predicate under an upper bound reverses the variance of
            # the upper constraint. Mixed thresholds need whole-array reasoning.
            self.emit('review', 'contains_combination_unchecked', where,
                      'Predicate and count constraints interact; inspect accepted arrays.')


def compare(old, new):
    analyzer = Analyzer(old, new)
    report = analyzer.run()
    report.update(extension='containscheck-v1 (includes tuplecheck and earlier analyzers)',
                  contains_pairs=analyzer.contains_pairs,
                  tuple_pairs=analyzer.tuple_pairs, key_pairs=analyzer.key_pairs,
                  map_pairs=analyzer.map_pairs, dispatch_pairs=analyzer.dispatch_pairs,
                  schema_visits=analyzer.steps, selector_groups=analyzer.selector_groups,
                  status_visits=analyzer.status_visits,
                  remapped_header_pairs=analyzer.remapped_header_pairs,
                  contains_scope='OpenAPI 3.1 contains with positive minimum and no maximum: '
                                 'compare referenced predicates by request/response variance. '
                                 'Compare count bounds only when predicates resolve identically. '
                                 'These are potential region-level breaks, not whole-array proof.')
    return report


def demo():
    capture = Path(__file__).resolve().parent.parent / 'imd-openapi.json'
    old, digest = api.load(capture)
    old = copy.deepcopy(old)
    old['openapi'] = '3.1.0'
    path = sorted(old['paths'])[0]
    method = sorted(old['paths'][path].keys() & api.METHODS)[0]
    schemas = old.setdefault('components', {}).setdefault('schemas', {})
    api.require('MatchState40' not in schemas, 'demo component collision')
    schemas['MatchState40'] = {'enum': ['pending', 'done']}
    old['paths'][path][method]['responses'] = {'200': {'description': 'Hypothetical array',
        'content': {'application/json': {'schema': {'type': 'array',
            'contains': {'$ref': '#/components/schemas/MatchState40'}}}}}}
    new = copy.deepcopy(old)
    new['components']['schemas']['MatchState40']['enum'].append('retry')
    report = compare(old, new)
    api.require(any(f['severity'] == 'breaking' and
                    f['code'] == 'schema_enum_incompatible' and
                    '/contains/enum' in f['location'] for f in report['findings']),
                'demo failed to inspect unchanged contains reference')
    report.update(capture_sha256=digest, baseline_source='https://api.imd.fun/openapi.json',
                  demo='Saved real IMD operation with a hypothetical OpenAPI 3.1 response '
                       'array. Only a referenced contains enum expands. This is not an '
                       'observed service change; no API operation was called.')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo')
    diff = commands.add_parser('compare')
    diff.add_argument('old')
    diff.add_argument('new')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            report = demo()
        else:
            old, oh = api.load(args.old)
            new, nh = api.load(args.new)
            report = compare(old, new)
            report.update(old_sha256=oh, new_sha256=nh)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if args.command == 'demo' else {
            'breaking': 1, 'review_required': 3, 'no_detected_breakage': 0}[report['status']]
    except (api.Invalid, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print('containscheck: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
