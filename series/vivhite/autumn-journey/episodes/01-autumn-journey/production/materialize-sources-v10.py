"""Import only a new accepted S01, preserving the complete v9 timeline.

No generation or automatic semantic acceptance. GPL-3.0-only.
"""
import argparse
import importlib.util
from pathlib import Path

EP=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('v10_previous_origins',Path(__file__).with_name('materialize-sources-v9.py'))
previous=importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
worker=previous.previous.worker
PLAN_FILE=EP/'production-plan-v10-bf16-768p.json'
ORIGINS={**previous.ORIGINS,
    'S01':('production-v10-motion-768p-001','production-plan-v10-S01-image-only-r1.json')}


def validate_locked_timing(plan,baseline):
    protected=('fps','width','height','sourceSize','sourceFps','totalFrames','titleOverlays','closingCredit')
    if any(plan.get(k)!=baseline.get(k) for k in protected):
        raise ValueError('Keep the v9 format, total frames and titles unchanged')
    timing=lambda p:[(s['id'],s['seconds'],s['startFrame'],s['sourceSeconds']) for s in p['shots']]
    if timing(plan)!=timing(baseline) or len(plan['shots'])!=48:
        raise ValueError('Every v10 shot duration and start must remain identical to v9')
    if any(a!=b for a,b in zip(plan['shots'],baseline['shots']) if a['id']!='S01'):
        raise ValueError('Only S01 may change source instructions in v10')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--directory',type=Path,required=True)
    a=p.parse_args()
    validate_locked_timing(worker.read(PLAN_FILE),worker.read(previous.PLAN_FILE))
    worker.materialize(a.base,a.directory,PLAN_FILE,ORIGINS)
