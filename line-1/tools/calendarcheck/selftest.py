#!/usr/bin/env python3
"""Offline checks, including an independent integer-minute coverage oracle."""
import copy
from decimal import Decimal
from fractions import Fraction
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calendarcheck as cc


def single(start=0, duration=4):
    tasks = {'tasks': [{'id': 'work', 'minutes': duration}]}
    plan = {'workers': 1, 'finish': start + duration, 'schedule': [
        {'task': 'work', 'worker': 1, 'start': start, 'finish': start + duration}]}
    return tasks, plan


def availability(windows):
    return {'availability': [{'worker': 1, 'windows': [
        {'start': a, 'finish': b} for a, b in windows]}]}


class Tests(unittest.TestCase):
    def test_demo(self):
        result = cc.demo()
        self.assertFalse(result['during_break']['valid'])
        self.assertTrue(result['during_break']['schedule_valid'])
        review = next(r for r in result['during_break']['tasks'] if r['task'] == 'review')
        self.assertEqual(review['gaps'], [{'start': '2', 'finish': '3'}])
        self.assertTrue(result['after_break']['valid'])

    def test_adjacent_and_half_open(self):
        tasks, plan = single(2, 3)
        self.assertTrue(cc.check(tasks, plan, availability([(0, 2), (2, 5), (5, 6)]), 1)['valid'])
        self.assertFalse(cc.check(tasks, plan, availability([(0, 2), (5, 6)]), 1)['valid'])

    def test_multiple_gaps(self):
        tasks, plan = single(0, 10)
        result = cc.check(tasks, plan, availability([(1, 2), (4, 6), (8, 9)]), 1)
        self.assertEqual(result['unavailable_minutes'], '6')
        self.assertEqual(result['tasks'][0]['gaps'], [
            {'start': '0', 'finish': '1'}, {'start': '2', 'finish': '4'},
            {'start': '6', 'finish': '8'}, {'start': '9', 'finish': '10'}])

    def test_empty_windows(self):
        tasks, plan = single(2, 3)
        self.assertEqual(cc.check(tasks, plan, availability([]), 1)['unavailable_minutes'], '3')

    def test_decimal_exactness(self):
        # Fractions avoid Decimal's default 28-digit arithmetic context.
        end = Decimal('0.300000000000000000000000000001')
        tasks = {'tasks': [{'id': 'work', 'minutes': end}]}
        plan = {'workers': 1, 'finish': end, 'schedule': [
            {'task': 'work', 'worker': 1, 'start': 0, 'finish': end}]}
        result = cc.check(tasks, plan, availability([(0, Decimal('0.3'))]), 1)
        self.assertEqual(result['unavailable_minutes'], '0.000000000000000000000000000001')
        self.assertEqual(Fraction(result['tasks'][0]['gaps'][0]['finish']), Fraction(end))

    def test_invalid_plan_withholds(self):
        tasks, plan, windows = cc.example()
        plan['schedule'][1]['start'] = 1
        report = cc.check(tasks, plan, windows, 2)
        self.assertFalse(report['schedule_valid'])
        self.assertEqual(report['tasks'], [])
        self.assertIsNone(report['unavailable_minutes'])
        self.assertIn('duration_mismatch:review', report['schedule_violations'])

    def test_deadline_and_workers_authoritative(self):
        tasks, plan, windows = cc.example()
        self.assertFalse(cc.check(tasks, plan, windows, 2, 5)['schedule_valid'])
        tasks, plan = single()
        plan['workers'] = 2
        self.assertFalse(cc.check(tasks, plan, availability([(0, 4)]), 1)['schedule_valid'])

    def test_calendar_validation(self):
        malformed = [availability([(2, 1)]), availability([(-1, 2)]),
                     availability([(0, 0)]), availability([(0, 3), (2, 4)]),
                     availability([(3, 4), (0, 1)]), availability([(False, 3)]),
                     availability([(0, float('inf'))]), {'availability': []},
                     {'availability': [{'worker': True, 'windows': []}]},
                     {'availability': [{'worker': 2, 'windows': []}]},
                     {'availability': [{'worker': 1, 'windows': [], 'extra': 1}]}]
        for value in malformed:
            with self.subTest(value=value), self.assertRaises(ValueError):
                cc.calendar(value, 1)
        with self.assertRaises(ValueError):
            cc.calendar({'availability': [{'worker': 1, 'windows': []}] * 2}, 2)
        for workers in (True, 0, 65):
            with self.assertRaises(ValueError):
                cc.calendar(availability([]), workers)

    def test_explicit_idle_workers(self):
        tasks, plan = single()
        plan['workers'] = 2
        windows = availability([(0, 4)])
        with self.assertRaises(ValueError):
            cc.check(tasks, plan, windows, 2)
        windows['availability'].append({'worker': 2, 'windows': []})
        self.assertTrue(cc.check(tasks, plan, windows, 2)['valid'])

    def test_window_bound(self):
        self.assertEqual(len(cc.calendar(availability([(i*2, i*2+1) for i in range(2000)]), 1)[1]), 2000)
        with self.assertRaises(ValueError):
            cc.calendar(availability([(i*2, i*2+1) for i in range(2001)]), 1)

    def test_seeded_minute_oracle(self):
        rng = random.Random(4001)
        for _ in range(300):
            workers = rng.randint(1, 4)
            tasks, schedule, windows = [], [], []
            missing, gaps_by_task = 0, {}
            for worker in range(1, workers+1):
                available = {i for i in range(25) if rng.randrange(3)}
                # Unit windows exercise adjacency merging without sharing logic.
                windows.append({'worker': worker, 'windows': [
                    {'start': i, 'finish': i+1} for i in sorted(available)]})
                cursor = rng.randint(0, 2)
                for index in range(rng.randint(1, 4)):
                    duration = rng.randint(1, 4)
                    name = f'{worker}:{index}'
                    tasks.append({'id': name, 'minutes': duration})
                    schedule.append({'task': name, 'worker': worker, 'start': cursor, 'finish': cursor+duration})
                    absent = {i for i in range(cursor, cursor+duration) if i not in available}
                    missing += len(absent)
                    gaps_by_task[name] = absent
                    cursor += duration + rng.randint(0, 2)
            graph = {'tasks': tasks}
            plan = {'workers': workers, 'finish': max(r['finish'] for r in schedule), 'schedule': schedule}
            original = copy.deepcopy((graph, plan, windows))
            result = cc.check(graph, plan, {'availability': windows}, workers)
            self.assertEqual(result['valid'], missing == 0)
            self.assertEqual(int(result['unavailable_minutes']), missing)
            for row in result['tasks']:
                observed = {i for gap in row['gaps'] for i in range(int(gap['start']), int(gap['finish']))}
                self.assertEqual(observed, gaps_by_task[row['task']])
            self.assertEqual((graph, plan, windows), original)

    def test_cli(self):
        script = str(Path(__file__).with_name('calendarcheck.py'))
        demo = subprocess.run([sys.executable, '-B', script, '--demo'], capture_output=True, text=True)
        self.assertEqual(demo.returncode, 0, demo.stderr)
        self.assertTrue(json.loads(demo.stdout)['after_break']['valid'])
        bad = subprocess.run([sys.executable, '-B', script, '--demo', '--workers', '2'], capture_output=True, text=True)
        self.assertEqual(bad.returncode, 1)
        self.assertEqual(bad.stdout, '')


if __name__ == '__main__':
    unittest.main()
