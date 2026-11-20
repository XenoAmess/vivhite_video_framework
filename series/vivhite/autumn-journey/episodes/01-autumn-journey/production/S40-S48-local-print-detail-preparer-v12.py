"""Prepare local detail evidence after download; no API, edits or acceptance."""
from pathlib import Path
import subprocess
import sys
import time

root = Path('D:/workspace/vivhite_video_framework')
ep = root / 'series/vivhite/autumn-journey/episodes/01-autumn-journey'
run = Path('D:/workspace/vivhite-analysis-output/vivhite/autumn-journey/production-v11-native-4k-001')
sys.path.insert(0, str(root / 'video-maker/tools'))
from local_video_pipeline import read, save, now
from reference_finisher import sha

plan_file = ep / 'production-plan-v11-native-4k.json'
plan_sha = '5797a7ea8d61e53b5ce7372a57fcce24cb8d924225a7c3760333651a2eda50fa'
assert sha(plan_file) == plan_sha
shots = {row['id']: row for row in read(plan_file)['shots']}
# Coordinates selected by actually viewing each bound input's complete first frame.
# These are preparation regions, not assertions that future output is correct.
regions = {
    'S40': [('sticker', [906, 375], 75)],
    'S41': [('plush', [643, 470], 80), ('badge', [378, 464], 45)],
    'S42': [('cup', [836, 330], 55)],
    'S43': [('card', [735, 514], 50)],
    'S44': [('pouch', [320, 344], 65)],
    'S45': [('keyring', [620, 326], 75)],
    'S46': [('sticker', [402, 168], 60)],
    'S47': [('plush', [740, 365], 110)],
    'S48': [('butterfly', [3300, 1500, 3840, 2160], None)],
}
workers = {name: ep / 'production' / name for name in ['inspect-print-details-v11.py', 'inspect-motion-details-v11.py']}
worker_hashes = {name: sha(path) for name, path in workers.items()}
jobs = {key: read(run / 'jobs' / (key + '.json'))['jobId'] for key in regions}
for key in regions:
    assert shots[key]['sourceSeconds'] == (14 if key == 'S48' else 5)
    assert sha(run / shots[key]['inputSource']) == shots[key]['inputSourceSha256']
out = run / 'metadata/S40-S48-local-print-detail-preparation-001.json'
assert not out.exists()
state = {'schemaVersion': 'vivhite-local-detail-preparation-1', 'startedAt': now(),
    'sourcePlanSha256': plan_sha, 'workerSha256': sha(__file__), 'inspectionWorkers': worker_hashes,
    'jobs': jobs, 'regions': regions, 'status': 'waiting-local-source', 'shots': [],
    'noHttpRequests': True, 'sourcePixelsModified': False, 'semanticAcceptance': False,
    'actualImageViewingClaim': False, 'formalFilmApproval': False}
save(out, state)
deadline = time.monotonic() + 48 * 3600
for key, details in regions.items():
    source = run / 'sources' / (key + '.mp4')
    report_file = run / 'clip-inspection' / (key + '.json')
    frames = 336 if key == 'S48' else 120
    while True:
        job = read(run / 'jobs' / (key + '.json'))
        assert job['jobId'] == jobs[key] and job['planSha256'] == plan_sha
        if job['status'] == 'completed' and source.exists() and report_file.exists():
            inspected = read(report_file)
            if inspected['decodedFrames'] == inspected['usedFramesAnalysed'] == frames:
                assert sha(source) == job['sourceSha256'] == inspected['identity']['sourceSha256']
                break
        if time.monotonic() > deadline:
            state.update(status='local-readiness-timeout', updatedAt=now())
            save(out, state)
            raise SystemExit('Local readiness timeout; no queue or generation action taken')
        time.sleep(60)
    entry = {'id': key, 'startedAt': now(), 'sourceSha256': sha(source), 'inspectionReportSha256': sha(report_file), 'commands': []}
    state['shots'].append(entry)
    state.update(status='preparing-local-detail', activeShot=key)
    save(out, state)
    for kind, coordinates, radius in details:
        name = 'inspect-motion-details-v11.py' if radius is None else 'inspect-print-details-v11.py'
        worker = workers[name]
        assert sha(worker) == worker_hashes[name]
        args = ['--source', str(source), '--identity', key + '-raw-' + kind, '--frames', str(frames)]
        if radius is None:
            args += ['--run-name', run.name, '--box', *map(str, coordinates)]
        else:
            args += ['--center', *map(str, coordinates), '--radius', str(radius)]
        argv = [sys.executable, '-X', 'utf8', str(worker), *args]
        row = {'kind': kind, 'workerSha256': worker_hashes[name], 'argv': argv}
        entry['commands'].append(row)
        save(out, state)
        with (run / 'logs' / (key + '-raw-' + kind + '-local-detail-001.log')).open('xb') as log:
            result = subprocess.run(argv, cwd=root, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
        row.update(exitCode=result.returncode, finishedAt=now())
        assert sha(worker) == worker_hashes[name] and sha(source) == entry['sourceSha256']
        save(out, state)
        if result.returncode:
            print(key, kind, 'preparation failed; log retained and actual review required.', flush=True)
    entry.update(finishedAt=now(), preparedWithoutErrors=all(row['exitCode'] == 0 for row in entry['commands']))
    state.update(status='waiting-local-source', updatedAt=now())
    save(out, state)
    print(key, 'detail preparation finished; no visual approval granted.', flush=True)
state.update(status='complete-evidence-only-actual-review-required', finishedAt=now())
save(out, state)
raise SystemExit(0 if all(row['preparedWithoutErrors'] for row in state['shots']) else 2)
