#!/usr/bin/env python3
"""Read-only checks for the optional course-energy-planner JSON format.

Python 3.9+, standard library only. Does not rewrite files or choose priorities.
"""
import argparse
import json
import math
import re
import sys
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = timezone.utc


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(label + ' must be a non-negative finite number')
    return value


def local_date(value, label):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError(label + ' must be YYYY-MM-DD')
    return date.fromisoformat(value)


def instant(value, label):
    if not isinstance(value, str) or 'T' not in value:
        raise ValueError(label + ' must be an ISO timestamp with an offset')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(label + ' needs an explicit timezone offset')
    return result.astimezone(UTC)


def identifier(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' must be a non-empty string')
    return value


def check(plan):
    findings = []
    def finding(severity, code, **detail):
        findings.append(dict(severity=severity, code=code, **detail))
    if not isinstance(plan, dict) or plan.get('schema_version') != 1:
        raise ValueError('schema_version must be 1')
    zone = ZoneInfo(plan['timezone'])
    horizon = plan['horizon']
    first = local_date(horizon['start'], 'horizon.start')
    last = local_date(horizon['end'], 'horizon.end')
    if last < first or (last - first).days > 366:
        raise ValueError('horizon must be ordered and at most 367 days')
    prefs = plan['preferences']
    ceiling = number(prefs['work_minutes_ceiling'], 'work_minutes_ceiling')
    if not isinstance(prefs.get('classes_count'), bool):
        raise ValueError('classes_count must be explicitly true or false')
    limits = prefs.get('daily_limits', {})
    if not isinstance(limits, dict):
        raise ValueError('daily_limits must be an object')
    for key, val in limits.items():
        local_date(key, 'daily limit date')
        number(val, 'daily limit')
    tasks = {}
    components = {}
    if not isinstance(plan['tasks'], list) or not isinstance(plan['sessions'], list):
        raise ValueError('tasks and sessions must be arrays')
    for task in plan['tasks']:
        tid = identifier(task['id'], 'task id')
        if tid in tasks:
            raise ValueError('duplicate task id: ' + tid)
        due = task.get('formal_due')
        due_date = due_time = None
        if due is None:
            finding('warning', 'DEADLINE_UNKNOWN', task_id=tid)
        elif isinstance(due, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', due):
            due_date = local_date(due, 'formal_due')
            finding('info', 'DEADLINE_TIME_UNKNOWN', task_id=tid, date=due)
        else:
            due_time = instant(due, 'formal_due')
            due_date = due_time.astimezone(zone).date()
        tasks[tid] = dict(due_date=due_date, due_time=due_time)
        if not isinstance(task['components'], list):
            raise ValueError('components must be an array')
        for component in task['components']:
            cid = identifier(component['id'], 'component id')
            key = (tid, cid)
            if key in components:
                raise ValueError('duplicate component id in task: ' + tid + '/' + cid)
            low = number(component['remaining_minutes']['low'], 'remaining low')
            high = number(component['remaining_minutes']['high'], 'remaining high')
            if high < low:
                raise ValueError('remaining high cannot be below low')
            components[key] = dict(low=low, high=high, allocated=0.0)
    sessions = []
    seen = set()
    daily = {}
    for item in plan['sessions']:
        sid = identifier(item['id'], 'session id')
        if sid in seen:
            raise ValueError('duplicate session id: ' + sid)
        seen.add(sid)
        start = instant(item['start'], 'session start')
        end = instant(item['end'], 'session end')
        if end <= start:
            raise ValueError('session end must be after start: ' + sid)
        kind = item['kind']
        if kind not in {'work', 'meeting', 'reserve', 'class', 'break'}:
            raise ValueError('unknown session kind: ' + str(kind))
        key = (item.get('task_id'), item.get('component_id'))
        linked = key != (None, None)
        if (kind in {'work', 'meeting'} or linked) and key not in components:
            raise ValueError('session must reference an existing task and component: ' + sid)
        local_start = start.astimezone(zone)
        local_end = end.astimezone(zone)
        if local_start.date() < first or local_end.date() > last + timedelta(days=1) or (local_end.date() == last + timedelta(days=1) and local_end.time() != time.min):
            finding('warning', 'OUTSIDE_HORIZON', session_id=sid)
        if linked and kind in {'work', 'meeting', 'reserve'}:
            task = tasks[key[0]]
            due_time, due_date = task['due_time'], task['due_date']
            allowed_end = end
            if due_time is not None and end > due_time:
                finding('error', 'AFTER_DEADLINE', session_id=sid, task_id=key[0])
                allowed_end = max(start, due_time)
            elif due_time is None and due_date is not None:
                # Date-only deadlines remain date-only; no guessed official clock.
                if local_end.date() > due_date:
                    finding('error', 'AFTER_DEADLINE_DATE', session_id=sid, task_id=key[0])
                    allowed_end = start
            window_start = datetime.combine(first, time.min, tzinfo=zone).astimezone(UTC)
            window_end = datetime.combine(last + timedelta(days=1), time.min, tzinfo=zone).astimezone(UTC)
            allocation_start = max(start, window_start)
            allocation_end = min(allowed_end, window_end)
            components[key]['allocated'] += max(0.0, (allocation_end - allocation_start).total_seconds() / 60)
        cursor = start
        while cursor < end:
            day = cursor.astimezone(zone).date()
            next_midnight = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone).astimezone(UTC)
            boundary = min(end, next_midnight)
            minutes = (boundary - cursor).total_seconds() / 60
            bucket = daily.setdefault(day.isoformat(), dict(work_minutes=0.0, class_minutes=0.0, break_minutes=0.0))
            if kind == 'class':
                bucket['class_minutes'] += minutes
            elif kind == 'break':
                bucket['break_minutes'] += minutes
            else:
                bucket['work_minutes'] += minutes
            cursor = boundary
        sessions.append(dict(id=sid, start=start, end=end))
    active = []
    for current in sorted(sessions, key=lambda s: (s['start'], s['end'])):
        active = [s for s in active if s['end'] > current['start']]
        for other in active:
            finding('error', 'CLOCK_OVERLAP', session_ids=[other['id'], current['id']], overlap_minutes=round((min(other['end'], current['end']) - current['start']).total_seconds()/60, 2))
        active.append(current)
    for day, bucket in sorted(daily.items()):
        budget = limits.get(day, ceiling)
        used = bucket['work_minutes'] + (bucket['class_minutes'] if prefs['classes_count'] else 0)
        bucket.update(budget_minutes=budget, counted_minutes=round(used, 2), budget_remaining_minutes=round(budget-used, 2))
        if used > budget + 0.0001:
            finding('error', 'CAPACITY_EXCEEDED', date=day, excess_minutes=round(used-budget, 2))
        for key in bucket:
            bucket[key] = round(bucket[key], 2)
    for (tid, cid), component in components.items():
        due = tasks[tid]['due_date']
        if due is not None and first <= due <= last:
            gap = component['low'] - component['allocated']
            if gap > 0.0001:
                finding('warning', 'LOWER_BOUND_GAP', task_id=tid, component_id=cid, unallocated_minutes=round(gap, 2))
    errors = [x for x in findings if x['severity'] == 'error']
    return dict(valid_structure=True, constraint_errors=len(errors), days=dict(sorted(daily.items())), findings=findings), (1 if errors else 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', help='JSON plan file; never modified')
    args = parser.parse_args()
    try:
        with open(args.plan, encoding='utf-8') as stream:
            plan = json.load(stream)
        result, code = check(plan)
    except (OSError, ValueError, TypeError, KeyError, ZoneInfoNotFoundError) as exc:
        result, code = dict(valid_structure=False, error=str(exc)), 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return code


if __name__ == '__main__':
    sys.exit(main())
