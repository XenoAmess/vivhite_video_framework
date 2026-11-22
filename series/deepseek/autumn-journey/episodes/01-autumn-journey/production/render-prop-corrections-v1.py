"""Gated constant reframing and optional inert printed-video texture. GPL-3.0-only."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
sys.path.insert(0, str(ROOT/'video-maker/tools'))
from stabilize_printed_patch import stabilize


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def render(plan_file):
    plan_file = plan_file.resolve()
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    directory = (ROOT.parent/plan['runtimeRelativeToRepositoryParent']).resolve()
    media = (ROOT.parent/'vivhite-analysis-output/deepseek/autumn-journey').resolve()
    if not directory.is_relative_to(media):
        raise ValueError('Keep corrections inside the episode media workspace')
    inputs = {}
    for sid, binding in plan['inputs'].items():
        source = (ROOT.parent/binding['pathRelativeToRepositoryParent']).resolve()
        if not source.is_relative_to(media) or sha(source) != binding['sha256']:
            raise ValueError('Actual source changed or escaped media workspace')
        inputs[sid] = source
    gate = [sys.executable, '-X', 'utf8', str(ROOT/'scripts/character_review.py'), 'check',
            '--episode', str(EPISODE/'episode.json'), '--document', str(plan_file)]
    for source in inputs.values():
        gate += ['--asset', str(source)]
    subprocess.run(gate, check=True)
    (directory/'intermediate').mkdir(parents=True, exist_ok=True)
    (directory/'sources').mkdir(exist_ok=True)
    for shot in plan['shots']:
        sid = shot['id']
        output = directory/'sources'/f'{sid}.mp4'
        receipt = output.with_suffix('.receipt.json')
        identity = {'planSha256': sha(plan_file), 'workerSha256': sha(__file__),
                    'sourceSha256': sha(inputs[sid]), 'shotId': sid}
        if output.exists():
            if not receipt.exists():
                raise ValueError('Unbound output retained; use a new candidate version')
            old = json.loads(receipt.read_text(encoding='utf-8'))
            if old['identity'] != identity or old['sha256'] != sha(output):
                raise ValueError('Cached correction changed')
            continue
        cropped = directory/'intermediate'/f'{sid}-cropped.mp4'
        if cropped.exists():
            raise ValueError('Existing intermediate retained; inspect before another version')
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(inputs[sid]), '-map', '0:v:0', '-an',
                        '-vf', shot['cropFilter'], '-frames:v', str(shot['outputFrames']), '-c:v',
                        'libx264', '-crf', '14', '-preset', 'fast', '-pix_fmt', 'yuv420p', str(cropped)],
                       check=True, timeout=180)
        if shot.get('printedPatch'):
            patch = shot['printedPatch']
            stabilize(cropped, output, tuple(patch['center']), patch['radius'])
        else:
            shutil.copyfile(cropped, output)
        subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(output), '-f', 'null', '-'],
                       check=True, timeout=180)
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames',
                        '-show_streams', '-of', 'json', str(output)]))
        video = probe['streams'][0]
        if (video['width'], video['height'], int(video['nb_read_frames']), video['avg_frame_rate']) != (
                1344, 768, shot['outputFrames'], '24/1'):
            raise ValueError('Corrected frame count or native dimensions changed')
        receipt.write_text(json.dumps({'schemaVersion': 'deepseek-prop-correction-receipt-1',
            'identity': identity, 'sha256': sha(output), 'intermediateSha256': sha(cropped),
            'probe': probe, 'fullDecode': 'passed', 'semanticAcceptance': 'pending-actual-output-review',
            'humanFullPlayback': False}, indent=2)+'\n', encoding='utf-8', newline='\n')
        print(sid, sha(output), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    render(parser.parse_args().plan)
