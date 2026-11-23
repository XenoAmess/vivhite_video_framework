"""Review-gated full-print compositing, isolated from historical v1. GPL-3.0-only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
sys.path.insert(0, str(ROOT/'video-maker/tools'))
from stabilize_carrier_plane import composite


def render(plan_file):
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    worker = ROOT/'video-maker/tools/stabilize_carrier_plane.py'
    if hashlib.sha256(worker.read_bytes()).hexdigest() != plan['workerSha256']:
        raise ValueError('Reviewed carrier worker changed')
    project = composite
    if plan.get('trackingMode') == 'manual-carrier-quads':
        from project_keyframed_print import composite as project
        if hashlib.sha256((ROOT/'video-maker/tools/project_keyframed_print.py').read_bytes()).hexdigest() != plan['keyframedWorkerSha256']:
            raise ValueError('Reviewed keyframed projection changed')
    if plan.get('trackingMode') == 'manual-carrier-quads-hand-protected':
        from project_keyframed_print_occlusion import composite as project
        if plan.get('materialBoundaryVersion') == 2:
            from project_keyframed_print_occlusion_v2 import composite as project
        for name, expected in plan['keyframedWorkers'].items():
            if hashlib.sha256((ROOT/'video-maker/tools'/name).read_bytes()).hexdigest() != expected:
                raise ValueError('Reviewed hand-protected keyframe worker changed')
    directory = ROOT.parent/plan['runtimeRelativeToRepositoryParent']
    media = (ROOT.parent/'vivhite-analysis-output/deepseek/autumn-journey').resolve()
    assets = []
    for row in plan['shots']:
        source = (ROOT.parent/row['input']).resolve()
        reference = (EPISODE/row['reference']).resolve()
        if not source.is_relative_to(media) or not reference.is_relative_to(EPISODE):
            raise ValueError('Actual inputs escaped the episode')
        if (hashlib.sha256(source.read_bytes()).hexdigest() != row['inputSha256']
                or hashlib.sha256(reference.read_bytes()).hexdigest() != row['referenceSha256']):
            raise ValueError('Actual input bytes changed')
        assets.extend([source, reference])
    gate = [sys.executable, '-X', 'utf8', str(ROOT/'scripts/character_review.py'), 'check',
            '--episode', str(EPISODE/'episode.json'), '--document', str(plan_file)]
    for asset in assets:
        gate.extend(['--asset', str(asset)])
    subprocess.run(gate, check=True)
    if not directory.resolve().is_relative_to(media):
        raise ValueError('Output escaped the episode media workspace')
    for row in plan['shots']:
        result = project(ROOT.parent/row['input'], EPISODE/row['reference'],
                           directory/'sources'/f"{row['id']}.mp4", row['definition'])
        print(row['id'], result['sha256'], 'requires actual complete-frame review', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    render(parser.parse_args().plan.resolve())
