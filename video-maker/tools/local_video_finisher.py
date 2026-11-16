"""Prepare exact-size picture assemblies; formal finishing retains the character gate.

Requires actual clip decisions for every selected generated source. GPL-3.0-only.
"""
import argparse
import copy
import json
from pathlib import Path

import reference_finisher
from local_video_pipeline import validate,contained


def prepare(plan_file,directory,destination):
    plan_file,directory = Path(plan_file).resolve(),Path(directory).resolve()
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    validate(plan)
    width,height = reference_finisher.output_dimensions(plan)
    segments = directory/'segments'
    segments.mkdir(exist_ok=True)
    concat = 'ffconcat version 1.0\n'
    # Before expensive assembly, check real source hashes and all decisions.
    selections_file = directory/'source-selections.json'
    selections = json.loads(selections_file.read_text(encoding='utf-8'))['selections'] if selections_file.exists() else {}
    selected_shots = copy.deepcopy(plan['shots'])
    files = []
    for shot in selected_shots:
        selected = selections.get(shot['id'])
        path = selected['path'] if selected else f"sources/{shot['id']}.mp4"
        source = contained(directory,path)
        if selected:
            if reference_finisher.sha(source) != selected['sha256']:
                raise ValueError('Selected correction changed')
            parent = contained(directory,selected['parent'])
            contained(directory,selected['receipt'])
            if reference_finisher.sha(parent) != selected['parentSha256']:
                raise ValueError('Selected correction parent changed')
        native = json.loads(reference_finisher.run(['ffprobe','-v','error','-show_streams','-of','json',str(source)]))['streams'][0]
        native_size = tuple(map(int,plan['sourceSize'].split('x')))
        if (native['width'],native['height']) != native_size or native['avg_frame_rate'] != '24/1':
            raise ValueError('Every selected source must retain the stage native resolution and frame rate')
        shot['sourceFile'] = path
        files.append({'path':path,'sha256':reference_finisher.sha(source)})
    reference_finisher.verify_clip_decisions({'sourcePlanSha256':reference_finisher.sha(plan_file),
                                            'shots':selected_shots,'files':files},directory)
    for shot in selected_shots:
        segment = segments/f"{shot['id']}.mp4"
        segment_receipt = segments/f"{shot['id']}.json"
        source_hash = reference_finisher.sha(directory/shot['sourceFile'])
        identity = {'sourceSha256':source_hash,'frames':shot['seconds']*30,'width':width,'height':height,
                    'recipe':'fps30-x264-fast-crf17-1'}
        if segment.exists():
            if not segment_receipt.exists():
                raise ValueError('Unbound existing segment; preserve this run and use a new directory')
            recorded = json.loads(segment_receipt.read_text(encoding='utf-8'))
            if recorded['identity'] != identity or recorded['sha256'] != reference_finisher.sha(segment):
                raise ValueError('Changed source or cached segment; use a separate run')
        if not segment.exists():
            reference_finisher.run(['ffmpeg','-v','error','-y','-i',str(directory/shot['sourceFile']),
                '-map','0:v:0','-an','-vf',f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30',
                '-frames:v',str(shot['seconds']*30),'-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p',str(segment)])
            reference_finisher.write_json(segment_receipt,{'identity':identity,'sha256':reference_finisher.sha(segment)})
        probe = json.loads(reference_finisher.run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(segment)]))
        video = probe['streams'][0]
        if (video['width'],video['height'],int(video['nb_read_frames'])) != (width,height,shot['seconds']*30):
            raise ValueError('Existing segment has an incorrect size or frame count')
        concat += f"file 'segments/{shot['id']}.mp4'\n"
    (directory/'segments.ffconcat').write_text(concat,encoding='utf-8',newline='\n')
    picture = directory/'picture-assembly.mp4'
    picture_receipt = directory/'picture-assembly-receipt.json'
    assembly_identity = {'sourcePlanSha256':reference_finisher.sha(plan_file),
        'segmentSha256':[reference_finisher.sha(segments/f"{shot['id']}.mp4") for shot in plan['shots']]}
    if picture.exists():
        if not picture_receipt.exists():
            raise ValueError('Unbound existing picture assembly; use a separate run')
        recorded = json.loads(picture_receipt.read_text(encoding='utf-8'))
        if recorded['identity'] != assembly_identity or recorded['sha256'] != reference_finisher.sha(picture):
            raise ValueError('Changed cached picture assembly; use a separate run')
    if not picture.exists():
        reference_finisher.run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i','segments.ffconcat',
                               '-c','copy','-movflags','+faststart','picture-assembly.mp4'],cwd=directory)
        reference_finisher.write_json(picture_receipt,{'identity':assembly_identity,'sha256':reference_finisher.sha(picture)})
    final = reference_finisher.prepare(plan_file,directory,destination)
    print(f"Prepared {width}x{height} final plan; actual final-input semantic review still required.")
    return final


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',required=True,type=Path)
    parser.add_argument('--directory',required=True,type=Path)
    parser.add_argument('--destination',required=True,type=Path)
    args = parser.parse_args()
    prepare(args.plan,args.directory,args.destination)
