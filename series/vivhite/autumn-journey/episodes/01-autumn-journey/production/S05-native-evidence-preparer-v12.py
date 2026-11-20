"""Local evidence preparation only; never calls the model or grants acceptance."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import subprocess
import time

root = Path('D:/workspace/vivhite_video_framework')
ep = root / 'series/vivhite/autumn-journey/episodes/01-autumn-journey'
run = Path('D:/workspace/vivhite-analysis-output/vivhite/autumn-journey/production-v12-S05-native-4k-001')
worker = ep / 'production/inspect-S05-native4k-v12.py'
extractor = ep / 'production/extract-native-candidates-v11.py'
state_file = run / 'metadata/S05-native-evidence-preparer.json'
configuration = run / 'metadata/S05-native-evidence-preparer-configuration.json'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def state(status, **fields):
    data = {'pid': os.getpid(), 'status': status, 'snapshotAt': datetime.now(timezone.utc).isoformat(),
            'onlyLocalFiles': True, 'semanticAcceptance': False, **fields}
    pending = state_file.with_suffix('.pending.json')
    pending.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8', newline='\n')
    pending.replace(state_file)

cfg = read(configuration)
assert cfg['jobId'] == 'video_gen_ab78089d679c4c66ba653410717fc5f5'
assert not state_file.exists(), 'Preserve previous preparer state; do not start duplicate workers'
command = [str(root / 'video-maker/.venv/Scripts/python.exe'), '-X', 'utf8', str(worker),
           '--directory', str(run), '--region', 'saddle-hips', '0', '0', '2600', '1041',
           '--region', 'legs-cranks', '857', '338', '2857', '2160',
           '--region', 'sticker', '1857', '647', '3143', '1435']
deadline = time.monotonic() + 48*3600
try:
    while time.monotonic() < deadline:
        assert sha(ep / 'production-plan-v12-S05-native-4k-r1.json') == cfg['planSha256']
        assert sha(worker) == cfg['workerSha256'] and sha(extractor) == cfg['extractorSha256']
        job = read(run / 'jobs/S05.json')
        assert job['jobId'] == cfg['jobId'] and job['planSha256'] == cfg['planSha256']
        report_file = run / 'clip-inspection/S05.json'
        if job.get('status') == 'completed' and job.get('sourceFile') and report_file.exists():
            report = read(report_file)
            source = (run / job['sourceFile']).resolve()
            assert source.is_relative_to(run)
            if source.exists() and report.get('status') == 'decoded' and report.get('decodedFrames') == 120:
                assert sha(source) == job['sourceSha256'] == report['identity']['sourceSha256']
                state('extracting', sourceSha256=sha(source), command=command)
                with (run / 'logs/S05-native-evidence-extraction.stdout.log').open('xb') as output:
                    with (run / 'logs/S05-native-evidence-extraction.stderr.log').open('xb') as error:
                        result = subprocess.run(command, cwd=root, stdout=output, stderr=error, timeout=3600)
                if result.returncode:
                    raise RuntimeError(f'Native evidence extractor failed: {result.returncode}; preserve all files')
                manifest = ep / 'assets/generated/production-v12-S05-native-4k-001/review/cycle-native-r1/manifest.json'
                data = read(manifest)
                assert data['sourceSha256'] == sha(source) and data['decodedFrames'] == 120
                state('evidence-ready-awaiting-actual-viewing', manifestSha256=sha(manifest),
                      sourceSha256=sha(source), manifest=str(manifest))
                break
        state('waiting-for-complete-local-source', jobId=cfg['jobId'])
        time.sleep(60)
    else:
        state('local-wait-deadline-reached', jobId=cfg['jobId'])
except BaseException as error:
    state('failed-preserve-evidence', errorType=type(error).__name__, error=str(error))
    raise
