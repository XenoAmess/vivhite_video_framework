"""Render an explicitly partial, unreviewed technical 4K prefix.

Uses actual accepted sources and the unchanged generation input gate. Does not
approve the encoded film, replace full delivery or publish a release. GPL-3.0-only.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0,str(ROOT/'video-maker/tools'))
from durable_video_controller import verify_frozen
from local_video_pipeline import read, save, validate, input_assets, source_frame_count, now
from reference_finisher import sha, run, titles
from render_4k_technical_preview import probe, selected_source


def render(configuration, count, destination):
    config = read(configuration)
    verify_frozen(config)
    directory = Path(config['directory']).resolve()
    destination = Path(destination).resolve()
    if destination == directory or not destination.is_relative_to(directory):
        raise ValueError('Use a separate technical prefix directory within the runtime')
    plan_file = Path(config['plan'])
    plan = read(plan_file)
    validate(plan)
    if plan['stage'] != 'refine' or not 1 <= count < len(plan['shots']):
        raise ValueError('This entry only renders a strict prefix of the native 4K plan')
    os.environ['PATH'] = os.pathsep.join([*config['toolDirectories'],os.environ.get('PATH','')])
    decisions = read(directory/'clip-decisions.json')
    if decisions['sourcePlanSha256'] != config['planSha256']:
        raise ValueError('Actual source decisions belong to another plan')
    selected = []
    for shot in plan['shots'][:count]:
        job = read(directory/'jobs'/f"{shot['id']}.json")
        source,report_file = selected_source(directory,shot,job,config['planSha256'])
        report = read(report_file)
        row = next((row for row in decisions['shots'] if row['id'] == shot['id']),{})
        digest = sha(source)
        if (job.get('status') != 'completed' or job.get('planSha256') != config['planSha256']
                or row.get('decision') != 'accepted' or row.get('sourceSha256') != digest
                or row.get('allSourceFrameReview') is not True
                or row.get('reviewedNativeFrames') != source_frame_count(shot)
                or any(row.get(key) != 'passed' for key in ('noHumanFaces','noAddedPeople',
                    'allCharactersFemale','costumeStyle','motionAndContinuity','merchandiseBehavior','referenceAppearance'))
                or report['identity']['sourceSha256'] != digest
                or report['decodedFrames'] != source_frame_count(shot)):
            raise ValueError('Every included source requires its actual complete-frame acceptance')
        native = probe(source)['streams']
        if (len(native) != 1 or native[0].get('codec_type') != 'video'
                or (native[0]['width'],native[0]['height'],native[0]['avg_frame_rate'],int(native[0]['nb_read_frames']))
                != (3840,2160,'24/1',source_frame_count(shot))):
            raise ValueError('Require complete native UHD video-only sources')
        selected.append({'id':shot['id'],'sourcePath':str(source),'sourceSha256':digest,
            'startFrame':shot['startFrame'],'seconds':shot['seconds']})
    gate = [sys.executable,str(ROOT/'scripts/character_review.py'),'check',
        '--episode',config['episode'],'--document',str(plan_file)]
    for asset in input_assets(plan,Path(config['episode']),directory):
        gate.extend(['--asset',str(asset)])
    print(run(gate,timeout=120),flush=True)
    selections_file = directory/'source-selections.json'
    selection_digest = sha(selections_file) if selections_file.exists() else None
    destination.mkdir(parents=True,exist_ok=False)
    (destination/'segments').mkdir()
    total_frames = sum(row['seconds']*30 for row in selected)
    duration = total_frames/30
    for row in selected:
        segment = destination/'segments'/f"{row['id']}.mp4"
        run(['ffmpeg','-v','error','-i',row['sourcePath'],'-map','0:v:0','-an','-vf','fps=30',
            '-frames:v',str(row['seconds']*30),'-c:v','libx264','-preset','fast','-crf','17',
            '-pix_fmt','yuv420p',str(segment)],timeout=3600)
        row['segmentSha256'] = sha(segment)
    (destination/'segments.ffconcat').write_text('ffconcat version 1.0\n'+''.join(
        f"file 'segments/{row['id']}.mp4'\n" for row in selected),encoding='utf-8',newline='\n')
    run(['ffmpeg','-v','error','-f','concat','-safe','0','-i','segments.ffconcat',
        '-c','copy','-movflags','+faststart','picture.mp4'],cwd=destination,timeout=1800)
    if sha(directory/'soundtrack.wav') != config['soundtrackSha256']:
        raise ValueError('Original soundtrack changed')
    shutil.copyfile(directory/'soundtrack.wav',destination/'soundtrack.wav')
    (destination/'titles.ass').write_text(titles(plan),encoding='utf-8-sig',newline='\n')
    if sha(destination/'titles.ass') != config['titlesSha256']:
        raise ValueError('Original title text/style/timing changed')
    partial = destination/'film-unreviewed-prefix.partial.mp4'
    run(['ffmpeg','-v','error','-i','picture.mp4','-i','soundtrack.wav','-map','0:v:0','-map','1:a:0',
        '-vf','ass=titles.ass','-frames:v',str(total_frames),'-t',str(duration),
        '-c:v','libx264','-crf','18','-preset','medium','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','256k','-ar','48000','-movflags','+faststart',str(partial)],
        cwd=destination,timeout=21600)
    run(['ffmpeg','-v','error','-xerror','-i',str(partial),'-f','null','-'],timeout=1800)
    actual = probe(partial)
    video = next(stream for stream in actual['streams'] if stream['codec_type'] == 'video')
    audio = next(stream for stream in actual['streams'] if stream['codec_type'] == 'audio')
    if ((video['width'],video['height'],video['avg_frame_rate'],int(video['nb_read_frames']))
            != (3840,2160,'30/1',total_frames) or any(abs(float(value)-duration) > .001
                for value in (video['duration'],audio['duration'],actual['format']['duration']))):
        raise ValueError('Technical prefix size, frame count or duration differs')
    if ((sha(selections_file) if selections_file.exists() else None) != selection_digest
            or any(sha(row['sourcePath']) != row['sourceSha256'] for row in selected)
            or sha(plan_file) != config['planSha256']):
        raise ValueError('Source binding changed during prefix rendering; partial retained')
    output = destination/'film-unreviewed-prefix.mp4'
    partial.replace(output)
    receipt = {'schemaVersion':'vivhite-partial-native-4k-technical-preview-1',
        'status':'encoded-technical-checks-passed-awaiting-encoded-review',
        'finishedAt':now(),'sourcePlanSha256':config['planSha256'],'workerSha256':sha(__file__),
        'sourceSelectionsSha256':selection_digest,'sources':selected,'includedShots':count,
        'width':3840,'height':2160,'fps':30,'frames':total_frames,'seconds':duration,
        'fullFilmTargetSeconds':205,'fullFilmTargetFrames':6150,'allOriginalShotTimingsPreserved':True,
        'filmSha256':sha(output),'bytes':output.stat().st_size,'fullAudioVideoDecode':'passed',
        'soundtrackSha256':sha(destination/'soundtrack.wav'),'titlesSha256':sha(destination/'titles.ass'),
        'nativeModelAudioInFinalMix':False,'formalDelivery':False,'releasePublished':False,
        'semanticReview':'Actual included sources passed; encoded prefix review remains separate.',
        'humanFullPlayback':False,'scope':'Only the unchanged opening prefix, not the full 205-second film.'}
    save(destination/'receipt.json',receipt)
    print(json.dumps({'path':str(output),'seconds':duration,'frames':total_frames,
        'formalDelivery':False,'fullAudioVideoDecode':'passed'},indent=2),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',required=True,type=Path)
    parser.add_argument('--count',required=True,type=int)
    parser.add_argument('--destination',required=True,type=Path)
    parser.add_argument('--technical-prefix-only',required=True,action='store_true')
    args = parser.parse_args()
    render(args.configuration.resolve(),args.count,args.destination)
