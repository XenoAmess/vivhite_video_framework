"""Import seven reviewed motion replacements, preserving the first 47 timings.

No media is generated or approved here. GPL-3.0-only.
"""
import argparse
import importlib.util
from pathlib import Path

EP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('v8_shared_source_materializer',
    Path(__file__).with_name('materialize-sources-v6.py'))
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

REPLACEMENTS = ('S05', 'S07', 'S15', 'S28', 'S44', 'S47', 'S48')
PLAN_FILE = EP / 'production-plan-v8-bf16-768p-r4.json'
ORIGINS = {**worker.ORIGINS, **{
    identity: ('production-v8-motion-768p-001', 'production-plan-v8-motion-image-only-r1.json')
    for identity in REPLACEMENTS}}
ORIGINS['S15'] = ('production-v8-motion-768p-S15-002', 'production-plan-v8-S15-image-only-r2.json')
ORIGINS['S48'] = ('production-v8-motion-768p-S48-005', 'production-plan-v8-S48-image-only-r5.json')


def validate_locked_timing(plan, baseline):
    """The user's correction permits a duration change only in the closing shot."""
    if (plan.get('fps') != 30 or len(plan['shots']) != 48 or len(baseline['shots']) != 48
            or plan.get('totalFrames') != 6150
            or [(s['id'], s['seconds'], s['startFrame']) for s in plan['shots'][:-1]]
            != [(s['id'], s['seconds'], s['startFrame']) for s in baseline['shots'][:-1]]
            or (plan['shots'][-1]['id'], plan['shots'][-1]['seconds'],
                plan['shots'][-1]['startFrame']) != ('S48', 14, 5730)
            or plan['shots'][-1]['sourceSeconds'] not in (14, 15)):
        raise ValueError('Only S48 may change duration; preserve all first 47 shot timings and exactly 205 seconds')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--directory', required=True, type=Path)
    args = parser.parse_args()
    plan_file = PLAN_FILE
    validate_locked_timing(worker.read(plan_file), worker.read(EP / 'production-plan-v7-bf16-768p.json'))
    worker.materialize(args.base, args.directory, plan_file, ORIGINS)
