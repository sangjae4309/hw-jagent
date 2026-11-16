#!/usr/bin/env python3
"""Union elapsed intervals from an explicitly normalized CSV.

Required columns: start,end,label,unit,clock_domain. One unit and clock domain
per input. This is not a Vitis/WDB parser and does not infer stall causes.
"""
import argparse
import csv
import json
import math
from pathlib import Path
import sys


def union_length(intervals):
    total = 0.0
    end = None
    for start, stop in sorted(intervals):
        if end is None or start > end:
            total += stop - start
            end = stop
        elif stop > end:
            total += stop - end
            end = stop
    return total


def analyze(path):
    intervals = []
    groups = {}
    units, domains = set(), set()
    with Path(path).open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        required = {'start', 'end', 'label', 'unit', 'clock_domain'}
        if not required <= set(reader.fieldnames or []):
            raise ValueError('Normalize CSV to start,end,label,unit,clock_domain before using this helper')
        for row in reader:
            start, end = float(row['start']), float(row['end'])
            if not math.isfinite(start) or not math.isfinite(end) or end < start:
                raise ValueError('Invalid interval: ' + str(row))
            if not row['unit'] or not row['clock_domain'] or not row['label']:
                raise ValueError('Unit, clock domain and label cannot be empty')
            units.add(row['unit'])
            domains.add(row['clock_domain'])
            intervals.append((start, end))
            groups.setdefault(row['label'], []).append((start, end))
    if not intervals or len(units) != 1 or len(domains) != 1:
        raise ValueError('Require nonempty intervals with one unit and one clock domain')
    return {'unit': next(iter(units)), 'clock_domain': next(iter(domains)), 'interval_count': len(intervals),
            'window_span': max(e for _, e in intervals) - min(s for s, _ in intervals),
            'union_elapsed': union_length(intervals), 'naive_sum_do_not_use_as_elapsed': sum(e-s for s, e in intervals),
            'per_label_union_not_additive': {k: union_length(v) for k, v in sorted(groups.items())},
            'limitations': 'Labels may overlap. Coverage union is not exclusive attribution or stall causality. The input boundary may omit unobserved time.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv')
    args = parser.parse_args()
    try:
        print(json.dumps(analyze(args.csv), indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
