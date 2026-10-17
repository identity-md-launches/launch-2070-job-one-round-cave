#!/usr/bin/env python3
"""Finite-array oracle and regression tests for ContainsCheck."""
import copy
import itertools
import unittest
from unittest.mock import patch
import containscheck as tool


def doc(schema, direction='response', version='3.1.0'):
    media = {'application/json': {'schema': copy.deepcopy(schema)}}
    op = {'responses': {'200': {'description': 'test', 'content': media}}}
    if direction == 'request':
        op['requestBody'] = {'content': media}
        op['responses'] = {}
    return {'openapi': version, 'paths': {'/probe': {'post': op}}}


def root(document, direction='response'):
    op = document['paths']['/probe']['post']
    body = op['requestBody'] if direction == 'request' else op['responses']['200']
    return body['content']['application/json']['schema']


def codes(report):
    return {f['code'] for f in report['findings']}


def contains_break(report):
    return any(f['severity'] == 'breaking' and '/contains' in f['location']
               for f in report['findings'])


class Tests(unittest.TestCase):
    def test_independent_singleton_array_oracle(self):
        # For an enum-only contains predicate and one-element arrays, accepted
        # arrays are exactly the enum's members. This oracle does not call the
        # analyzer's predicate or variance helpers.
        sets = [set(s) for size in range(1, 4)
                for s in itertools.combinations(range(3), size)]
        checked = 0
        for direction, old_set, new_set in itertools.product(
                ('request', 'response'), sets, sets):
            old = doc({'type': 'array', 'contains': {'enum': sorted(old_set)}}, direction)
            new = doc({'type': 'array', 'contains': {'enum': sorted(new_set)}}, direction)
            before = {(v,) for v in range(3) if v in old_set}
            after = {(v,) for v in range(3) if v in new_set}
            unsafe = bool(before - after) if direction == 'request' else bool(after - before)
            self.assertEqual(contains_break(tool.compare(old, new)), unsafe,
                             (direction, old_set, new_set))
            checked += 1
        self.assertEqual(checked, 98)

    def test_unchanged_reference_target_changes(self):
        for direction in ('request', 'response'):
            old = doc({'type': 'array', 'contains': {'$ref': '#/components/schemas/Hit'}}, direction)
            old['components'] = {'schemas': {'Hit': {'enum': [0, 1]}}}
            new = copy.deepcopy(old)
            new['components']['schemas']['Hit']['enum'] = [0] if direction == 'request' else [0, 1, 2]
            self.assertFalse(contains_break(tool.previous.compare(old, new)))
            report = tool.compare(old, new)
            self.assertTrue(contains_break(report))
            self.assertIn('schema_enum_incompatible', codes(report))

    def test_positive_minimum_and_finite_maximum(self):
        old = {'type': 'array', 'contains': {'enum': [0, 1]}, 'minContains': 1}
        new = copy.deepcopy(old)
        new['minContains'] = 2
        self.assertIn('min_contains_incompatible', codes(tool.compare(doc(old, 'request'), doc(new, 'request'))))
        self.assertNotIn('min_contains_incompatible', codes(tool.compare(doc(old), doc(new))))
        old['minContains'], new['minContains'] = 2, 1
        self.assertIn('min_contains_incompatible', codes(tool.compare(doc(old), doc(new))))
        old['minContains'] = new['minContains'] = 1
        new['maxContains'] = 2
        self.assertIn('max_contains_incompatible', codes(tool.compare(doc(old, 'request'), doc(new, 'request'))))
        self.assertNotIn('max_contains_incompatible', codes(tool.compare(doc(old), doc(new))))
        old['maxContains'], new['maxContains'] = 2, 3
        self.assertIn('max_contains_incompatible', codes(tool.compare(doc(old), doc(new))))

    def test_presence_and_zero_minimum(self):
        bare = doc({'type': 'array'}, 'request')
        required = doc({'type': 'array', 'contains': {'enum': [0]}}, 'request')
        self.assertIn('contains_presence_incompatible', codes(tool.compare(bare, required)))
        zero = doc({'type': 'array', 'contains': {'enum': [0]}, 'minContains': 0}, 'request')
        self.assertNotIn('contains_presence_incompatible', codes(tool.compare(bare, zero)))
        capped = doc({'type': 'array', 'contains': {'enum': [0]},
                      'minContains': 0, 'maxContains': 0}, 'request')
        self.assertIn('contains_presence_incompatible', codes(tool.compare(bare, capped)))
        inert = doc({'type': 'array', 'contains': False,
                     'minContains': 0, 'maxContains': 0}, 'request')
        self.assertNotIn('contains_presence_incompatible', codes(tool.compare(bare, inert)))
        self.assertIn('contains_presence_incompatible', codes(tool.compare(
            doc(root(required, 'request')), doc(root(bare, 'request')))))

    def test_boolean_predicates_and_mixed_limits(self):
        a = doc({'type': 'array', 'contains': True}, 'request')
        b = doc({'type': 'array', 'contains': False}, 'request')
        self.assertIn('contains_predicate_incompatible', codes(tool.compare(a, b)))
        self.assertNotIn('contains_predicate_incompatible', codes(tool.compare(b, a)))
        self.assertIn('contains_predicate_incompatible', codes(tool.compare(
            doc(root(b, 'request')), doc(root(a, 'request')))))
        impossible = doc({'contains': False, 'minContains': 1})
        still_impossible = doc({'contains': False, 'minContains': 2, 'maxContains': 0})
        self.assertFalse(contains_break(tool.compare(impossible, still_impossible)))
        a = doc({'type': 'array', 'contains': {'enum': [0]}, 'maxContains': 2})
        b = copy.deepcopy(a)
        root(b)['contains']['enum'].append(1)
        report = tool.compare(a, b)
        self.assertIn('contains_combination_unchecked', codes(report))
        self.assertFalse(contains_break(report))

    def test_nested_and_inherited_findings(self):
        old = doc({'type': 'object', 'properties': {'x': {
            'type': 'array', 'contains': {'type': 'object', 'properties': {
                'name': {'enum': ['a']}}}}}})
        new = copy.deepcopy(old)
        root(new)['properties']['x']['contains']['properties']['name']['enum'].append('b')
        report = tool.compare(old, new)
        self.assertIn('schema_enum_incompatible', codes(report))
        self.assertTrue(any('/properties/x/contains/properties/name/enum' in f['location']
                            for f in report['findings']))
        self.assertTrue(all(f in report['findings'] for f in tool.previous.compare(old, new)['findings']))

    def test_dialect_and_invalid_inputs(self):
        for version in ('3.0.3', '3.1.0'):
            a = doc({'contains': {'enum': [0]}}, version=version)
            b = doc({'contains': {'enum': [1]}}, version=version)
            report = tool.compare(a, b)
            self.assertEqual('contains_dialect_unchecked' in codes(report), version == '3.0.3')
        for schema in ({'contains': 3}, {'contains': {'$ref': 'https://invalid.example/schema'}},
                       {'contains': {'$ref': '#/missing'}}, {'contains': True, 'minContains': -1},
                       {'contains': True, 'minContains': True}, {'contains': True, 'maxContains': 2.0},
                       {'contains': True, 'maxContains': False}):
            with self.subTest(schema=schema), self.assertRaises(tool.api.Invalid):
                tool.compare(doc(schema), doc(schema))

    def test_budget_and_nonmutation(self):
        a = doc({'contains': {'enum': [0]}})
        b = copy.deepcopy(a)
        report = tool.compare(a, b)
        self.assertEqual(len(report['contains_pairs']), 1)
        self.assertEqual(a, b)
        b['paths']['/probe']['post']['responses']['200']['content']['application/json']['schema']['minContains'] = 2
        with patch.object(tool, 'MAX_CONTAINS_PAIRS', 0), self.assertRaises(tool.api.Invalid):
            tool.compare(a, b)
        self.assertEqual(root(a)['contains'], {'enum': [0]})

    def test_demo(self):
        result = tool.demo()
        self.assertEqual(result['operations_compared'], 5)
        self.assertTrue(contains_break(result))
        self.assertEqual(len(result['contains_pairs']), 1)


if __name__ == '__main__':
    unittest.main()
