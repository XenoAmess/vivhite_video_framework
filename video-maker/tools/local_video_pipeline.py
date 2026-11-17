"""Version-bound, resumable BF16 generation and local 2K regeneration.

Uploads real files and archives every request, poll, original result and error.
Generated media is never automatically semantically approved. GPL-3.0-only.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from reference_finisher import run, sha


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name+'.partial')
    partial.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    partial.replace(path)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def contained(owner, relative):
    owner = Path(owner).resolve()
    relative = Path(relative)
    path = (owner/relative).resolve()
    if relative.is_absolute() or not path.is_relative_to(owner) or not path.is_file():
        raise ValueError('An actual input is missing or escaped its directory')
    return path


def validate(plan):
    draft = plan.get('stage') == 'draft'
    exceptions = plan.get('shotDurationExceptions',{})
    if exceptions not in ({},{'S20':10},{'S48':10},{'S20':10,'S48':10},
                          {'S48':14},{'S20':10,'S48':14},{'S48':15},{'S20':10,'S48':15}):
        raise ValueError('Only the explicitly requested S20 ten-second and S48 ten/fifteen-second exceptions are allowed')
    expected = ('fasth3-omni-bf16',1344,768) if draft else ('open-h3-2k',2560,1440)
    if (plan.get('schemaVersion') != 'vivhite-local-two-stage-video-1'
            or plan.get('stage') not in ('draft','refine')
            or (plan.get('model'),plan.get('width'),plan.get('height')) != expected
            or plan.get('fps') != 30 or plan.get('sourceFps') != 24 or plan.get('maxShotSeconds') != 5
            or not all(plan.get(key) is True for key in ('noSpeech','noHumanFaces','noAddedPeople','allCharactersFemale'))):
        raise ValueError('Invalid five-second-maximum local video plan')
    identities = set()
    frame = 0
    for shot in plan['shots']:
        if (not re.fullmatch(r'S\d{2}[A-Z]?',shot['id']) or shot['id'] in identities
                or not isinstance(shot['seconds'],int) or not 2 <= shot['seconds'] <= exceptions.get(shot['id'],5)
                or shot.get('sourceSeconds') != exceptions.get(shot['id'],5)
                or shot.get('startFrame') != frame
                or not shot.get('prompt','').strip()):
            raise ValueError('Invalid shot identity, duration or contiguous timing')
        identities.add(shot['id'])
        frame += shot['seconds']*30
    if not identities or frame != plan['totalFrames']:
        raise ValueError('Timeline does not match total frames')
    if any(not any(shot['id']==identity and shot['seconds']==seconds for shot in plan['shots'])
           for identity,seconds in exceptions.items()):
        raise ValueError('Every declared exception must match an actual continuous shot')


def source_frame_count(shot):
    seconds = shot.get('sourceSeconds',5)
    if not isinstance(seconds,int) or isinstance(seconds,bool) or seconds not in (5,10,14,15):
        raise ValueError('Unsupported source duration')
    return seconds*24


def select_target_shots(shots,order='',limit=None,skip=''):
    priorities = order.split(',') if order else []
    excluded = set(skip.split(',')) if skip else set()
    known = {shot['id'] for shot in shots}
    if excluded-known or set(priorities)-known or (limit is not None and limit <= 0):
        raise ValueError('Target selection must name actual shots and a positive limit')
    ordered = [shot for shot in shots if shot['id'] not in excluded]
    ordered.sort(key=lambda shot:priorities.index(shot['id']) if shot['id'] in priorities else len(priorities))
    target = ordered[:limit] if limit else ordered
    if not target:
        raise ValueError('Target selection contains no shots')
    return target


def input_assets(plan, episode, directory):
    assets = []
    for shot in plan['shots']:
        if plan['stage'] == 'draft':
            assets.extend(contained(Path(episode).parent,path) for path in shot['references'])
            if shot.get('motionReference'):
                motion = contained(directory,shot['motionReference'])
                if sha(motion) != shot['motionReferenceSha256']:
                    raise ValueError('Motion reference changed')
                assets.append(motion)
        else:
            source = contained(directory,shot['inputSource'])
            if sha(source) != shot['inputSourceSha256']:
                raise ValueError('Reviewed 2K input changed')
            assets.append(source)
    for item in plan.get('reusedSources',[]):
        source = contained(directory,item['path'])
        if sha(source) != item['sha256']:
            raise ValueError('Explicitly reused reviewed source changed')
        assets.append(source)
    return list(dict.fromkeys(assets))


class ApiError(RuntimeError):
    def __init__(self, code, detail):
        self.code = code
        super().__init__(f'HTTP {code}: {detail[:1600]}')


class Api:
    def __init__(self, base):
        parsed = urllib.parse.urlsplit(base)
        if (parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username
                or parsed.password or parsed.query or parsed.fragment):
            raise ValueError('Use an HTTP(S) API root without credentials or query')
        self.base = base.rstrip('/')
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(self, method, path, body=None, headers=None, timeout=120):
        url = urllib.parse.urljoin(self.base+'/',path.lstrip('/'))
        request = urllib.request.Request(url,data=body,headers=headers or {},method=method)
        try:
            return self.opener.open(request,timeout=timeout)
        except urllib.error.HTTPError as error:
            raise ApiError(error.code,error.read(16384).decode('utf-8','replace')) from error

    def json(self, method, path, payload=None):
        body = None if payload is None else json.dumps(payload,ensure_ascii=False).encode('utf-8')
        with self.request(method,path,body,{'Content-Type':'application/json'}) as response:
            return json.load(response)

    def upload(self, path):
        path = Path(path)
        if path.stat().st_size > 512*1024*1024:
            raise ValueError('Reference exceeds the documented upload limit')
        boundary = 'vivhite-'+uuid.uuid4().hex
        # Generated/reference filenames contain no user-supplied MIME controls.
        if any(character in path.name for character in '\r\n"'):
            raise ValueError('Unsafe upload filename')
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
                'Content-Type: application/octet-stream\r\n\r\n').encode('utf-8')
        body += path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode('ascii')
        with self.request('POST','/files',body,{'Content-Type':f'multipart/form-data; boundary={boundary}'},300) as response:
            return json.load(response)


def payload_for(plan, shot, upload):
    if plan['stage'] == 'draft':
        payload = {'model':'fasth3-omni-bf16','task':'ref2va','seconds':shot.get('sourceSeconds',5),'size':'1344x768',
                'num_inference_steps':8,'guidance_scale':1.0,'seed':shot['seed'],'prompt':shot['prompt'],
                'image_reference':[upload(path) for path in shot['references']]}
        if shot.get('motionReference'):
            payload['video_reference'] = [upload(shot['motionReference'])]
        return payload
    return {'model':'open-h3-2k','size':'2560x1440','sampler':plan.get('sampler','up3'),
            'seed':plan.get('refinementSeed',1234),'prompt':shot['prompt'],
            'input_video':upload(shot['inputSource'])}


def submit(api, endpoint, payload, receipt_file, receipt):
    # Persist uncertainty before POST. A disconnect can happen after creation;
    # resumption must never blindly create a duplicate job in that case.
    if receipt.get('status') in ('submitting','submission-uncertain'):
        raise RuntimeError('Ambiguous earlier POST: inspect the saved request and server queue before resubmitting')
    receipt.update(status='submitting',submittedAt=now())
    save(receipt_file,receipt)
    try:
        remote = api.json('POST',endpoint,payload)
    except ApiError as error:
        receipt.update(status='prepared' if error.code == 429 else 'failed',error=str(error))
        save(receipt_file,receipt)
        if error.code == 429:
            return False
        raise
    except Exception as error:
        receipt.update(status='submission-uncertain',error=str(error))
        save(receipt_file,receipt)
        raise
    if not re.fullmatch(r'[A-Za-z0-9_-]+',remote.get('id','')):
        raise ValueError('Server did not return a valid task ID; saved POST must be reconciled')
    receipt.update(jobId=remote['id'],status=remote['status'],remote=remote)
    save(receipt_file,receipt)
    return True


def publish_result(api, remote, shot, directory, size):
    expected_frames = source_frame_count(shot)
    identity = remote['id']
    raw = directory/'sources-raw'/f"{shot['id']}-{identity}.mp4"
    raw.parent.mkdir(exist_ok=True)
    expected = remote.get('result',{}).get('sha256')
    if not raw.exists():
        partial = raw.with_suffix('.partial.mp4')
        with api.request('GET',f'/videos/{identity}/content',timeout=300) as response, partial.open('wb') as target:
            while block := response.read(1024*1024):
                target.write(block)
        if expected and sha(partial) != expected:
            raise ValueError('Downloaded file differs from server SHA-256; partial file retained')
        run(['ffmpeg','-v','error','-xerror','-i',str(partial),'-f','null','-'],timeout=600)
        partial.replace(raw)
    if expected and sha(raw) != expected:
        raise ValueError('Saved original result changed')
    probe = json.loads(run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(raw)]))
    video = next(item for item in probe['streams'] if item['codec_type']=='video')
    width,height = map(int,size.split('x'))
    if ((video['width'],video['height']) != (width,height) or video['avg_frame_rate'] != '24/1'
            or int(video['nb_read_frames']) < expected_frames):
        raise ValueError('Native result has unexpected dimensions, frame rate or insufficient frames; original retained')
    source = directory/'sources'/f"{shot['id']}.mp4"
    source.parent.mkdir(exist_ok=True)
    if not source.exists():
        run(['ffmpeg','-v','error','-y','-i',str(raw),'-map','0:v:0','-an','-frames:v',str(expected_frames),
             '-c:v','copy','-movflags','+faststart',str(source)])
    normalized = json.loads(run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(source)]))
    if len(normalized['streams']) != 1 or int(normalized['streams'][0]['nb_read_frames']) != expected_frames:
        raise ValueError('Exact requested source normalization failed')
    return raw,source,probe


def generate(args):
    plan_file, directory = args.plan.resolve(),args.directory.resolve()
    plan = read(plan_file)
    validate(plan)
    assets = input_assets(plan,args.episode.resolve(),directory)
    snapshots = {path:sha(path) for path in assets}
    gate = [sys.executable,str(args.root.resolve()/'scripts/character_review.py'),'check',
            '--episode',str(args.episode.resolve()),'--document',str(plan_file)]
    for asset in assets:
        gate.extend(['--asset',str(asset)])
    print(run(gate,timeout=120),flush=True)
    api = Api(args.api)
    models = api.json('GET','/models')
    actual = next((model for model in models['data'] if model['id']==plan['model']),None)
    if actual is None or (plan['stage']=='draft' and actual.get('decoder_layers') != 36):
        raise ValueError('Expected model/36-layer decoder is not reported by the actual endpoint')
    for folder in ('jobs','requests','uploads','metadata','logs'):
        (directory/folder).mkdir(parents=True,exist_ok=True)
    save(directory/'metadata/models.json',models)
    save(directory/'metadata/health-start.json',api.json('GET','/../health'))
    state_file = directory/'run.json'
    plan_hash = sha(plan_file)
    state = read(state_file) if state_file.exists() else {'startedAt':now(),'planSha256':plan_hash}
    if state['planSha256'] != plan_hash:
        raise ValueError('Use a new run directory for changed plans')
    state.update(status='generating',stage=plan['stage'],model=plan['model'],workerSha256=sha(__file__))
    save(state_file,state)
    target = select_target_shots(plan['shots'],args.order,args.limit,args.skip)
    state['excludedShots'] = args.skip.split(',') if args.skip else []
    receipts = {}
    for shot in target:
        path = directory/'jobs'/f"{shot['id']}.json"
        receipts[shot['id']] = read(path) if path.exists() else {'shotId':shot['id'],'status':'prepared'}
    upload_paths = {str(path):path for path in assets}
    for shot in plan['shots']:
        if plan['stage']=='draft':
            for relative in shot['references']:
                upload_paths[relative] = contained(args.episode.resolve().parent,relative)
            if shot.get('motionReference'):
                upload_paths[shot['motionReference']] = contained(directory,shot['motionReference'])
        else:
            upload_paths[shot['inputSource']] = contained(directory,shot['inputSource'])

    def upload(relative):
        path = upload_paths[relative]
        digest = sha(path)
        if digest != snapshots[path]:
            raise ValueError('An input changed since the formal review gate')
        cache = directory/'uploads'/f'{digest}.json'
        record = read(cache) if cache.exists() else None
        if record is None:
            result = api.upload(path)
            if not re.fullmatch(r'[A-Za-z0-9_-]+',result.get('id','')):
                raise ValueError('Invalid uploaded file identifier')
            record = {'sha256':digest,'server':api.base,'response':result,'uploadedAt':now()}
            save(cache,record)
        if record['server'] != api.base:
            raise ValueError('Upload cache belongs to another endpoint')
        return {'file_id':record['response']['id']}

    def inspect_source(shot, source):
        import review_reference_clips
        review_reference_clips.inspect(source,{**shot,'seconds':shot.get('sourceSeconds',5)},args.evidence.resolve(),
                                       directory/'clip-inspection',args.face_model.resolve())

    try:
        while True:
            if sha(plan_file) != plan_hash:
                raise ValueError('Plan changed during production')
            running = sum(row['status'] not in ('prepared','completed') for row in receipts.values())
            for shot in target:
                row = receipts[shot['id']]
                receipt_file = directory/'jobs'/f"{shot['id']}.json"
                if row['status']=='completed':
                    if sha(directory/row['sourceFile']) != row['sourceSha256']:
                        raise ValueError('Completed local source changed')
                    inspect_source(shot,directory/row['sourceFile'])
                    continue
                if row['status'] in ('failed','cancelled','submission-uncertain','submitting'):
                    raise RuntimeError(f"{shot['id']} has {row['status']}; retained evidence requires inspection")
                if row['status']=='prepared':
                    if running >= args.window:
                        continue
                    payload = payload_for(plan,shot,upload)
                    request_file = directory/'requests'/f"{shot['id']}.json"
                    if request_file.exists() and read(request_file) != payload:
                        raise ValueError('Request changed; preserve this run and use a new one')
                    save(request_file,payload)
                    row.update(requestSha256=sha(request_file),planSha256=plan_hash)
                    if not submit(api,'/videos' if plan['stage']=='draft' else '/videos/regenerations',payload,receipt_file,row):
                        continue
                    running += 1
                    print(f"{shot['id']} submitted {row['jobId']}",flush=True)
                remote = api.json('GET',f"/videos/{row['jobId']}")
                with (directory/'logs'/f"{shot['id']}-polls.jsonl").open('a',encoding='utf-8') as log:
                    log.write(json.dumps({'at':now(),'response':remote},ensure_ascii=False)+'\n')
                changed = row['status'] != remote['status']
                row.update(status='download_pending' if remote['status']=='completed' else remote['status'],
                           remote=remote,updatedAt=now())
                if remote['status']=='in_progress' and not row.get('firstInProgressAt'):
                    row['firstInProgressAt'] = now()
                save(receipt_file,row)
                if changed:
                    print(f"{shot['id']} {remote['status']}",flush=True)
                if remote['status']=='completed':
                    raw,source,probe = publish_result(api,remote,shot,directory,plan['sourceSize'])
                    row.update(status='completed',rawFile=raw.relative_to(directory).as_posix(),rawSha256=sha(raw),
                               sourceFile=source.relative_to(directory).as_posix(),sourceSha256=sha(source),
                               downloadedAt=now(),nativeProbe=probe,semanticReview='pending')
                    try:
                        with api.request('GET',f'/videos/{remote["id"]}/logs',timeout=30) as response:
                            server_log = directory/'logs'/f"{shot['id']}-server.log"
                            server_log.write_bytes(response.read())
                            row['serverLogSha256'] = sha(server_log)
                    except Exception as error:
                        row['serverLogFetchError'] = str(error)
                    save(receipt_file,row)
                    running -= 1
                    # The full source is inspected, including material that is
                    # shortened in the final cut but may be passed to 2K.
                    inspect_source(shot,source)
                elif remote['status'] in ('failed','cancelled'):
                    raise RuntimeError(f"{shot['id']} remote {remote['status']}: {remote.get('error')}")
            complete = sum(row['status']=='completed' and bool(row.get('sourceSha256')) for row in receipts.values())
            state.update(updatedAt=now(),completedSources=complete,totalShots=len(plan['shots']),
                         targetSources=len(target),generationPercent=round(100*complete/len(plan['shots']),2),
                         semanticReview='pending',humanFullPlayback=False)
            save(state_file,state)
            if complete == len(target):
                break
            time.sleep(args.poll_seconds)
        state.update(status='sources-completed-semantic-review-pending',finishedAt=now())
        save(state_file,state)
        print(json.dumps(state,ensure_ascii=True),flush=True)
    except BaseException as error:
        state.update(status='interrupted-or-failed',updatedAt=now(),error=str(error),
                     recovery='Server task IDs and full requests retained; no other remote task cancelled.')
        save(state_file,state)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--episode',required=True,type=Path)
    parser.add_argument('--plan',required=True,type=Path)
    parser.add_argument('--directory',required=True,type=Path)
    parser.add_argument('--api',required=True)
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--face-model',required=True,type=Path)
    parser.add_argument('--window',type=int,default=3,choices=range(1,9))
    parser.add_argument('--limit',type=int)
    parser.add_argument('--order',default='')
    parser.add_argument('--skip',default='',help='Preserve but do not submit these shots; replacement plans are reviewed separately')
    parser.add_argument('--poll-seconds',type=float,default=8)
    args = parser.parse_args()
    generate(args)
