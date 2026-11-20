"""Export ready local native sources without waiting for earlier shot IDs.

No HTTP, source edits, generation submission or semantic approval. GPL-3.0-only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

PLAN_SHA = '5797a7ea8d61e53b5ce7372a57fcce24cb8d924225a7c3760333651a2eda50fa'
REGIONS = {
    'S42': [('cup', [836, 330], 55)],
    'S43': [('card', [735, 514], 50)],
    'S44': [('pouch', [320, 344], 65)],
    'S45': [('keyring', [620, 326], 75)],
    'S46': [('sticker', [402, 168], 60)],
    'S47': [('plush', [740, 365], 110)],
    'S48': [('butterfly', [3300, 1500, 3840, 2160], None)],
}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def ready_source(directory, identity, job_id, frames):
    """Require matching complete local evidence; queued/missing reports stay pending."""
    job = read(directory / 'jobs' / (identity + '.json'))
    if job.get('jobId') != job_id or job.get('planSha256') != PLAN_SHA:
        raise ValueError('Submitted job binding changed: ' + identity)
    if job.get('status') in ('failed', 'cancelled', 'canceled'):
        raise ValueError('Source generation needs attention: ' + identity)
    source = directory / 'sources' / (identity + '.mp4')
    report_file = directory / 'clip-inspection' / (identity + '.json')
    if job.get('status') != 'completed' or not source.is_file() or not report_file.is_file():
        return None
    report = read(report_file)
    if (report.get('status') != 'decoded' or report.get('shotId') != identity
            or report.get('decodedFrames') != frames or report.get('usedFramesAnalysed') != frames
            or sha(source) != job.get('sourceSha256')
            or report.get('identity', {}).get('sourceSha256') != job.get('sourceSha256')):
        raise ValueError('Incomplete or stale local source inspection: ' + identity)
    return {'sourceSha256': job['sourceSha256'], 'inspectionReportSha256': sha(report_file)}


def ready_batch(directory, pending, jobs):
    """Inspect every pending ID, so a later ready source is never blocked by a queue head."""
    result = []
    for identity in pending:
        proof = ready_source(directory, identity, jobs[identity], 336 if identity == 'S48' else 120)
        if proof is not None:
            result.append((identity, proof))
    return result


def prepare(directory, episode, state_file, identities, wait_seconds=48*3600):
    root = episode.parents[4]
    sys.path.insert(0, str(root / 'video-maker/tools'))
    from local_video_pipeline import save, now
    plan_file = episode / 'production-plan-v11-native-4k.json'
    if (sha(plan_file) != PLAN_SHA or not identities or len(set(identities)) != len(identities)
            or any(identity not in REGIONS for identity in identities)):
        raise ValueError('Immutable submitted plan and unique explicit remaining shot IDs required')
    if state_file.exists():
        raise ValueError('Preserve prior preparation state; select a separate run')
    shots = {row['id']: row for row in read(plan_file)['shots']}
    jobs = {identity: read(directory / 'jobs' / (identity + '.json'))['jobId'] for identity in identities}
    names = ['prepare-review-viewing-copies-v11.py', 'extract-native-candidates-v11.py',
             'inspect-print-details-v11.py', 'inspect-motion-details-v11.py']
    workers = {name: episode / 'production' / name for name in names}
    worker_hashes = {name: sha(path) for name, path in workers.items()}
    for identity in identities:
        if sha(directory / shots[identity]['inputSource']) != shots[identity]['inputSourceSha256']:
            raise ValueError('Original generation input changed: ' + identity)
    state = {'schemaVersion': 'vivhite-ready-order-local-evidence-preparation-1',
        'startedAt': now(), 'workerSha256': sha(__file__), 'sourcePlanSha256': PLAN_SHA,
        'jobs': jobs, 'inspectionWorkers': worker_hashes, 'regions': {key: REGIONS[key] for key in identities},
        'status': 'waiting-local-source', 'pendingShots': list(identities), 'shots': [],
        'noHttpRequests': True, 'sourcePixelsModified': False, 'semanticAcceptance': False,
        'actualImageViewingClaim': False, 'formalFilmApproval': False}
    save(state_file, state)
    review = episode / 'assets/generated/production-v11-native-4k-001/review'
    deadline = time.monotonic() + wait_seconds
    pending = list(identities)
    try:
        while pending:
            if sha(plan_file) != PLAN_SHA or sha(__file__) != state['workerSha256']:
                raise ValueError('Plan or preparation worker changed')
            batch = ready_batch(directory, pending, jobs)
            for identity, proof in batch:
                shot = shots[identity]
                if sha(directory / shot['inputSource']) != shot['inputSourceSha256']:
                    raise ValueError('Bound input changed: ' + identity)
                source = directory / 'sources' / (identity + '.mp4')
                report_file = directory / 'clip-inspection' / (identity + '.json')
                frames = 336 if identity == 'S48' else 120
                entry = {'id': identity, 'startedAt': now(), **proof, 'commands': []}
                state['shots'].append(entry)
                state.update(status='preparing-local-evidence', activeShot=identity)
                save(state_file, state)
                commands = [
                    (names[0], ['--directory', str(directory), '--shot', identity,
                        '--source', str(source), '--report', str(report_file)]),
                    (names[1], ['--source', str(source), '--report', str(report_file),
                        '--destination', str(review / 'native-candidates' / (identity + '-raw'))]),
                ]
                for kind, coordinates, radius in REGIONS[identity]:
                    name = names[3] if radius is None else names[2]
                    args = ['--source', str(source), '--identity', identity + '-raw-' + kind,
                            '--frames', str(frames)]
                    if radius is None:
                        args += ['--run-name', directory.name, '--box', *map(str, coordinates)]
                    else:
                        args += ['--center', *map(str, coordinates), '--radius', str(radius), '--max-scale', '2.5']
                    commands.append((name, args))
                for index, (name, args) in enumerate(commands, 1):
                    if sha(workers[name]) != worker_hashes[name]:
                        raise ValueError('Inspection worker changed: ' + name)
                    log_file = directory / 'logs' / f'{identity}-ready-order-002-{index:02}.log'
                    argv = [sys.executable, '-X', 'utf8', str(workers[name]), *args]
                    row = {'worker': name, 'workerSha256': worker_hashes[name], 'argv': argv,
                        'log': str(log_file), 'startedAt': now()}
                    entry['commands'].append(row)
                    save(state_file, state)
                    try:
                        with log_file.open('xb') as log:
                            result = subprocess.run(argv, cwd=root, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
                        row['exitCode'] = result.returncode
                    except subprocess.TimeoutExpired:
                        row.update(exitCode=None, errorType='TimeoutExpired')
                    row['finishedAt'] = now()
                    if sha(workers[name]) != worker_hashes[name] or ready_source(directory, identity, jobs[identity], frames) != proof:
                        raise ValueError('Bound source or inspection changed during extraction: ' + identity)
                    save(state_file, state)
                entry.update(finishedAt=now(), preparedWithoutErrors=all(row.get('exitCode') == 0 for row in entry['commands']))
                pending.remove(identity)
                state.update(status='waiting-local-source', pendingShots=list(pending), updatedAt=now())
                save(state_file, state)
                print(identity, 'ready-order evidence prepared; actual viewing and acceptance remain separate.', flush=True)
            if pending:
                if time.monotonic() >= deadline:
                    raise TimeoutError('Local evidence readiness deadline')
                time.sleep(60)
        complete = all(row['preparedWithoutErrors'] for row in state['shots'])
        state.update(status='complete-evidence-only-actual-review-required' if complete else 'evidence-errors-materials-retained', finishedAt=now())
        save(state_file, state)
        return 0 if complete else 2
    except Exception as error:
        state.update(status='attention-local-evidence-only', errorType=type(error).__name__, updatedAt=now())
        save(state_file, state)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--episode', required=True, type=Path)
    parser.add_argument('--state', required=True, type=Path)
    parser.add_argument('--shots', required=True, nargs='+')
    args = parser.parse_args()
    raise SystemExit(prepare(args.directory.resolve(), args.episode.resolve(), args.state.resolve(), args.shots))
