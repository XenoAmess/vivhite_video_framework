"""Build a separate v2 using explicit exact-byte replacement decisions. GPL-3.0-only."""
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
DIRECTORY = MEDIA/'production-v2-768p-full-001'
SOURCE_PLAN = EPISODE/'production-plan-v2-768p.json'
FINAL_PLAN = EPISODE/'final-assembly-plan-v2-768p.json'
CHANGED = ['S10','S16','S23','S26','S34','S37','S40','S43']
sys.path.insert(0, str(ROOT/'video-maker/tools'))
import local_video_finisher
import reference_finisher as finisher
from local_video_pipeline import validate


def read(file):
    return json.loads(Path(file).read_text(encoding='utf-8'))


def write_new(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Retain immutable candidate: '+str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)


def workers():
    return {Path(p).resolve().relative_to(ROOT).as_posix(): finisher.sha(p) for p in [__file__,
        ROOT/'video-maker/tools/local_video_finisher.py', ROOT/'video-maker/tools/reference_finisher.py']}


def source_assets(plan):
    result = [DIRECTORY/s['sourceFile'] for s in plan['shots']]
    result += [DIRECTORY/'soundtrack.wav', EPISODE/plan['director']]
    for shot in plan['shots']:
        result.extend(EPISODE/p for p in shot.get('references', []))
    return list(dict.fromkeys(p.resolve() for p in result))


def gate(document, assets):
    command = [sys.executable, '-X', 'utf8', str(ROOT/'scripts/character_review.py'), 'check',
               '--episode', str(EPISODE/'episode.json'), '--document', str(document)]
    for asset in assets:
        command.extend(['--asset', str(asset)])
    subprocess.run(command, check=True, cwd=ROOT)


def prepare():
    replacements = read(EPISODE/'production/source-selections-v2.json')['shots']
    if sorted(row['id'] for row in replacements) != CHANGED:
        raise ValueError('Exactly the eight requested visual shots must be selected')
    plan = read(EPISODE/'production-plan-v1-768p.json')
    prior_directory = MEDIA/'production-v1-768p-full-001'
    old_rows = {s['id']: s for s in read(prior_directory/'clip-decisions.json')['shots']}
    replacement_rows = {}
    checks = ['noHumanFaces','noAddedPeople','allCharactersFemale','costumeStyle',
              'motionAndContinuity','merchandiseBehavior','referenceAppearance']
    for entry in replacements:
        sid = entry['id']
        runtime = MEDIA/entry['runtime']
        if not runtime.resolve().is_relative_to(MEDIA.resolve()):
            raise ValueError('Source escaped episode media')
        review = read(runtime/'clip-decisions.json')
        review_plan = EPISODE/entry['plan']
        if review['sourcePlanSha256'] != finisher.sha(review_plan):
            raise ValueError('Actual review plan changed: '+sid)
        row = next(s for s in review['shots'] if s['id'] == sid)
        if (row['decision'] != 'accepted' or row['method'] != 'assistant-frame-review'
                or row.get('allSourceFrameReview') is not True or row.get('allUsedFrameReview') is not True
                or row.get('reviewedNativeFrames') != 120 or any(row.get(k) != 'passed' for k in checks)
                or row['sourceSha256'] != finisher.sha(runtime/'sources'/f'{sid}.mp4')):
            raise ValueError('Explicit complete native review still missing: '+sid)
        for evidence in row['frameEvidence']:
            if finisher.sha(evidence['path']) != evidence['sha256']:
                raise ValueError('Actual proof changed: '+sid)
        replacement_rows[sid] = (runtime, row, entry)
    director = EPISODE/'director-v4.md'
    actions = {}
    for line in director.read_text(encoding='utf-8').splitlines():
        if line.startswith('| S'):
            cells = [c.strip() for c in line.split('|')]
            sid, time_range, seconds, action = cells[1:5]
            shot = next(s for s in plan['shots'] if s['id'] == sid)
            start, end = [int(t.split(':')[0])*60+int(t.split(':')[1]) for t in time_range.split('–')]
            if int(seconds) != shot['seconds'] or start*30 != shot['startFrame'] or end-start != int(seconds):
                raise ValueError('A shot duration or start was changed: '+sid)
            actions[sid] = action
    if len(actions) != 48:
        raise ValueError('Complete actual director required')
    decisions, ledger = [], []
    (DIRECTORY/'sources').mkdir(parents=True, exist_ok=True)
    (DIRECTORY/'segments').mkdir(exist_ok=True)
    frame_refs = {s['id']:s['references'] for s in read(EPISODE/'production-plan-v2-repair01-768p.json')['shots']}
    for shot in plan['shots']:
        sid = shot['id']
        if sid in replacement_rows:
            runtime, row, entry = replacement_rows[sid]
            record = {'id': sid, 'runtime': entry['runtime'], 'plan': entry['plan'],
                      'planSha256': finisher.sha(EPISODE/entry['plan']), 'reviewSha256': finisher.sha(runtime/'clip-decisions.json')}
            if sid in frame_refs:
                shot['references'] = frame_refs[sid]
                shot['referenceSha256'] = [finisher.sha(EPISODE/f) for f in shot['references']]
            if sid == 'S40':
                shot['references'] = ['assets/generated/production-v2-firstframes-001/scenes/S40-clean-v1.png',
                                      'assets/generated/production-v2-firstframes-001/scenes/S40-sticker-fitted-rgba.png']
                shot['referenceSha256'] = [finisher.sha(EPISODE/f) for f in shot['references']]
        else:
            runtime, row = prior_directory, old_rows[sid]
            if row['decision'] != 'accepted' or row['sourceSha256'] != finisher.sha(runtime/'sources'/f'{sid}.mp4'):
                raise ValueError('Exact prior reviewed source changed: '+sid)
            record = {'id': sid, 'runtime': prior_directory.name, 'reviewTransfer': 'Unchanged exact v1 source and dated decision; no new full playback or user acceptance is inferred.'}
            for suffix in ['.mp4','.json']:
                segment = runtime/'segments'/f'{sid}{suffix}'
                target = DIRECTORY/'segments'/segment.name
                if not target.exists():
                    shutil.copyfile(segment, target)
        source = runtime/'sources'/f'{sid}.mp4'
        target = DIRECTORY/'sources'/source.name
        if target.exists() and finisher.sha(target) != row['sourceSha256']:
            raise ValueError('Retain different source candidate: '+sid)
        if not target.exists():
            shutil.copyfile(source, target)
        shot.update(sourceFile=f'sources/{sid}.mp4', sourceSha256=row['sourceSha256'],
                    action=actions[sid], prompt='Assemble actually reviewed source: '+actions[sid])
        decisions.append(copy.deepcopy(row))
        ledger.append({**record, 'sha256': row['sourceSha256']})
    music = prior_directory/'soundtrack.wav'
    if not (DIRECTORY/'soundtrack.wav').exists():
        shutil.copyfile(music, DIRECTORY/'soundtrack.wav')
    if finisher.sha(DIRECTORY/'soundtrack.wav') != plan['soundtrack']['sha256']:
        raise ValueError('Approved music changed')
    write_new(DIRECTORY/'source-imports.json', {'schemaVersion':'deepseek-source-imports-2','shots':ledger})
    write_new(EPISODE/'production/source-adoptions-v2.json', {'schemaVersion':'deepseek-source-imports-2','shots':ledger})
    plan.update(revision=2, director=director.name, directorSha256=finisher.sha(director),
        sourceAdoptionsSha256=finisher.sha(DIRECTORY/'source-imports.json'), episodeAssemblyWorkers=workers(),
        supersedesSourcePlanSha256=finisher.sha(EPISODE/'production-plan-v1-768p.json'),
        scope='Eight visual replacements and exact requested dedication. All48 shot timings and approved music unchanged. Historical v1 preserved; user aesthetic review remains pending.')
    for title in plan['titleOverlays']:
        if title['shotId'] == 'S48':
            title['dedication'] = '献给世界上最好用的你'
    validate(plan)
    write_new(SOURCE_PLAN, plan)
    decision_record = {'schemaVersion':'vivhite-clip-decisions-1','sourcePlanSha256':finisher.sha(SOURCE_PLAN),
        'shots':decisions,'scope':'Eight newly actually reviewed exact-byte sources;40 unchanged v1 review transfers. Full encoded-film review remains separate.'}
    write_new(DIRECTORY/'clip-decisions.json', decision_record)
    write_new(EPISODE/'production/source-review-v2-full-timeline.json', decision_record)
    print('Separate v2 plan and48 source bindings prepared; formal gate still required.')


def assemble():
    plan = read(SOURCE_PLAN)
    if plan['episodeAssemblyWorkers'] != workers():
        raise ValueError('Reviewed workers changed')
    gate(SOURCE_PLAN, source_assets(plan))
    if FINAL_PLAN.exists():
        finisher.bound_files(read(FINAL_PLAN), DIRECTORY)
    else:
        local_video_finisher.prepare(SOURCE_PLAN, DIRECTORY, FINAL_PLAN)


def finish():
    if read(SOURCE_PLAN)['episodeAssemblyWorkers'] != workers():
        raise ValueError('Reviewed workers changed')
    if (DIRECTORY/'film.mp4').exists():
        raise ValueError('Finished candidate retained; inspect existing receipts')
    finisher.finish(EPISODE/'episode.json', FINAL_PLAN, DIRECTORY, sys.executable)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare-plan','assemble','finish'])
    command = parser.parse_args().command
    {'prepare-plan':prepare, 'assemble':assemble, 'finish':finish}[command]()
