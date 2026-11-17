"""Import only two new accepted sources; keep the complete v8 timeline.

No media generation or semantic approval. GPL-3.0-only.
"""
import argparse
import importlib.util
from pathlib import Path

EP=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('v9_previous_origins',Path(__file__).with_name('materialize-sources-v8.py'))
previous=importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
PLAN_FILE=EP/'production-plan-v9-bf16-768p.json'
ORIGINS={**previous.ORIGINS,
    'S44':('production-v9-motion-768p-001','production-plan-v9-motion-image-only-r1.json'),
    'S47':('production-v9-motion-768p-001','production-plan-v9-motion-image-only-r1.json')}


def validate_locked_timing(plan,baseline):
    previous.validate_locked_timing(plan,baseline)
    if ([(s['id'],s['seconds'],s['startFrame'],s['sourceSeconds']) for s in plan['shots']]
            != [(s['id'],s['seconds'],s['startFrame'],s['sourceSeconds']) for s in baseline['shots']]):
        raise ValueError('Every v9 shot duration and start must remain identical to v8')
    if any(a!=b for a,b in zip(plan['shots'],baseline['shots']) if a['id'] not in ('S44','S47')):
        raise ValueError('Only S44 and S47 may change source instructions in v9')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',required=True,type=Path)
    parser.add_argument('--directory',required=True,type=Path)
    args=parser.parse_args()
    validate_locked_timing(previous.worker.read(PLAN_FILE),previous.worker.read(previous.PLAN_FILE))
    previous.worker.materialize(args.base,args.directory,PLAN_FILE,ORIGINS)
