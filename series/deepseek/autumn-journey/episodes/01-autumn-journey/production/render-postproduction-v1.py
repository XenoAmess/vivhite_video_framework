"""Version-bound local compositing; input gate precedes video encoding. GPL-3.0-only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
MEDIA = ROOT.parent/'vivhite-analysis-output'
PLAN = EPISODE/'postproduction-plan-v1-768p.json'
ASSETS = EPISODE/'assets/generated/production-v1-closing-composite-001'
RUNTIME = MEDIA/'deepseek/autumn-journey/production-v1-local-compositing-001'


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def write(file, data):
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


def files():
    return {
        'S44Source': MEDIA/'deepseek/autumn-journey/production-v1-pilot-768p-001/sources/S44.mp4',
        'coastSource': MEDIA/'vivhite/autumn-journey/production-v12-saddle-768p-full-001/sources/S48.mp4',
        'cleanPlate': ASSETS/'clean-plate-1344x768.png',
        'foreground': ASSETS/'foreground-original.png',
    }


def prepare():
    if PLAN.exists():
        raise ValueError('Preserve existing immutable postproduction plan')
    inputs = files()
    bindings = {key: {'pathRelativeToRepositoryParent': f.relative_to(ROOT.parent).as_posix(),
                      'sha256': sha(f)} for key, f in inputs.items()}
    data = {
        'schemaVersion': 'deepseek-local-compositing-1', 'width': 1344, 'height': 768,
        'fps': 24, 'noSpeech': True, 'noHumanFaces': True, 'noAddedPeople': True,
        'allCharactersFemale': True, 'inputs': bindings, 'nativeAudioRetained': False,
        'shots': [
            {'id': 'S44', 'seconds': 4, 'sourceSeconds': 5,
             'action': 'Closed tent is unzipped downward once, curtain pulled left, revealing empty grass. Exactly the existing right hand, connected arm and navy-white female body crop. Source has a chin at extreme top-right and is NOT adopted unchanged; constant crop excludes it from every output frame.',
             'crop': {'x': 0, 'y': 96, 'width': 1176, 'height': 672},
             'outputFrames': 120,
             'filter': 'crop=1176:672:0:96,scale=1344:768:flags=lanczos,setsar=1'},
            {'id': 'S48', 'seconds': 14, 'sourceSeconds': 14, 'outputFrames': 336,
             'action': 'One continuous fourteen-second empty coastal moving background. Nonliving new whale-maid plush, hiking bag and rigid whale-tail charm rest in lower-right foreground, no autonomous face or toy motion. Waves move continuously, no loop or frozen whole scene. Clean beach patch removes the complete legacy butterfly footprint; no tree, human or other prop. Titles are added only in final assembly.',
             'legacySymbolUnionBounds': [1164, 630, 1309, 761],
             'cleanPlatePatch': {'x': 1130, 'y': 585, 'width': 214, 'height': 183,
                                'leftTopFeatherPixels': 12, 'rightBottomFeatherPixels': 0},
             'foregroundTransform': {'width': 400, 'x': 920, 'y': 480},
             'filter': "[1:v]crop=214:183:1130:585,format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='255*clip(X/12,0,1)*clip(Y/12,0,1)'[plate];[0:v][plate]overlay=1130:585[bg];[2:v]scale=400:-1,format=rgba[fg];[bg][fg]overlay=920:480,format=yuv420p,setsar=1[out]"}
        ],
        'scope': 'Actual local postproduction inputs and instructions; source/output frame review and final-film acceptance are separate. This closing is layered compositing, not a new pure Ref2VA output.'
    }
    write(PLAN, data)
    print(PLAN)


def render():
    data = json.loads(PLAN.read_text(encoding='utf-8'))
    inputs = files()
    for key, file in inputs.items():
        if data['inputs'][key]['sha256'] != sha(file):
            raise ValueError('Actual postproduction input changed')
    gate = [sys.executable, '-X', 'utf8', str(ROOT/'scripts/character_review.py'), 'check',
            '--episode', str(EPISODE/'episode.json'), '--document', str(PLAN)]
    for file in inputs.values():
        gate += ['--asset', str(file)]
    subprocess.run(gate, check=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    for shot in data['shots']:
        destination = RUNTIME/'sources'/f"{shot['id']}.mp4"
        receipt = destination.with_suffix('.receipt.json')
        identity = {'planSha256': sha(PLAN), 'workerSha256': sha(__file__), 'shotId': shot['id']}
        if destination.exists():
            if not receipt.exists():
                raise ValueError('Unbound existing output; preserve and use a new version')
            old = json.loads(receipt.read_text(encoding='utf-8'))
            if old['identity'] != identity or old['sha256'] != sha(destination):
                raise ValueError('Cached correction changed; preserve and use a new version')
            continue
        destination.parent.mkdir(exist_ok=True)
        partial = destination.with_suffix('.partial.mp4')
        if partial.exists():
            raise ValueError('Earlier partial retained; inspect before another version')
        if shot['id'] == 'S44':
            arguments = ['-i', str(inputs['S44Source']), '-vf', shot['filter'], '-map', '0:v:0']
        else:
            arguments = ['-i', str(inputs['coastSource']), '-loop', '1', '-framerate', '24',
                         '-i', str(inputs['cleanPlate']), '-loop', '1', '-framerate', '24',
                         '-i', str(inputs['foreground']), '-filter_complex', shot['filter'], '-map', '[out]']
        subprocess.run(['ffmpeg', '-v', 'error', *arguments, '-an', '-frames:v', str(shot['outputFrames']),
                        '-r', '24', '-c:v', 'libx264', '-crf', '16', '-preset', 'fast',
                        '-pix_fmt', 'yuv420p', str(partial)], check=True, timeout=600)
        subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(partial), '-f', 'null', '-'],
                       check=True, timeout=180)
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames',
                        '-show_streams', '-of', 'json', str(partial)]))
        video = probe['streams'][0]
        if (video['width'], video['height'], int(video['nb_read_frames']), video['avg_frame_rate']) != (
                1344, 768, shot['outputFrames'], '24/1'):
            raise ValueError('Postproduction stream/frame count mismatch')
        partial.replace(destination)
        write(receipt, {'schemaVersion': 'deepseek-postproduction-receipt-1', 'identity': identity,
                        'sha256': sha(destination), 'probe': probe, 'fullDecode': 'passed',
                        'semanticAcceptance': 'pending-actual-frame-review', 'humanFullPlayback': False})
        print(shot['id'], sha(destination), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'render'])
    args = parser.parse_args()
    prepare() if args.command == 'prepare' else render()
