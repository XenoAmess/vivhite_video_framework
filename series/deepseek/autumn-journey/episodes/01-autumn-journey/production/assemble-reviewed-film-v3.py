"""Assemble exactly two accepted replacements into the preserved v2 timeline. GPL-3.0-only."""
import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
MEDIA = ROOT.parent/'vivhite-analysis-output/deepseek/autumn-journey'
DIRECTORY = MEDIA/'production-v3-768p-full-001'
SOURCE_PLAN = EPISODE/'production-plan-v3-768p.json'
FINAL_PLAN = EPISODE/'final-assembly-plan-v3-768p.json'
CHANGED = ['S37','S47']
sys.path.insert(0,str(ROOT/'video-maker/tools'))
import local_video_finisher
import reference_finisher as finisher
from local_video_pipeline import validate


def read(file):
    return json.loads(Path(file).read_text(encoding='utf-8'))


def save(path,value):
    content = (json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    if path.exists() and path.read_bytes()!=content:
        raise ValueError('Retain immutable candidate: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(content)


def workers():
    return {Path(p).resolve().relative_to(ROOT).as_posix():finisher.sha(p) for p in [__file__,
        ROOT/'video-maker/tools/local_video_finisher.py',ROOT/'video-maker/tools/reference_finisher.py']}


def source_assets(plan):
    assets = [DIRECTORY/s['sourceFile'] for s in plan['shots']]
    assets += [DIRECTORY/'soundtrack.wav',EPISODE/plan['director']]
    assets += [EPISODE/ref for s in plan['shots'] for ref in s.get('references',[])]
    return list(dict.fromkeys(p.resolve() for p in assets))


def gate(document,assets):
    command=[sys.executable,'-X','utf8',str(ROOT/'scripts/character_review.py'),'check',
             '--episode',str(EPISODE/'episode.json'),'--document',str(document)]
    for asset in assets: command += ['--asset',str(asset)]
    subprocess.run(command,check=True,cwd=ROOT)


def prepare():
    selections=read(EPISODE/'production/source-selections-v3.json')['shots']
    if sorted(s['id'] for s in selections)!=CHANGED:
        raise ValueError('Only S37 and S47 may change')
    base=MEDIA/'production-v2-768p-full-001'
    plan=read(EPISODE/'production-plan-v2-768p.json')
    old={s['id']:s for s in read(base/'clip-decisions.json')['shots']}
    generation={s['id']:s for s in read(EPISODE/'production-plan-v3-repair01-768p.json')['shots']}
    actions={}
    director=EPISODE/'director-v5.md'
    for line in director.read_text(encoding='utf-8').splitlines():
        if line.startswith('| S'):
            fields=[v.strip() for v in line.split('|')]
            sid,times,seconds,action=fields[1:5]
            shot=next(s for s in plan['shots'] if s['id']==sid)
            start,end=[int(t.split(':')[0])*60+int(t.split(':')[1]) for t in times.split('–')]
            if start*30!=shot['startFrame'] or end-start!=shot['seconds'] or int(seconds)!=shot['seconds']:
                raise ValueError('Keep every original shot boundary: '+sid)
            actions[sid]=action
    if len(actions)!=48: raise ValueError('Complete director required')
    replacements={}
    for selection in selections:
        sid=selection['id']; runtime=(MEDIA/selection['runtime']).resolve()
        if not runtime.is_relative_to(MEDIA.resolve()): raise ValueError('Source escaped episode')
        decisions=read(runtime/'clip-decisions.json')
        if decisions['sourcePlanSha256']!=finisher.sha(EPISODE/selection['plan']):
            raise ValueError('Reviewed source plan changed')
        row=next(s for s in decisions['shots'] if s['id']==sid)
        checks=['noHumanFaces','noAddedPeople','allCharactersFemale','costumeStyle',
                'motionAndContinuity','merchandiseBehavior','referenceAppearance']
        if (row['decision']!='accepted' or row['method']!='assistant-frame-review'
            or row.get('allSourceFrameReview') is not True or row.get('reviewedNativeFrames')!=120
            or row.get('allUsedFrameReview') is not True or any(row.get(k)!='passed' for k in checks)
            or row['sourceSha256']!=finisher.sha(runtime/'sources'/f'{sid}.mp4')):
            raise ValueError('Actual complete source review required: '+sid)
        for evidence in row['frameEvidence']:
            if finisher.sha(evidence['path'])!=evidence['sha256']: raise ValueError('Evidence changed')
        replacements[sid]=(runtime,row,selection)
    decisions=[]; ledger=[]
    for sub in ['sources','segments']: (DIRECTORY/sub).mkdir(parents=True,exist_ok=True)
    for shot in plan['shots']:
        sid=shot['id']
        if sid in replacements:
            runtime,row,selection=replacements[sid]
            shot['references']=generation[sid]['references']
            shot['referenceSha256']=generation[sid]['referenceSha256']
            shot['originalGenerationAction']=generation[sid]['generationAction']
            shot['seed']=generation[sid]['seed']
            shot['actualCorrectionPlan']=selection['plan']
            record={'id':sid,'runtime':selection['runtime'],'plan':selection['plan'],
                    'planSha256':finisher.sha(EPISODE/selection['plan']),
                    'reviewSha256':finisher.sha(runtime/'clip-decisions.json')}
        else:
            runtime,row=base,old[sid]
            if row['decision']!='accepted' or row['sourceSha256']!=finisher.sha(runtime/'sources'/f'{sid}.mp4'):
                raise ValueError('Unchanged source changed: '+sid)
            record={'id':sid,'runtime':base.name,'reviewTransfer':'Exact unchanged v2 source decision; no new full source viewing or user approval inferred.'}
            for suffix in ['.mp4','.json']:
                target=DIRECTORY/'segments'/f'{sid}{suffix}'
                if not target.exists(): shutil.copyfile(base/'segments'/target.name,target)
        target=DIRECTORY/'sources'/f'{sid}.mp4'
        if target.exists() and finisher.sha(target)!=row['sourceSha256']: raise ValueError('Retain different candidate')
        if not target.exists(): shutil.copyfile(runtime/'sources'/target.name,target)
        shot.update(sourceFile=f'sources/{sid}.mp4',sourceSha256=row['sourceSha256'],
                    action=actions[sid],prompt='Assemble actually reviewed source: '+actions[sid])
        decisions.append(copy.deepcopy(row)); ledger.append({**record,'sha256':row['sourceSha256']})
    if not (DIRECTORY/'soundtrack.wav').exists(): shutil.copyfile(base/'soundtrack.wav',DIRECTORY/'soundtrack.wav')
    if finisher.sha(DIRECTORY/'soundtrack.wav')!=plan['soundtrack']['sha256']: raise ValueError('Music changed')
    save(DIRECTORY/'source-imports.json',{'schemaVersion':'deepseek-source-imports-3','shots':ledger})
    save(EPISODE/'production/source-adoptions-v3.json',{'schemaVersion':'deepseek-source-imports-3','shots':ledger})
    plan.update(revision=3,director=director.name,directorSha256=finisher.sha(director),
        sourceAdoptionsSha256=finisher.sha(DIRECTORY/'source-imports.json'),episodeAssemblyWorkers=workers(),
        supersedesSourcePlanSha256=finisher.sha(EPISODE/'production-plan-v2-768p.json'),
        scope='Exactly two user-rejected shot replacements. All48 timings, ASS, dedication and approved music unchanged; v1/v2 preserved, user review pending.')
    validate(plan); save(SOURCE_PLAN,plan)
    record={'schemaVersion':'vivhite-clip-decisions-1','sourcePlanSha256':finisher.sha(SOURCE_PLAN),
            'shots':decisions,'scope':'Two newly reviewed complete sources;46 exact unchanged v2 decisions transferred.'}
    save(DIRECTORY/'clip-decisions.json',record); save(EPISODE/'production/source-review-v3-full-timeline.json',record)
    print('Prepared actual48-source v3 assembly plan, formal review gate still required')


def assemble():
    plan=read(SOURCE_PLAN)
    if plan['episodeAssemblyWorkers']!=workers(): raise ValueError('Assembly workers changed')
    gate(SOURCE_PLAN,source_assets(plan))
    if FINAL_PLAN.exists(): finisher.bound_files(read(FINAL_PLAN),DIRECTORY)
    else: local_video_finisher.prepare(SOURCE_PLAN,DIRECTORY,FINAL_PLAN)


def finish():
    if read(SOURCE_PLAN)['episodeAssemblyWorkers']!=workers(): raise ValueError('Workers changed')
    if (DIRECTORY/'film.mp4').exists(): raise ValueError('Retain completed candidate')
    finisher.finish(EPISODE/'episode.json',FINAL_PLAN,DIRECTORY,sys.executable)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare-plan','assemble','finish'])
    args=parser.parse_args()
    {'prepare-plan':prepare,'assemble':assemble,'finish':finish}[args.command]()
