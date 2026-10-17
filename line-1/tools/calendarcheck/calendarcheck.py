#!/usr/bin/env python3
"""Check a full offline plan against explicitly declared worker availability."""
import argparse
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'plancheck'))
sys.path.insert(0, str(HERE.parent / 'lockcheck'))
import plancheck as pc
from lockcheck import exact


def calendar(data, workers):
    """Require every worker, including idle ones; merge adjacent windows only."""
    if type(workers) is not int or not 1 <= workers <= 64:
        raise ValueError('workers must be an integer from 1 to 64')
    pc.keys(data, ('availability',))
    rows = data['availability']
    if not isinstance(rows, list) or len(rows) != workers:
        raise ValueError('availability must explicitly name every worker exactly once')
    result, count = {}, 0
    for row in rows:
        pc.keys(row, ('worker', 'windows'))
        worker = row['worker']
        if type(worker) is not int or not 1 <= worker <= workers or worker in result:
            raise ValueError('invalid or duplicate calendar worker')
        if not isinstance(row['windows'], list):
            raise ValueError('windows must be an array')
        count += len(row['windows'])
        if count > 2000:
            raise ValueError('calendar exceeds 2000 windows')
        merged = []
        for window in row['windows']:
            pc.keys(window, ('start', 'finish'))
            start, finish = (pc.number(window[k], k) for k in ('start', 'finish'))
            if start < 0 or finish <= start:
                raise ValueError('windows must have nonnegative start and positive length')
            if merged and start < merged[-1][1]:
                raise ValueError('windows must be ordered and nonoverlapping')
            if merged and start == merged[-1][1]:
                merged[-1] = (merged[-1][0], finish)
            else:
                merged.append((start, finish))
        result[worker] = merged
    return result


def uncovered(start, finish, windows):
    cursor, gaps = start, []
    for left, right in windows:
        if right <= cursor:
            continue
        if left >= finish:
            break
        if left > cursor:
            gaps.append((cursor, left))
        cursor = max(cursor, right)
        if cursor >= finish:
            break
    if cursor < finish:
        gaps.append((cursor, finish))
    return gaps


def check(tasks, plan, availability, workers, budget=None):
    windows = calendar(availability, workers)
    baseline = pc.check(tasks, plan, workers, budget)
    report = {'valid': False, 'schedule_valid': baseline['valid'],
              'schedule_violations': baseline['violations'], 'tasks': [],
              'unavailable_minutes': None,
              'scope': 'Fixed full-task intervals and caller-declared availability; no task execution, clock, reservation or rescheduling.',
              'arithmetic': 'Exact decimal minutes rendered as strings; half-open intervals [start, finish).'}
    if not baseline['valid']:
        report['scope'] = 'Availability findings withheld until the complete schedule passes Plancheck.'
        return report
    total = pc.number(0, 'zero')
    for row in sorted(plan['schedule'], key=lambda r: (pc.number(r['start'], 'start'), r['worker'], r['task'])):
        start, finish = (pc.number(row[k], k) for k in ('start', 'finish'))
        gaps = uncovered(start, finish, windows[row['worker']])
        missing = sum((b-a for a, b in gaps), pc.number(0, 'zero'))
        total += missing
        report['tasks'].append({'task': row['task'], 'worker': row['worker'],
                                'available': not gaps, 'unavailable_minutes': exact(missing),
                                'gaps': [{'start': exact(a), 'finish': exact(b)} for a, b in gaps]})
    report['unavailable_minutes'] = exact(total)
    report['valid'] = total == 0
    return report


def example():
    tasks = {'tasks': [{'id': 'draft', 'minutes': 2},
                       {'id': 'review', 'minutes': 1, 'after': ['draft']},
                       {'id': 'background', 'minutes': 4}]}
    plan = {'workers': 2, 'finish': 6, 'schedule': [
        {'task': 'draft', 'worker': 1, 'start': 0, 'finish': 2},
        {'task': 'review', 'worker': 1, 'start': 2, 'finish': 3},
        {'task': 'background', 'worker': 2, 'start': 2, 'finish': 6}]}
    availability = {'availability': [
        {'worker': 1, 'windows': [{'start': 0, 'finish': 2}, {'start': 3, 'finish': 6}]},
        {'worker': 2, 'windows': [{'start': 0, 'finish': 6}]}]}
    return tasks, plan, availability


def demo():
    tasks, plan, availability = example()
    before = check(tasks, plan, availability, 2, 6)
    plan['schedule'][1].update(start=3, finish=4)
    return {'during_break': before, 'after_break': check(tasks, plan, availability, 2, 6)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--demo', action='store_true')
    for name in ('tasks', 'plan', 'calendar'):
        parser.add_argument('--' + name)
    parser.add_argument('--workers', type=int)
    parser.add_argument('--budget', type=Decimal)
    args = parser.parse_args()
    try:
        options = (args.tasks, args.plan, args.calendar, args.workers, args.budget)
        if args.demo:
            if any(v is not None for v in options):
                raise ValueError('--demo cannot be combined with check options')
            result, code = demo(), 0
        else:
            if any(v is None for v in options[:4]):
                raise ValueError('--tasks, --plan, --calendar and --workers are required')
            result = check(pc.read_json(args.tasks), pc.read_json(args.plan),
                           pc.read_json(args.calendar), args.workers, args.budget)
            code = 0 if result['valid'] else 2
        print(json.dumps(result, indent=2, allow_nan=False))
        return code
    except (ValueError, InvalidOperation, OSError, OverflowError, RecursionError) as exc:
        print('calendarcheck: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
