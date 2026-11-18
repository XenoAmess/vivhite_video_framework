"""Own a reviewed video client independently of the interactive conversation.

Use an on-demand Windows scheduled task to own this process. No remote task is
cancelled, no ambiguous POST retried and no semantic decision manufactured.
GPL-3.0-only.
"""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from local_video_pipeline import read, save
from reference_finisher import sha


def now():
    return datetime.now(timezone.utc).isoformat()


def can_resume(state, jobs):
    if any(j.get('status') in ('failed','cancelled','submitting','submission-uncertain') for j in jobs):
        return False
    if state.get('status') == 'generating':
        return True
    if state.get('status') != 'interrupted-or-failed':
        return False
    error = state.get('error','').lower()
    local_json_replacement = (any(f'[winerror {code}]' in error for code in (5,32,33))
        and '.json' in error and '.partial' in error and ' -> ' in error)
    if local_json_replacement:
        return True
    return any(part in error for part in (
        'timed out','connection reset','connection aborted','connection refused',
        'remote end closed','temporary failure','urlopen error','winerror 100',
        'http 408','http 429','http 502','http 503','http 504'))


class ProcessHandle:
    def __init__(self, pid, expected_creation=None):
        self.pid, self.handle, self.creation = pid, None, None
        if not pid:
            return
        if os.name != 'nt':
            raise RuntimeError('This scheduled-task controller requires Windows')
        kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.OpenProcess.argtypes = [wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        self.handle = kernel.OpenProcess(0x1000,False,pid)
        if not self.handle and ctypes.get_last_error() == 5:
            raise PermissionError('Cannot inspect the existing client; do not risk a duplicate')
        if self.handle:
            timestamps = [wintypes.FILETIME() for _ in range(4)]
            kernel.GetProcessTimes.argtypes = [ctypes.c_void_p]+[ctypes.POINTER(wintypes.FILETIME)]*4
            if not kernel.GetProcessTimes(self.handle,*[ctypes.byref(t) for t in timestamps]):
                self.close()
                raise ctypes.WinError(ctypes.get_last_error())
            self.creation = (timestamps[0].dwHighDateTime<<32)|timestamps[0].dwLowDateTime
            if expected_creation is not None and self.creation != expected_creation:
                self.close()

    def alive(self):
        if not self.handle:
            return False
        code = wintypes.DWORD()
        kernel = ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetExitCodeProcess.argtypes = [ctypes.c_void_p,ctypes.POINTER(wintypes.DWORD)]
        return bool(kernel.GetExitCodeProcess(self.handle,ctypes.byref(code))) and code.value == 259

    def terminate(self):
        # Only called after the explicit local stop marker is present.
        if self.alive():
            # The Windows venv launcher has a separate Python child. The held
            # handle pins this verified PID, so terminate its entire owned tree.
            result = subprocess.run(['taskkill.exe','/PID',str(self.pid),'/T','/F'],
                capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode and self.alive():
                raise RuntimeError('Unable to stop the verified local video client tree')

    def identity(self):
        return {'pid':self.pid,'creationTicks':self.creation}

    def close(self):
        if self.handle:
            kernel = ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.CloseHandle.argtypes = [ctypes.c_void_p]
            kernel.CloseHandle(self.handle)
            self.handle = None


def verify_frozen(config):
    if sha(config['plan']) != config['planSha256']:
        raise ValueError('Submitted production plan changed; preserve the running job and inspect')
    for item in config['frozenWorkers']:
        if sha(item['path']) != item['sha256']:
            raise ValueError('A frozen worker changed; inspect before starting another client')


def discover_worker(config, config_file):
    """Reconcile the short spawn/journal crash window before starting a client."""
    environment = {**os.environ,'VIVHITE_DURABLE_CONFIG':str(config_file)}
    script = """$c = Get-Content -LiteralPath $env:VIVHITE_DURABLE_CONFIG -Raw -Encoding UTF8 | ConvertFrom-Json
$runName = Split-Path -Leaf $c.directory
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -like ('*' + $runName + '*') -and
        ($_.CommandLine -like '*local_video_pipeline.py*' -or $_.CommandLine -like '*render_4k_technical_preview.py*') } |
    Select-Object ProcessId,ParentProcessId | ConvertTo-Json -Compress
"""
    result = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',script],
        capture_output=True,env=environment,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('Unable to reconcile existing video clients; do not risk a duplicate')
    value = json.loads(result.stdout.decode('utf-8-sig')) if result.stdout.strip() else []
    rows = value if isinstance(value,list) else [value]
    pids = {r['ProcessId'] for r in rows}
    roots = [r for r in rows if r['ParentProcessId'] not in pids]
    if len(roots) > 1:
        raise RuntimeError('Multiple existing video client trees require inspection')
    return ProcessHandle(roots[0]['ProcessId'] if roots else None)


def checkpoint_sources(config, jobs):
    """Commit only complete inspection evidence and a non-sensitive source catalog."""
    root, directory = Path(config['root']), Path(config['directory'])
    episode = Path(config['episode']).parent
    evidence = (episode/'assets/generated/production-v11-native-4k-001/review/video-4k').resolve()
    rows, paths = [], []
    for job in jobs:
        if job.get('status') != 'completed' or not job.get('sourceSha256'):
            continue
        report_file = directory/'clip-inspection'/f"{job['shotId']}.json"
        if not report_file.exists():
            continue
        report = read(report_file)
        if report.get('status') != 'decoded' or report['identity']['sourceSha256'] != job['sourceSha256']:
            continue
        images = [report.get('temporalEvidence'),report.get('faceEvidence'),*report.get('allUsedFrameEvidence',[])]
        for image in images:
            if image:
                path = Path(image['path']).resolve()
                if not path.is_relative_to(evidence) or sha(path) != image['sha256']:
                    raise ValueError('Complete source inspection image identity changed')
                paths.append(path.relative_to(root).as_posix())
        rows.append({'id':job['shotId'],'jobId':job['jobId'],'status':'source-downloaded-inspected-content-review-pending',
            'sourceSha256':job['sourceSha256'],'rawSha256':job['rawSha256'],
            'requestSha256':job['requestSha256'],'inputSourceSha256':read(config['plan'])['shots'][int(job['shotId'][1:])-1]['inputSourceSha256'],
            'decodedNativeFrames':report['decodedFrames'],'width':3840,'height':2160,'fps':24,
            'inspectionReportSha256':sha(report_file),'semanticReview':'pending'})
    ledger_file = directory/'git-checkpoint.json'
    ledger = read(ledger_file) if ledger_file.exists() else {}
    identity = [(r['id'],r['sourceSha256'],r['inspectionReportSha256']) for r in rows]
    if not rows:
        return
    if json.loads(json.dumps(identity)) == ledger.get('sources'):
        if not ledger.get('pushed') and time.time()-ledger.get('lastPushAttempt',0) >= 300:
            pushed = subprocess.run(['git','push'],cwd=root,capture_output=True,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
            ledger.update(pushed=pushed.returncode == 0,lastPushAttempt=time.time(),
                error=pushed.stderr.decode('utf-8','replace')[-1200:] if pushed.returncode else None)
            save(ledger_file,ledger)
        return
    catalog = episode/'production/source-generation-v11-4k.json'
    save(catalog,{'schemaVersion':'vivhite-native-4k-source-catalog-1','sourcePlanSha256':config['planSha256'],
        'sources':rows,'completedSources':len(rows),'totalSources':48,
        'semanticAcceptance':'not-automatically-granted','humanFullPlayback':False})
    paths.append(catalog.relative_to(root).as_posix())
    cached = subprocess.run(['git','diff','--cached','--name-only','-z'],cwd=root,capture_output=True,check=True)
    staged = set(filter(None,cached.stdout.decode('utf-8').split('\0')))
    if staged-set(paths):
        print(now(),'deferred checkpoint: another task has staged files',flush=True)
        return
    pathspec = directory/'logs'/f'git-checkpoint-{time.time_ns()}.pathspec'
    pathspec.write_bytes(('\0'.join(paths)+'\0').encode('utf-8'))
    for command in (
        ['git','add','--pathspec-from-file='+str(pathspec),'--pathspec-file-nul'],
        ['git','diff','--cached','--check']):
        result = subprocess.run(command,cwd=root,capture_output=True,timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise RuntimeError('Source evidence checkpoint deferred: '+result.stderr.decode('utf-8','replace')[-1000:])
    changed = any(subprocess.run(['git','diff','--cached','--quiet','--',*paths[offset:offset+20]],
        cwd=root,creationflags=subprocess.CREATE_NO_WINDOW).returncode for offset in range(0,len(paths),20))
    if changed:
        result = subprocess.run(['git','commit','--only','-m',f'chore: preserve {len(rows)} native 4k source inspections',
            '--pathspec-from-file='+str(pathspec),'--pathspec-file-nul'],cwd=root,capture_output=True,
            timeout=300,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise RuntimeError('Source evidence commit deferred: '+result.stderr.decode('utf-8','replace')[-1000:])
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip()
    pushed = subprocess.run(['git','push'],cwd=root,capture_output=True,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    save(ledger_file,{'sources':identity,'commit':head,'pushed':pushed.returncode == 0,'at':now(),'lastPushAttempt':time.time(),
        'error':pushed.stderr.decode('utf-8','replace')[-1200:] if pushed.returncode else None})
    print(now(),'complete source inspections committed',head,'pushed',pushed.returncode == 0,flush=True)


def sources_complete(config, jobs):
    plan = read(config['plan'])
    expected = {s['id'] for s in plan['shots']}
    actual = {j['shotId']:j for j in jobs if j.get('status') == 'completed' and j.get('sourceSha256')}
    if set(actual) != expected:
        return False
    directory = Path(config['directory'])
    for shot in plan['shots']:
        path = directory/'clip-inspection'/f"{shot['id']}.json"
        if not path.exists():
            return False
        report = read(path)
        if (report.get('status') != 'decoded'
                or report.get('identity',{}).get('sourceSha256') != actual[shot['id']]['sourceSha256']
                or report.get('decodedFrames') != shot['sourceSeconds']*24):
            return False
    return True


def preview_complete(config, receipt):
    directory = Path(config['directory'])
    output = directory/'technical-preview/film-unreviewed.mp4'
    selections = directory/'source-selections.json'
    return (receipt.get('status') == 'encoded-technical-checks-passed-awaiting-semantic-review'
        and receipt.get('sourcePlanSha256') == config['planSha256']
        and receipt.get('sourceSelectionsSha256') == (sha(selections) if selections.exists() else None)
        and receipt.get('soundtrackSha256') == config['soundtrackSha256']
        and receipt.get('titlesSha256') == config['titlesSha256']
        and (receipt.get('width'),receipt.get('height'),receipt.get('fps'),
             receipt.get('frames'),receipt.get('seconds')) == (3840,2160,30,6150,205)
        and receipt.get('fullAudioVideoDecode') == 'passed'
        and output.exists() and sha(output) == receipt.get('filmSha256'))


def supervise(config_file):
    config = read(config_file)
    directory = Path(config['directory']).resolve()
    root = Path(config['root']).resolve()
    os.environ['PATH'] = os.pathsep.join([*config.get('toolDirectories',[]),os.environ.get('PATH','')])
    if directory.is_relative_to(root):
        raise ValueError('Keep durable runtime state and large media outside the repository')
    verify_frozen(config)
    (directory/'logs').mkdir(exist_ok=True)
    log = (directory/'logs/durable-controller.log').open('a',encoding='utf-8',buffering=1)
    sys.stdout = sys.stderr = log
    lock = (directory/'controller.lock').open('a+b')
    import msvcrt
    if not lock.tell():
        lock.write(b'0');lock.flush()
    lock.seek(0)
    msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
    prior_file = directory/'controller.json'
    prior = read(prior_file) if prior_file.exists() else {}
    binding = sha(config_file)
    identity = prior.get('worker',{}) if prior.get('configSha256') == binding else {}
    identity = identity or config.get('existingWorker',{})
    owner = ProcessHandle(identity.get('pid'),identity.get('creationTicks'))
    child = None
    attempts = prior.get('resumeAttempts',0) if prior.get('configSha256') == binding else 0
    retry_at = 0
    last_status = None
    kind = prior.get('workerKind','generation')
    progress_spec = importlib.util.spec_from_file_location('durable_4k_progress',config['progressWorker'])
    progress = importlib.util.module_from_spec(progress_spec)
    progress_spec.loader.exec_module(progress)
    # Per-thread only; restore on exit. Does not change a Windows power plan.
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    print(now(),'controller started',os.getpid(),'adopting',owner.identity(),flush=True)
    try:
        while True:
            state = read(directory/'run.json')
            jobs = [read(p) for p in sorted((directory/'jobs').glob('*.json'))]
            status = 'watching-active-worker' if owner.alive() else 'attention-required'
            if (directory/'control/stop.json').exists():
                owner.terminate()
                print(now(),'explicit local stop marker; no remote job automatically cancelled',flush=True)
                status = 'stopped-by-local-request'
            else:
                verify_frozen(config)
                if not owner.alive():
                    owner.close()
                    owner = discover_worker(config,config_file)
                    if owner.alive():
                        print(now(),'reconciled existing client',owner.identity(),flush=True)
                        status = 'reconciled-existing-worker'
                complete = sources_complete(config,jobs)
                preview = read(directory/'technical-preview/receipt.json') if (directory/'technical-preview/receipt.json').exists() else {}
                complete_preview = preview_complete(config,preview)
                preview_state = read(directory/'technical-preview/run.json') if (directory/'technical-preview/run.json').exists() else {}
                preview_retry = not preview_state or can_resume(preview_state,[])
                if not owner.alive() and complete and complete_preview:
                    status = 'complete-technical-preview-awaiting-semantic-review'
                elif not owner.alive() and ((complete and preview_retry) or (not complete and can_resume(state,jobs))):
                    if time.monotonic() >= retry_at:
                        owner.close()
                        for partial in (directory/'sources-raw').glob('*.partial.mp4'):
                            archive = directory/'failed-downloads'/f'{time.time_ns()}-{partial.name}'
                            archive.parent.mkdir(exist_ok=True)
                            partial.replace(archive)
                        attempts += 1
                        kind = 'technical-preview' if complete else 'generation'
                        command = config['previewCommand'] if complete else config['generationCommand']
                        with (directory/'logs'/f'durable-{kind}-{attempts:03}.log').open('ab') as console:
                            child = subprocess.Popen(command,cwd=root,stdout=console,stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW)
                        owner = ProcessHandle(child.pid)
                        retry_at = time.monotonic()+min(300,30*2**min(attempts-1,4))
                        status = 'started-'+kind
                        print(now(),status,owner.identity(),flush=True)
                    else:
                        status = 'waiting-for-client-retry-backoff'
                elif not owner.alive():
                    save(directory/'attention.json',{'at':now(),'status':'requires-inspection',
                        'reason':(preview_state if complete else state).get('error','Client exit requires inspection before resubmission'),
                        'ambiguousPostNeverAutomaticallyRetried':True,
                        'remoteFailureNeverAutomaticallyRequeued':True})
            if child is not None:
                child.poll()  # Reap the owned launcher without killing its child.
            snapshot = {'schemaVersion':'vivhite-durable-video-controller-1','pid':os.getpid(),
                'status':status,'snapshotAt':now(),'configSha256':binding,
                'sourcePlanSha256':config['planSha256'],'resumeAttempts':attempts,
                'worker':owner.identity(),'workerKind':kind,'schedulerTask':config['schedulerTask'],
                'completedSources':sum(j.get('status') == 'completed' for j in jobs),
                'remoteCancellationAllowed':False,'semanticAcceptance':'never-automatically-granted'}
            save(prior_file,snapshot)
            try:
                progress.export(Path(config['base']),episode_directory=Path(config['episode']).parent,emit=False)
            except (OSError,ValueError) as error:
                print(now(),'progress snapshot deferred:',repr(error),flush=True)
            try:
                checkpoint_sources(config,jobs)
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
                print(now(),'Git checkpoint deferred; rendering continues:',repr(error),flush=True)
            if status != last_status:
                print(now(),status,flush=True)
                last_status = status
            if status in ('stopped-by-local-request','complete-technical-preview-awaiting-semantic-review'):
                disabled = subprocess.run(['schtasks.exe','/Change','/TN',config['schedulerTask'],'/DISABLE'],
                    capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
                snapshot['watchdogDisabled'] = disabled.returncode == 0
                save(prior_file,snapshot)
                print(now(),'watchdog disabled',disabled.returncode == 0,flush=True)
                return
            time.sleep(20)
    finally:
        owner.close()
        lock.close()
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        log.flush()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True,type=Path)
    supervise(parser.parse_args().config.resolve())
