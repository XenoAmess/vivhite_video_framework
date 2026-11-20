"""Render explicitly chosen lighting trials from raw source; do not adopt them."""
import argparse
import os
from pathlib import Path
import shutil
import sys

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0, str(ROOT / 'video-maker/tools'))
from local_video_pipeline import read, save, now
from reference_finisher import sha
from restore_printed_regions_lighting import restore
from restore_printed_badge_lighting import restore as restore_badge


def render(run, shot, trial, revision):
    source = run / f'sources/{shot}.mp4'
    trial_configuration = read(trial)
    if sha(source) != trial_configuration['sourceSha256']:
        raise ValueError('Trial is bound to another source')
    configuration = EP / f'production/{shot}-print-lighting-configuration-v14-{revision}.json'
    destination = run / f'corrections/{shot}-print-lighting-v14-{revision}.mp4'
    checkpoint = run / f'checkpoints/{shot}-print-lighting-v14-{revision}'
    if configuration.exists() or destination.exists() or checkpoint.exists():
        raise ValueError('Preserve old candidates; choose a new revision')
    save(configuration, trial_configuration)
    checkpoint.mkdir()
    records = []
    for path in [Path(__file__), trial, configuration, *[ROOT / 'video-maker/tools' / name
            for name in ('restore_printed_regions_lighting.py', 'restore_printed_regions.py',
                'restore_printed_eyes.py', 'stabilize_printed_patch.py', 'print_lighting_calibration.py',
                'restore_printed_badge_lighting.py')]]:
        target = checkpoint / path.name
        shutil.copyfile(path, target)
        records.append({'source': str(path), 'frozen': str(target), 'sha256': sha(path)})
    save(checkpoint / 'frozen-inputs.json', {'createdAt': now(), 'files': records,
        'rawSha256': sha(source), 'selectedStillTrialSha256': sha(trial),
        'semanticAcceptance': False})
    renderer = restore if 'regions' in trial_configuration else restore_badge
    renderer(source, destination, configuration)
    if not all(sha(row['source']) == sha(row['frozen']) == row['sha256'] for row in records):
        raise ValueError('A frozen rendering input changed')
    print(shot, 'lighting video candidate rendered; complete review required', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--shot', required=True)
    parser.add_argument('--trial', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    os.environ['PATH'] = os.pathsep.join(read(args.run / 'metadata/durable-controller-config.json')
        ['toolDirectories']) + os.pathsep + os.environ['PATH']
    render(args.run.resolve(), args.shot, args.trial.resolve(), args.revision)
