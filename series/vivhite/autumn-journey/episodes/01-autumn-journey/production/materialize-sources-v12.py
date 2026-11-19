"""Import the actually accepted S05 repair and the exact other47 v10 sources.

No generation or automatic semantic approval. GPL-3.0-only.
"""
import argparse
import importlib.util
from pathlib import Path

EP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('v12_previous_origins',
    Path(__file__).with_name('materialize-sources-v10.py'))
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
worker = previous.worker
PLAN_FILE = EP / 'production-plan-v12-bf16-768p.json'
ORIGINS = {**previous.ORIGINS,
    'S05': ('production-v12-saddle-768p-001', 'production-plan-v12-S05-saddle-r1.json')}


def validate_locked_timing(plan, baseline):
    protected = ('fps', 'width', 'height', 'sourceSize', 'sourceFps', 'totalFrames',
                 'titleOverlays', 'closingCredit')
    if any(plan.get(key) != baseline.get(key) for key in protected):
        raise ValueError('Keep the v10 format, total frames and titles unchanged')
    timing = lambda value: [(row['id'], row['seconds'], row['startFrame'], row['sourceSeconds'])
                            for row in value['shots']]
    if timing(plan) != timing(baseline) or len(plan['shots']) != 48:
        raise ValueError('Every shot duration and start must remain identical to v10')
    if any(row != old for row, old in zip(plan['shots'], baseline['shots']) if row['id'] != 'S05'):
        raise ValueError('Only S05 may change source instructions in v12')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    validate_locked_timing(worker.read(PLAN_FILE), worker.read(previous.PLAN_FILE))
    worker.materialize(args.base, args.directory, PLAN_FILE, ORIGINS)
