"""Prepare technical caches for explicitly accepted native4K sources.

No generation requests, new visual decisions, film assembly or publication.
Formal import, character binding and encoded-film review remain required.
GPL-3.0-only.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0, str(ROOT / 'video-maker/tools'))
from local_video_pipeline import contained, read, save, source_frame_count, now
from reference_finisher import sha
from render_4k_technical_preview import selected_source

PLAN_SHA = '5797a7ea8d61e53b5ce7372a57fcce24cb8d924225a7c3760333651a2eda50fa'
CHECKS = ('noHumanFaces', 'noAddedPeople', 'allCharactersFemale', 'costumeStyle',
          'motionAndContinuity', 'merchandiseBehavior', 'referenceAppearance')


def accepted_source(directory, shot):
    """Reject missing or revoked decisions even when no local correction exists."""
    decisions = read(directory / 'clip-decisions.json')
    decision = next((row for row in decisions['shots'] if row['id'] == shot['id']), {})
    if (decisions.get('sourcePlanSha256') != PLAN_SHA
            or decision.get('decision') != 'accepted'
            or decision.get('method') != 'assistant-frame-review'
            or decision.get('allSourceFrameReview') is not True
            or decision.get('allUsedFrameReview') is not True
            or decision.get('reviewedNativeFrames') != source_frame_count(shot)
            or any(decision.get(key) != 'passed' for key in CHECKS)):
        raise ValueError('Complete actual accepted-source review required: ' + shot['id'])
    job = read(directory / 'jobs' / (shot['id'] + '.json'))
    source, report_file = selected_source(directory, shot, job, PLAN_SHA)
    digest = sha(source)
    original = contained(directory, 'sources/' + shot['id'] + '.mp4')
    report = read(report_file)
    if (job.get('status') != 'completed' or job.get('planSha256') != PLAN_SHA
            or job.get('sourceSha256') != sha(original)
            or decision.get('sourceSha256') != digest
            or report.get('identity', {}).get('sourceSha256') != digest
            or report.get('decodedFrames') != source_frame_count(shot)
            or report.get('usedFramesAnalysed') != source_frame_count(shot)):
        raise ValueError('Stale source, decision, job or inspection: ' + shot['id'])
    evidence = decision.get('frameEvidence', [])
    if sum(row['items'] for row in evidence) != source_frame_count(shot):
        raise ValueError('Incomplete source evidence: ' + shot['id'])
    for row in evidence:
        if sha(row['path']) != row['sha256']:
            raise ValueError('Changed actual viewing evidence: ' + shot['id'])
    return source, digest


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams',
                             '-of', 'json', str(path)], capture_output=True, check=True, timeout=600)
    streams = json.loads(result.stdout)['streams']
    if len(streams) != 1 or streams[0]['codec_type'] != 'video':
        raise ValueError('Exactly one video-only stream required')
    stream = streams[0]
    return (stream['width'], stream['height'], stream['avg_frame_rate'], int(stream['nb_read_frames']))


def prepare(directory, cache, identities):
    plan_file = EP / 'production-plan-v11-native-4k.json'
    if sha(plan_file) != PLAN_SHA:
        raise ValueError('Immutable submitted plan required')
    plan = read(plan_file)
    by_id = {row['id']: row for row in plan['shots']}
    if not identities or len(set(identities)) != len(identities) or any(key not in by_id for key in identities):
        raise ValueError('Unique explicit existing shot IDs required')
    # Validate the entire requested batch before creating outputs.
    inputs = [(by_id[key], *accepted_source(directory, by_id[key])) for key in identities]
    os.environ['PATH'] = os.pathsep.join(read(directory / 'metadata/durable-controller-config.json')
        ['toolDirectories']) + os.pathsep + os.environ.get('PATH', '')
    cache.mkdir(parents=True, exist_ok=True)
    state_file = cache / 'cache-preparation.json'
    if state_file.exists():
        raise ValueError('Preserve previous run; choose a new cache directory')
    state = {'schemaVersion': 'vivhite-reviewed-native4k-segment-cache-1', 'startedAt': now(),
             'workerSha256': sha(__file__), 'sourcePlanSha256': PLAN_SHA, 'requestedShots': identities,
             'status': 'preparing', 'segments': [], 'semanticAcceptance': False, 'formalFilm': False}
    save(state_file, state)
    try:
        for shot, source, digest in inputs:
            started = time.monotonic()
            if probe(source) != (3840, 2160, '24/1', source_frame_count(shot)):
                raise ValueError('Complete native4K source required: ' + shot['id'])
            identity = {'sourceSha256': digest, 'frames': shot['seconds'] * 30,
                        'width': 3840, 'height': 2160, 'recipe': 'fps30-x264-fast-crf17-1'}
            target = cache / (shot['id'] + '.mp4')
            partial = target.with_suffix('.partial.mp4')
            receipt = target.with_suffix('.json')
            if any(path.exists() for path in (target, partial, receipt)):
                raise ValueError('Preserve existing segment outputs: ' + shot['id'])
            argv = ['ffmpeg', '-v', 'error', '-i', str(source), '-map', '0:v:0', '-an', '-vf',
                    'scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,fps=30',
                    '-frames:v', str(identity['frames']), '-c:v', 'libx264', '-preset', 'fast',
                    '-crf', '17', '-pix_fmt', 'yuv420p', str(partial)]
            with (cache / (shot['id'] + '.encoder.log')).open('xb') as log:
                subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1800)
            if probe(partial) != (3840, 2160, '30/1', identity['frames']):
                raise ValueError('Encoded segment geometry, rate or length differs')
            if accepted_source(directory, shot)[1] != digest or sha(source) != digest:
                raise ValueError('Source or decision changed while encoding')
            partial.replace(target)
            save(receipt, {'identity': identity, 'sha256': sha(target)})
            state['segments'].append({'id': shot['id'], 'identity': identity, 'sha256': sha(target),
                'receiptSha256': sha(receipt), 'argv': argv, 'elapsedSeconds': time.monotonic() - started})
            state.update(updatedAt=now(), completedSegments=len(state['segments']))
            save(state_file, state)
            print(shot['id'], 'technical segment prepared; no film approval.', flush=True)
        state.update(status='complete-cache-awaiting-formal-import-and-film-review', finishedAt=now())
        save(state_file, state)
    except Exception as error:
        state.update(status='failed-partials-retained', failedAt=now(), errorType=type(error).__name__)
        save(state_file, state)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--cache', required=True, type=Path)
    parser.add_argument('--shots', required=True, nargs='+')
    args = parser.parse_args()
    prepare(args.directory.resolve(), args.cache.resolve(), args.shots)
