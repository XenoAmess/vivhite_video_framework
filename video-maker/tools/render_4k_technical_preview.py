"""Build an explicitly unreviewed UHD preview after all source jobs finish.

Checks the approved generation inputs and technical source identity. This entry
cannot issue semantic approvals, create film.mp4 or publish a formal release.
GPL-3.0-only.
"""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from local_video_pipeline import read, save, input_assets, validate, now, source_frame_count, contained
from reference_finisher import sha, run, titles


def probe(path):
    return json.loads(run(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(path)],timeout=1800))


def selected_source(directory, shot, job, plan_digest):
    original = contained(directory,f"sources/{shot['id']}.mp4")
    selection_file = directory/'source-selections.json'
    selections = read(selection_file) if selection_file.exists() else {}
    selected = selections.get('selections',{}).get(shot['id'])
    if not selected:
        return original,directory/'clip-inspection'/f"{shot['id']}.json"
    if selections.get('sourcePlanSha256') != plan_digest:
        raise ValueError('Corrected selection belongs to another source plan')
    source = contained(directory,selected['path'])
    parent = contained(directory,selected['parent'])
    receipt = read(contained(directory,selected['receipt']))
    digest = sha(source)
    decisions = read(directory/'clip-decisions.json')
    decision = next((row for row in decisions.get('shots',[]) if row['id'] == shot['id']),{})
    if (parent != original or sha(parent) != job.get('sourceSha256')
            or selected['parentSha256'] != job.get('sourceSha256') or selected['sha256'] != digest
            or receipt.get('sourceSha256') != selected['parentSha256']
            or receipt.get('correctedSha256') != digest
            or decisions.get('sourcePlanSha256') != plan_digest
            or decision.get('decision') != 'accepted' or decision.get('sourceSha256') != digest
            or decision.get('allSourceFrameReview') is not True
            or decision.get('reviewedNativeFrames') != source_frame_count(shot)
            or any(decision.get(key) != 'passed' for key in ('noHumanFaces','noAddedPeople',
                'allCharactersFemale','costumeStyle','motionAndContinuity','merchandiseBehavior','referenceAppearance'))):
        raise ValueError('Correction requires unchanged parent, receipt and actual complete-frame acceptance')
    return source,contained(directory,selected['inspectionReport'])


def build(config_file):
    config = read(config_file)
    root, directory = Path(config['root']).resolve(), Path(config['directory']).resolve()
    plan_file = Path(config['plan']).resolve()
    plan = read(plan_file)
    validate(plan)
    if (plan.get('stage') != 'refine' or plan['sourceSize'] != '3840x2160'
            or sha(plan_file) != config['planSha256']):
        raise ValueError('Only the frozen native UHD generation plan is allowed')
    preview = directory/'technical-preview'
    preview.mkdir(exist_ok=True)
    output = preview/'film-unreviewed.mp4'
    selection_file = directory/'source-selections.json'
    selection_digest = sha(selection_file) if selection_file.exists() else None
    if output.exists():
        receipt = read(preview/'receipt.json') if (preview/'receipt.json').exists() else {}
        if (receipt.get('sourcePlanSha256') == sha(plan_file) and receipt.get('filmSha256') == sha(output)
                and receipt.get('sourceSelectionsSha256') == selection_digest):
            print('Retaining the same completed unreviewed technical preview.',flush=True)
            return
        output.rename(preview/f'film-unreviewed-unbound-{time.time_ns()}.mp4')
        if (preview/'receipt.json').exists():
            (preview/'receipt.json').rename(preview/f'receipt-unbound-{time.time_ns()}.json')
    state_file = preview/'run.json'
    state = {'status':'generating','stage':'unreviewed-technical-preview','startedAt':now(),
        'productionPlanSha256':sha(plan_file),'formalDelivery':False,'semanticReview':'pending'}
    save(state_file,state)
    try:
        assets = input_assets(plan,Path(config['episode']),directory)
        gate = [sys.executable,str(root/'scripts/character_review.py'),'check','--episode',config['episode'],
                '--document',str(plan_file)]
        for path in assets:
            gate.extend(['--asset',str(path)])
        print(run(gate,timeout=120),flush=True)
        sources = []
        (preview/'segments').mkdir(exist_ok=True)
        for shot in plan['shots']:
            job = read(directory/'jobs'/f"{shot['id']}.json")
            original = contained(directory,f"sources/{shot['id']}.mp4")
            source,report_file = selected_source(directory,shot,job,sha(plan_file))
            report = read(report_file)
            digest = sha(source)
            if (job.get('status') != 'completed' or job.get('sourceSha256') != sha(original)
                    or job.get('planSha256') != sha(plan_file)
                    or report.get('status') != 'decoded' or report['identity']['sourceSha256'] != digest
                    or report['decodedFrames'] != source_frame_count(shot)):
                raise ValueError('Missing or stale complete native UHD source: '+shot['id'])
            streams = probe(source)['streams']
            if (len(streams) != 1 or streams[0].get('codec_type') != 'video'
                    or (streams[0]['width'],streams[0]['height'],streams[0]['avg_frame_rate'],
                        int(streams[0]['nb_read_frames'])) != (3840,2160,'24/1',source_frame_count(shot))):
                raise ValueError('Source is not the expected native UHD video-only interval')
            segment = preview/'segments'/f"{shot['id']}.mp4"
            receipt = segment.with_suffix('.json')
            identity = {'sourceSha256':digest,'frames':shot['seconds']*30,
                        'width':3840,'height':2160,'recipe':'fps30-x264-fast-crf17-1'}
            if segment.exists():
                if not receipt.exists():
                    segment.rename(segment.with_name(f'{segment.stem}-unbound-{time.time_ns()}.mp4'))
                elif read(receipt).get('identity') != identity or sha(segment) != read(receipt).get('sha256'):
                    raise ValueError('Existing preview segment changed; preserve it for inspection')
            if not segment.exists():
                partial = segment.with_suffix('.partial.mp4')
                if partial.exists():
                    partial.rename(partial.with_name(f'{partial.stem}-{time.time_ns()}.mp4'))
                run(['ffmpeg','-v','error','-y','-i',str(source),'-map','0:v:0','-an','-vf','fps=30',
                     '-frames:v',str(shot['seconds']*30),'-c:v','libx264','-preset','fast','-crf','17',
                     '-pix_fmt','yuv420p',str(partial)],timeout=3600)
                stream = probe(partial)['streams'][0]
                if (stream['width'],stream['height'],int(stream['nb_read_frames'])) != (3840,2160,identity['frames']):
                    raise ValueError('Preview segment has incorrect geometry or frame count')
                partial.replace(segment)
                save(receipt,{'identity':identity,'sha256':sha(segment)})
            sources.append({'id':shot['id'],'sourceSha256':digest,'segmentSha256':sha(segment)})
            state.update(completedSegments=len(sources),updatedAt=now());save(state_file,state)
        soundtrack = directory/'soundtrack.wav'
        if sha(soundtrack) != config['soundtrackSha256']:
            raise ValueError('Original soundtrack changed')
        if not (preview/'soundtrack.wav').exists():
            shutil.copyfile(soundtrack,preview/'soundtrack.wav')
        if sha(preview/'soundtrack.wav') != sha(soundtrack):
            raise ValueError('Preview audio differs from the retained original soundtrack')
        (preview/'titles.ass').write_text(titles(plan),encoding='utf-8-sig',newline='\n')
        if sha(preview/'titles.ass') != config['titlesSha256']:
            raise ValueError('Title text, style or timing changed')
        (preview/'segments.ffconcat').write_text('ffconcat version 1.0\n'+''.join(
            f"file 'segments/{s['id']}.mp4'\n" for s in plan['shots']),encoding='utf-8',newline='\n')
        picture = preview/'picture-assembly.mp4'
        picture_receipt = preview/'picture-assembly-receipt.json'
        picture_identity = {'sourcePlanSha256':sha(plan_file),'segments':[s['segmentSha256'] for s in sources]}
        if picture.exists():
            if not picture_receipt.exists():
                picture.rename(preview/f'picture-assembly-unbound-{time.time_ns()}.mp4')
            elif read(picture_receipt).get('identity') != picture_identity or read(picture_receipt).get('sha256') != sha(picture):
                raise ValueError('Existing preview picture assembly changed')
        if not picture.exists():
            run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i','segments.ffconcat',
                 '-c','copy','-movflags','+faststart','picture-assembly.mp4'],cwd=preview,timeout=1800)
            save(picture_receipt,{'identity':picture_identity,'sha256':sha(picture)})
        duration = plan['totalFrames']/30
        partial = preview/'film-unreviewed.partial.mp4'
        if partial.exists():
            partial.rename(preview/f'film-unreviewed-{time.time_ns()}.partial.mp4')
        run(['ffmpeg','-v','error','-y','-i','picture-assembly.mp4','-i','soundtrack.wav',
            '-map','0:v:0','-map','1:a:0','-vf',f'ass=titles.ass,fade=t=out:st={duration-.8}:d=0.8',
            '-frames:v',str(plan['totalFrames']),'-t',str(duration),'-c:v','libx264','-crf','18',
            '-preset','medium','-pix_fmt','yuv420p','-c:a','aac','-b:a','256k','-ar','48000',
            '-movflags','+faststart',str(partial)],cwd=preview,timeout=21600)
        run(['ffmpeg','-v','error','-xerror','-i',str(partial),'-f','null','-'],timeout=1800)
        actual = probe(partial)
        video = next(s for s in actual['streams'] if s['codec_type'] == 'video')
        audio = next(s for s in actual['streams'] if s['codec_type'] == 'audio')
        if ((video['width'],video['height'],video['avg_frame_rate'],int(video['nb_read_frames']))
                != (3840,2160,'30/1',plan['totalFrames'])
                or abs(float(actual['format']['duration'])-duration) > .001
                or abs(float(video['duration'])-duration) > .001
                or abs(float(audio['duration'])-duration) > .001):
            raise ValueError('Technical preview length, geometry or frame count differs from the locked plan')
        if output.exists():
            raise ValueError('Preserve the existing complete preview before creating another version')
        if (sha(selection_file) if selection_file.exists() else None) != selection_digest:
            raise ValueError('Source selections changed during preview; preserve the partial result')
        partial.replace(output)
        receipt = {'schemaVersion':'vivhite-unreviewed-4k-preview-1',
            'status':'encoded-technical-checks-passed-awaiting-semantic-review','filmSha256':sha(output),
            'bytes':output.stat().st_size,'width':3840,'height':2160,'fps':30,
            'frames':plan['totalFrames'],'seconds':duration,'fullAudioVideoDecode':'passed',
            'sourcePlanSha256':sha(plan_file),'workerSha256':sha(__file__),'sources':sources,
            'sourceSelectionsSha256':selection_digest,
            'soundtrackSha256':sha(soundtrack),'titlesSha256':sha(preview/'titles.ass'),
            'noSpatialUpscaling':True,'formalDelivery':False,'semanticReview':'pending',
            'humanFullPlayback':False,'releasePublished':False,'finishedAt':now()}
        save(preview/'receipt.json',receipt)
        state.update(status='technical-preview-completed-semantic-review-pending',finishedAt=now())
        save(state_file,state)
        print('Complete playable native UHD preview saved; semantic review and formal release remain pending.',flush=True)
    except BaseException as error:
        state.update(status='interrupted-or-failed',updatedAt=now(),error=str(error))
        save(state_file,state)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True,type=Path)
    parser.add_argument('--technical-preview-only',required=True,action='store_true')
    args = parser.parse_args()
    build(args.config.resolve())
