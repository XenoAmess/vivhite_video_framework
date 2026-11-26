"""Per-shot Pipa production on the LAN video gateway. GPL-3.0-only."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback
import wave

import local_video_pipeline as video


SIZE = '1344x768'
FPS = 24
PICTURE_TIMESCALE = 12288
MODEL_FRAMES = 120
EPISODE = 'pipa/versus/01-shenyin-heiyan-vs-xuren-meng'
CAPACITY = 32
POLL_SECONDS = 60


def ff(*args, timeout=600):
    return video.run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', *map(str,args)], timeout=timeout)


def probe(path):
    return json.loads(video.run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams',
                                 '-show_format', '-of', 'json', str(path)], timeout=600))


def verify_picture(path, frames, size):
    streams = probe(path)['streams']
    picture = streams[0]
    if (len(streams) != 1 or picture['codec_type'] != 'video'
            or f"{picture['width']}x{picture['height']}" != size or picture['avg_frame_rate'] != '24/1'
            or int(picture['nb_read_frames']) != frames):
        raise ValueError(f'Unexpected video timing or format in {path.name}')
    ff('-xerror', '-i', path, '-f', 'null', '-')


def validate(plan, manifest):
    if (plan.get('schemaVersion') != 'vivhite-shotwise-video-1'
            or (plan['width'],plan['height'],plan['referenceFps'],plan['outputFps']) != (1344,768,FPS,FPS)
            or plan['authorization']['scope'] != EPISODE
            or '/'.join(manifest[key] for key in ('series','topic','id')) != EPISODE
            or manifest['characterBasis'] != 'user-authorized-visuals-and-role-mapping-for-this-episode'
            or set(manifest['cast']) != {item['id'] for item in plan['characters'].values()}
            or plan['authorization']['roles'] != {role:item['id'] for role,item in plan['characters'].items()}
            or plan['source']['storyFrameInterval'] != [0,plan['totalFrames']]):
        raise ValueError('The actual episode, authorization, size or source interval does not match')
    expected = 0
    previous_id = 'S00'
    for shot in plan['shots']:
        if (not re.fullmatch(r'S[0-9]{2}',shot['id']) or shot['id'] <= previous_id
                or shot['startFrame'] != expected
                or type(shot['endFrame']) is not int or shot['endFrame'] <= expected
                or not shot['cast'] or len(set(shot['cast'])) != len(shot['cast'])
                or not set(shot['cast']) <= set(plan['characters']) or not shot['direction'].strip()):
            raise ValueError('The shot list must cover a contiguous timeline with known visible roles')
        expected = shot['endFrame']
        previous_id = shot['id']
    if expected != plan['totalFrames']:
        raise ValueError('The shots do not cover the full story')


def normalized_filter(in_frames, out_frames):
    return (f'setpts=(PTS-STARTPTS)*{out_frames}/{in_frames},fps=24,'
            f'tpad=stop_mode=clone:stop_duration=5,trim=end_frame={out_frames},setpts=N/(24*TB)')


def transcode_picture(source, output, filters, frames, size):
    if output.exists():
        verify_picture(output,frames,size)
        return
    partial = output.with_name(output.stem+f'.{time.time_ns()}.partial.mp4')
    ff('-n','-i',source,'-map','0:v:0','-an','-vf',filters,'-frames:v',frames,
       '-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p',
       '-video_track_timescale',PICTURE_TIMESCALE,'-movflags','+faststart',partial)
    verify_picture(partial,frames,size)
    partial.replace(output)


def asset(path):
    return {'path':str(path.resolve()),'sha256':video.sha(path)}


def check_asset(entry):
    path = Path(entry['path'])
    if video.sha(path) != entry['sha256']:
        raise ValueError(f'Prepared input changed: {path.name}')
    return path


def sync_soundtrack(root, prepared, timing_path):
    timing = video.read(timing_path)
    plan = video.read(check_asset(prepared['plan']))
    soundtrack = plan['soundtrack']
    sample_rate = 48000
    samples_per_frame = sample_rate // FPS
    crossfade = timing['crossfadeSamplesAt48k']
    output_samples = prepared['totalFrames'] * samples_per_frame
    source_samples = round(timing['sourceAudioEndSeconds'] * sample_rate)
    if (timing['schemaVersion'] != 'vivhite-pipa-soundtrack-sync-1'
            or (timing['videoId'],timing['part']) != (soundtrack['videoId'],soundtrack['part'])
            or timing['editFramesPerSecond'] != FPS
            or soundtrack['startSeconds'] != 0 or timing['sourceAudioEndSeconds'] != soundtrack['endSeconds']
            or not 0 < crossfade < samples_per_frame or crossfade % 2
            or not timing['anchors']):
        raise ValueError('The soundtrack anchors must match this edition and picture timeline')
    shot_starts = {shot['id']:shot['startFrame'] for shot in prepared['shots']}
    if any(shot_starts.get(point['shot']) != point['originalFrame'] for point in timing['anchors']):
        raise ValueError('A soundtrack anchor does not match its actual picture cut')
    boundaries = [(0,0)]
    boundaries.extend((point['originalFrame']*samples_per_frame,point['editFrame']*samples_per_frame)
                      for point in timing['anchors'])
    boundaries.append((output_samples,source_samples))
    segments = list(zip(boundaries,boundaries[1:]))
    if any(picture_to-picture_from <= crossfade or audio_to-audio_from <= crossfade
           for (picture_from,audio_from),(picture_to,audio_to) in segments):
        raise ValueError('Soundtrack anchors must increase on both timelines')
    if (root/'pipa-768p.mp4').exists():
        raise ValueError('Use a new production directory to change an assembled soundtrack')

    filters = [f"[0:a:0]aresample={sample_rate},apad=pad_len={sample_rate},asplit={len(segments)}"
               + ''.join(f'[aligned-input-{index}]' for index in range(len(segments)))]
    for index,((picture_from,audio_from),(picture_to,audio_to)) in enumerate(segments):
        tempo = (audio_to-audio_from)/(picture_to-picture_from)
        leading = crossfade//2 if index else 0
        trailing = crossfade//2 if index < len(segments)-1 else 0
        first = audio_from-round(tempo*leading)
        # The ahead samples let atempo complete the overlap before trimming its output.
        last = min(audio_to+round(tempo*trailing)+4096,source_samples+4096)
        length = picture_to-picture_from+leading+trailing
        filters.append(f'[aligned-input-{index}]atrim=start_sample={first}:end_sample={last},'
                       f'asetpts=PTS-STARTPTS,atempo={tempo:.12f},apad=whole_len={length},'
                       f'atrim=end_sample={length},asetpts=N/SR/TB[aligned-part-{index}]')
    filters.append(''.join(f'[aligned-part-{index}]' for index in range(len(segments)))
                   + f'acrossfade=n={len(segments)}:ns={crossfade}:c1=tri:c2=tri[aligned]')
    audio = check_asset(prepared['soundtrackSource'])
    timing_input = asset(timing_path)
    output = root/f"soundtrack-cut-sync-{timing_input['sha256'][:12]}.wav"
    if not output.exists():
        partial = output.with_name(output.stem+f'.{time.time_ns()}.partial.wav')
        ff('-n','-i',audio,'-filter_complex',';'.join(filters),'-map','[aligned]','-c:a','pcm_s16le','-ac','2',partial)
        with wave.open(str(partial),'rb') as track:
            if (track.getframerate(),track.getnchannels(),track.getnframes()) != (sample_rate,2,output_samples):
                raise ValueError('Audio alignment did not cover the exact picture timeline')
        partial.replace(output)
    with wave.open(str(output),'rb') as track:
        if (track.getframerate(),track.getnchannels(),track.getnframes()) != (sample_rate,2,output_samples):
            raise ValueError('Existing aligned audio does not match the picture timeline')
    ff('-xerror','-i',output,'-f','null','-')
    prepared['soundtrack'] = asset(output)
    prepared['soundtrackTiming'] = timing_input
    video.save(root/'prepared.json',prepared)
    print(output, flush=True)


def prepare(args, root):
    args.episode = args.episode.resolve()
    args.plan = args.plan.resolve()
    plan = video.read(args.plan)
    manifest = video.read(args.episode)
    validate(plan,manifest)
    if root.is_relative_to(args.episode.parents[5]):
        raise ValueError('Keep production media outside the source repository')
    if (video.sha(args.original) != plan['source']['expectedSha256']
            or video.sha(args.soundtrack) != plan['soundtrack']['expectedSha256']):
        raise ValueError('The two selected source files do not match the production plan')
    config_file = root/'prepared.json'
    if config_file.exists():
        raise ValueError('Use a new run directory for a new prepared plan')
    root.mkdir(parents=True,exist_ok=True)
    refs = root/'references'
    refs.mkdir(exist_ok=True)
    normalized = root/'source-original-24fps.mp4'
    if not normalized.exists():
        ff('-n','-i',args.original,'-map','0:v:0','-an','-vf','fps=24,scale=960:540:flags=lanczos',
           '-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',normalized)
    original_probe = probe(normalized)
    if (len(original_probe['streams']) != 1 or original_probe['streams'][0]['avg_frame_rate'] != '24/1'
            or int(original_probe['streams'][0]['nb_read_frames']) < plan['totalFrames']):
        raise ValueError('The normalized original does not cover the story')

    soundtrack = root/'soundtrack.wav'
    seconds = plan['totalFrames']/FPS
    audio_end = plan['soundtrack']['endSeconds']
    audio_start = plan['soundtrack']['startSeconds']
    tempo = (audio_end-audio_start)/seconds
    ff('-n','-ss',audio_start,'-i',args.soundtrack,'-map','0:a:0','-vn','-af',
       f'atrim=duration={audio_end-audio_start},asetpts=PTS-STARTPTS,aresample=48000,'
       f'atempo={tempo:.12f},apad=whole_dur={seconds:.9f},atrim=duration={seconds:.9f}',
       '-c:a','pcm_s16le',soundtrack)
    characters = {key:asset(video.contained(args.episode.parent,item['reference']))
                  for key,item in plan['characters'].items()}
    anchors = {}
    for identifier,path in (('S11',args.rear_anchor),('S12',args.reaction_anchor)):
        if path:
            anchors[identifier] = asset(path)
    rows = []
    for shot in plan['shots']:
        identifier = shot['id']
        start,end = shot['startFrame'],shot['endFrame']
        frames = end-start
        original = refs/f'{identifier}-original.mp4'
        reference = refs/f'{identifier}-model.mp4'
        transcode_picture(normalized,original,f'trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS',
                          frames,'960x540')
        transcode_picture(original,reference,normalized_filter(frames,MODEL_FRAMES),MODEL_FRAMES,'960x540')
        layouts = [characters[role] for role in shot['cast']]
        role_text = ' '.join(f'<Picture {i}> is the exact identity for {plan["characters"][role]["appearance"]}.'
                             for i,role in enumerate(shot['cast'],1))
        anchor_text = ''
        if identifier in anchors:
            layouts.append(anchors[identifier])
            anchor_text = f' <Picture {len(layouts)}> shows the desired pose and framing for this same character.'
        prompt = (
            'Render ONE continuous cel-shaded 2D anime shot, using <Video 1> as the motion and camera guide. '
            'Follow the movement, viewpoint and camera direction from this source shot. Replace the original '
            '3D source characters in every frame, including the first and last frames. ' + role_text + anchor_text
            + ' ' + shot['direction'] + ' Keep the same pose timing and camera, with no added cuts or stray characters. '
            'Fully clothed comic animation. Any stage prop is openly stylized, with abstract theatrical lighting. '
            'Keep each intended hairstyle and costume legible, including when a character is shown from behind. '
            'No added words, watermarks, subtitles or dialogue.'
        )
        rows.append({**shot,'frames':frames,'original':asset(original),'motion':asset(reference),
                     'images':layouts,'prompt':prompt,'seed':1234})
    prepared = {'schemaVersion':'vivhite-shotwise-prepared-1','plan':asset(args.plan),
                'episode':asset(args.episode),'original':asset(args.original),
                'soundtrackSource':asset(args.soundtrack),'soundtrack':asset(soundtrack),
                'totalFrames':plan['totalFrames'],'shots':rows}
    video.save(config_file,prepared)
    print(f'Prepared {len(rows)} distinct shots, {plan["totalFrames"]} output frames',flush=True)


def latest(root, shot):
    parent = root/'shots'/shot['id']
    parent.mkdir(parents=True,exist_ok=True)
    active = sorted(path for path in parent.glob('attempt-[0-9][0-9][0-9]') if path.is_dir())
    return active[-1] if active else parent/'attempt-001'

def selected_shot(prepared, identity):
    shot = next((s for s in prepared['shots'] if s['id']==identity),None)
    if shot is None:
        raise ValueError('Unknown shot')
    return shot


def retry(args, root, prepared):
    shot = selected_shot(prepared,args.shot)
    current = latest(root,shot)
    receipt = video.read(current/'job.json')
    if receipt['status'] not in ('completed','failed','cancelled'):
        raise ValueError('A previous attempt is still active or its submission needs reconciliation')
    prompt = args.prompt_file.read_text(encoding='utf-8-sig').strip()
    if not prompt:
        raise ValueError('Provide the full new prompt')
    if args.replace_layouts and not args.anchor:
        raise ValueError('Provide an anchor to replace the prepared layouts')
    revision = {'prompt':prompt,'seed':args.seed,'additionalImages':[asset(path) for path in args.anchor],
                'previousAttempt':current.name,'recordedAt':video.now()}
    if args.replace_layouts:
        revision['replacePreparedLayouts'] = True
    next_attempt = current.with_name(f'attempt-{int(current.name.removeprefix("attempt-"))+1:03}')
    next_attempt.mkdir()
    video.save(next_attempt/'retry.json',revision)
    print(next_attempt)


def review_binding(attempt, shot):
    receipt = video.read(attempt/'job.json')
    picture = attempt/'cut.mp4'
    if (receipt['status']!='completed' or receipt['cutFrames']!=shot['frames']
            or receipt['cutSha256']!=video.sha(picture)
            or receipt['requestSha256']!=video.sha(attempt/'request.json')):
        raise ValueError('The complete candidate and actual request must match the attempt receipt')
    return {'cutSha256':receipt['cutSha256'],'requestSha256':receipt['requestSha256'],
            'originalSha256':shot['original']['sha256']}


def compare_shot(root, shot):
    attempt = latest(root,shot)
    binding = review_binding(attempt,shot)
    original = check_asset(shot['original'])
    candidate = attempt/'cut.mp4'
    output = attempt/'comparison'
    output.mkdir(exist_ok=True)
    manifest = output/'frames.json'
    count = (shot['frames']+15)//16
    pages = sorted(output.glob('side-by-side-*.jpg'))
    if not manifest.exists() or video.read(manifest)!=binding or len(pages)!=count:
        views = ('[0:v]scale=232:132[left];[1:v]scale=232:132[right];'
                 '[left][right]hstack=inputs=2,tile=4x4:padding=1:margin=1[review]')
        ff('-y','-i',original,'-i',candidate,'-filter_complex',views,'-map','[review]',
           '-q:v','2',output/'side-by-side-%02d.jpg')
        if len(list(output.glob('side-by-side-*.jpg')))!=count:
            raise ValueError('Comparison pages do not cover the whole shot')
        video.save(manifest,binding)
    print(output)


def record_review(args, root, shot):
    attempt = latest(root,shot)
    report = attempt/'review.json'
    if report.exists():
        raise ValueError('Preserve this review and use a new attempt for a changed candidate')
    binding = review_binding(attempt,shot)
    check_asset(shot['original'])
    if video.read(attempt/'comparison/frames.json')!=binding or args.frames!=shot['frames']:
        raise ValueError('The source and candidate must be compared for every delivered frame')
    notes = args.observations.read_text(encoding='utf-8-sig').strip()
    if not notes:
        raise ValueError('Record what was actually observed in the reviewed frames')
    video.save(report,{**binding,'decision':args.decision,'reviewedFrames':args.frames,
                       'method':args.method,'observations':notes,'reviewedAt':video.now()})


def uploaded(api, root, entry):
    path = check_asset(entry)
    cache = root/'uploads'/f"{entry['sha256']}.json"
    if cache.exists():
        existing = video.read(cache)
        if existing['server'] != api.base:
            raise ValueError('The upload cache belongs to a different gateway')
        return {'file_id':existing['response']['id']}
    response = api.upload(path)
    if not re.fullmatch(r'[a-zA-Z0-9_-]+',response.get('id','')):
        raise ValueError('Unexpected uploaded media ID')
    video.save(cache,{'sha256':entry['sha256'],'server':api.base,'response':response,'uploadedAt':video.now()})
    return {'file_id':response['id']}


def post(api, root, shot, attempt):
    revision = shot if attempt.name=='attempt-001' else video.read(attempt/'retry.json')
    prepared_images = shot['images']
    if revision.get('replacePreparedLayouts'):
        prepared_images = prepared_images[:len(shot['cast'])]
    references = [*prepared_images,*revision.get('additionalImages',[])]
    payload = {'model':'fasth3-omni-bf16','task':'ref2va','size':SIZE,'seconds':5,'num_inference_steps':8,
               'guidance_scale':1.0,'seed':revision['seed'],'prompt':revision['prompt'],
               'video_reference':[uploaded(api,root,shot['motion'])],
               'image_reference':[uploaded(api,root,entry) for entry in references]}
    path = attempt/'request.json'
    if path.exists() and video.read(path) != payload:
        raise ValueError('Preserve the exact request of each attempt')
    video.save(path,payload)
    receipt = {'shotId':shot['id'],'status':'prepared','requestSha256':video.sha(path)}
    return video.submit(api,'/videos',payload,attempt/'job.json',receipt)


def download(api, shot, attempt, remote, receipt):
    raw, picture, inspection = video.publish_result(api,remote,{'id':shot['id']},attempt,SIZE)
    final = attempt/'cut.mp4'
    transcode_picture(picture,final,normalized_filter(MODEL_FRAMES,shot['frames']),shot['frames'],SIZE)
    pages = sorted(attempt.glob('review-frames-*.jpg'))
    if len(pages) != (shot['frames']+29)//30:
        ff('-y','-i',final,'-map','0:v:0','-vf','scale=224:128,tile=6x5:padding=1:margin=1',
           '-q:v','2',attempt/'review-frames-%02d.jpg')
    receipt.update(status='completed',rawSha256=video.sha(raw),normalizedSha256=video.sha(picture),
                   cutSha256=video.sha(final),cutFrames=shot['frames'],downloadedAt=video.now(),
                   semanticReview='pending',nativeProbe=inspection)
    video.save(attempt/'job.json',receipt)
    print(f"{shot['id']} {attempt.name} ready for visual review",flush=True)


def generate(base, root, prepared):
    api = video.Api(base)
    catalog = api.json('GET','/models')
    model = video.validate_server_model({'stage':'draft','model':'fasth3-omni-bf16'},catalog)
    if 'reference_video' not in model.get('capabilities',[]):
        raise ValueError('The endpoint does not advertise video references')
    video.save(root/'models.json',catalog)
    while True:
        if (root/'stop.json').exists():
            print('Local stop marker present. Known remote jobs remain recorded.',flush=True)
            return
        rows = []
        for shot in prepared['shots']:
            attempt = latest(root,shot)
            receipt = video.read(attempt/'job.json') if (attempt/'job.json').exists() else {'status':'prepared'}
            rows.append((shot,attempt,receipt))
        queue = api.json('GET','/queue')
        queue_full = queue.get('maintenance',{}).get('enabled',False)
        waiting = {item['id'] for group in ('queued','waiting_for_source') for item in queue.get(group,[])}
        unfinished = sum(bool(r.get('jobId')) and r['status'] not in ('completed','failed','cancelled')
                         for _,_,r in rows)
        for shot,attempt,receipt in rows:
            status = receipt['status']
            if status in ('prepared','completed','failed','cancelled','submitting','submission-uncertain'):
                continue
            identity = receipt['jobId']
            if video.queue_job_id(identity) in waiting:
                continue
            remote = api.json('GET',f'/videos/{identity}')
            with (attempt/'polls.jsonl').open('a',encoding='utf-8') as log:
                log.write(json.dumps({'at':video.now(),'response':remote},ensure_ascii=False)+'\n')
            receipt.update(status=remote['status'],remote=remote)
            if remote['status']=='completed':
                receipt['status'] = 'download_pending'
                video.save(attempt/'job.json',receipt)
                try:
                    download(api,shot,attempt,remote,receipt)
                except (OSError,RuntimeError) as error:
                    # Fetch and media probes can be repeated using the same remote job.
                    receipt['lastDownloadError'] = {'at':video.now(),'detail':str(error) or repr(error)}
                    video.save(attempt/'job.json',receipt)
                    print(f"{shot['id']} result needs another download or probe: {type(error).__name__}: {error}",
                          flush=True)
                    continue
                unfinished -= 1
            else:
                video.save(attempt/'job.json',receipt)
                if remote['status'] in ('failed','cancelled'):
                    unfinished -= 1
                    print(f"{shot['id']} stopped with remote status {remote['status']}",flush=True)
        # Collect finished jobs first, then fill the newly freed slots in shot
        # order so an earlier retake cannot be starved by later prepared shots.
        for shot,attempt,receipt in rows:
            if unfinished >= CAPACITY or queue_full:
                break
            if receipt['status']!='prepared':
                continue
            attempt.mkdir(parents=True,exist_ok=True)
            try:
                if post(api,root,shot,attempt):
                    unfinished += 1
                    receipt.update(video.read(attempt/'job.json'))
                    print(f"{shot['id']} {attempt.name} queued as {receipt['jobId']}",flush=True)
                else:
                    queue_full = True
            except (OSError,RuntimeError,ValueError) as error:
                # If POST was ambiguous, video.submit has already journaled it.
                print(f"{shot['id']} {attempt.name}: {type(error).__name__}: {error}",flush=True)
                if not (attempt/'job.json').exists():
                    queue_full = True
        counts = {}
        reviews = {}
        for _,attempt,receipt in rows:
            status = video.read(attempt/'job.json')['status'] if (attempt/'job.json').exists() else receipt['status']
            counts[status] = counts.get(status,0)+1
            if status == 'completed':
                review_path = attempt/'review.json'
                decision = video.read(review_path)['decision'] if review_path.exists() else 'pending'
                reviews[decision] = reviews.get(decision,0)+1
        active = sum(counts.get(key,0) for key in ('prepared','queued','in_progress','download_pending'))
        video.save(root/'progress.json',{'at':video.now(),'totalShots':len(rows),'counts':counts,'visualReviews':reviews,
                                         'status':'rendering' if active else 'awaiting-shot-review-or-repair'})
        if active == 0:
            return
        time.sleep(POLL_SECONDS)


def write_picture_concat(path, clips):
    lines = ['ffconcat version 1.0']
    frames = elapsed = 0
    for picture, count in clips:
        frames += count
        endpoint = (frames * 1_000_000 + FPS // 2) // FPS
        seconds, micros = divmod(endpoint - elapsed, 1_000_000)
        quoted = picture.as_posix().replace("'", "'\\''")
        # MP4 container durations can be rounded to milliseconds. Use the
        # cumulative frame clock for each boundary and keep the encoded frames.
        lines.extend((f"file '{quoted}'", f'duration {seconds}.{micros:06d}'))
        elapsed = endpoint
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')


def verify_picture_clock(path, frame_count):
    result = json.loads(video.run([
        'ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_packets',
        '-show_entries', 'stream=time_base:packet=pts', '-of', 'json', str(path),
    ], timeout=600))
    ticks = PICTURE_TIMESCALE // FPS
    expected = list(range(0, frame_count * ticks, ticks))
    actual = sorted(int(packet['pts']) for packet in result['packets'])
    if result['streams'][0]['time_base'] != f'1/{PICTURE_TIMESCALE}' or actual != expected:
        raise ValueError('The assembled picture has uneven presentation timestamps')


def finish(root, prepared):
    films = []
    for shot in prepared['shots']:
        attempt = latest(root,shot)
        picture = attempt/'cut.mp4'
        review = video.read(attempt/'review.json')
        binding = review_binding(attempt,shot)
        if (review['decision']!='accepted' or review['reviewedFrames']!=shot['frames']
                or any(review.get(key)!=value for key,value in binding.items())):
            raise ValueError(f"Missing or stale visual acceptance for {shot['id']}")
        verify_picture(picture,shot['frames'],SIZE)
        films.append((picture, shot['frames']))
    audio = check_asset(prepared['soundtrack'])
    if 'soundtrackTiming' in prepared:
        check_asset(prepared['soundtrackTiming'])
    concat = root/'approved-shots.ffconcat'
    write_picture_concat(concat, films)
    output = root/'pipa-768p.mp4'
    if output.exists():
        raise ValueError('This production has already been assembled')
    partial = root/f'pipa-768p-{time.time_ns()}.partial.mp4'
    seconds = prepared['totalFrames']/FPS
    ff('-n','-f','concat','-safe','0','-i',concat,'-i',audio,'-map','0:v:0','-map','1:a:0',
       '-c:v','copy','-video_track_timescale',PICTURE_TIMESCALE,'-c:a','aac','-b:a','192k',
       '-t',f'{seconds:.9f}','-movflags','+faststart',partial)
    ff('-xerror','-i',partial,'-f','null','-')
    streams = probe(partial)['streams']
    picture,sound = streams
    if (int(picture['nb_read_frames'])!=prepared['totalFrames'] or picture['avg_frame_rate']!='24/1'
            or (picture['width'],picture['height'])!=(1344,768) or sound['codec_type']!='audio'
            or abs(float(sound['duration'])-seconds)>1/FPS):
        raise ValueError('The complete film does not match the reviewed timeline')
    verify_picture_clock(partial, prepared['totalFrames'])
    video.save(root/'final-receipt.json',{'artifact':{'path':str(output),'sha256':video.sha(partial)},
                                         'frames':prepared['totalFrames'],
                                         'seconds':seconds,'audioVideoCompleteDecode':'passed',
                                         'shots':len(films),'createdAt':video.now(),
                                         'soundtrackSha256':prepared['soundtrack']['sha256'],
                                         'soundtrackTimingSha256':prepared.get('soundtrackTiming',{}).get('sha256')})
    partial.replace(output)
    video.save(root/'progress.json',{'at':video.now(),'totalShots':len(films),'status':'assembled'})


def run_scheduled(base, root, config):
    import msvcrt
    with (root/'worker.lock').open('a+b') as lock, (root/'worker.log').open('a',encoding='utf-8',buffering=1) as log:
        if not lock.tell():
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:
            return
        with redirect_stdout(log),redirect_stderr(log):
            try:
                progress_file = root/'progress.json'
                if (root/'pipa-768p.mp4').exists() and (root/'final-receipt.json').exists():
                    if not progress_file.exists() or video.read(progress_file)['status']!='assembled':
                        check_asset(video.read(root/'final-receipt.json')['artifact'])
                        video.save(progress_file,{'at':video.now(),'totalShots':len(config['shots']),'status':'assembled'})
                    return
                if progress_file.exists() and video.read(progress_file)['status']=='awaiting-shot-review-or-repair':
                    attempts = [latest(root,shot) for shot in config['shots']]
                    done = [attempt/'job.json' for attempt in attempts]
                    terminal = ('completed','failed','cancelled','submitting','submission-uncertain')
                    if all(path.exists() and video.read(path)['status'] in terminal for path in done):
                        if (not (root/'pipa-768p.mp4').exists()
                                and all((attempt/'review.json').exists()
                                        and video.read(attempt/'review.json').get('decision')=='accepted'
                                        for attempt in attempts)):
                            finish(root,config)
                        return
                generate(base,root,config)
            except Exception as error:
                print(f'{video.now()} worker interrupted: {type(error).__name__}: {error}',flush=True)
                traceback.print_exc()
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True,type=Path)
    sub = parser.add_subparsers(dest='command',required=True)
    prep = sub.add_parser('prepare')
    for name in ('episode','plan','original','soundtrack'):
        prep.add_argument('--'+name,required=True,type=Path)
    prep.add_argument('--rear-anchor',type=Path)
    prep.add_argument('--reaction-anchor',type=Path)
    render = sub.add_parser('render')
    render.add_argument('--api',default=video.DEFAULT_API)
    render.add_argument('--scheduled',action='store_true')
    render.add_argument('--tool-directory',type=Path)
    soundtrack = sub.add_parser('sync-soundtrack')
    soundtrack.add_argument('--timing',required=True,type=Path)
    ret = sub.add_parser('retry')
    ret.add_argument('--shot',required=True)
    ret.add_argument('--prompt-file',required=True,type=Path)
    ret.add_argument('--seed',required=True,type=int)
    ret.add_argument('--anchor',action='append',type=Path,default=[])
    ret.add_argument('--replace-layouts',action='store_true',
                     help='Replace prepared layout images and keep the cast reference images')
    comparison = sub.add_parser('compare')
    comparison.add_argument('--shot',required=True)
    review = sub.add_parser('review')
    review.add_argument('--shot',required=True)
    review.add_argument('--decision',required=True,choices=('accepted','rejected'))
    review.add_argument('--frames',required=True,type=int)
    review.add_argument('--method',required=True,choices=('assistant-frame-review','human-playback-review'))
    review.add_argument('--observations',required=True,type=Path)
    sub.add_parser('finish')
    args = parser.parse_args()
    root = args.directory.resolve()
    if args.command=='prepare':
        prepare(args,root)
        return
    config = video.read(root/'prepared.json')
    if config['schemaVersion']!='vivhite-shotwise-prepared-1':
        raise ValueError('Unsupported prepared run')
    check_asset(config['plan'])
    check_asset(config['episode'])
    if args.command=='render':
        if args.tool_directory:
            os.environ['PATH'] = str(args.tool_directory.resolve())+os.pathsep+os.environ.get('PATH','')
        if args.scheduled:
            run_scheduled(args.api,root,config)
        else:
            generate(args.api,root,config)
    elif args.command=='retry':
        retry(args,root,config)
    elif args.command=='sync-soundtrack':
        sync_soundtrack(root,config,args.timing.resolve())
    elif args.command=='compare':
        compare_shot(root,selected_shot(config,args.shot))
    elif args.command=='review':
        record_review(args,root,selected_shot(config,args.shot))
    else:
        finish(root,config)


if __name__ == '__main__':
    main()
