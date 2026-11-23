"""Assemble the exact 48 explicitly reviewed sources; never generate or approve them.

Formal picture assembly and finishing both retain the character review gate.
GPL-3.0-only.
"""
import argparse
import copy
import json
from pathlib import Path
import runpy
import subprocess
import sys

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
MEDIA = ROOT.parent/'vivhite-analysis-output/deepseek/autumn-journey'
DIRECTORY = MEDIA/'production-v1-768p-full-001'
SOURCE_PLAN = EPISODE/'production-plan-v1-768p.json'
FINAL_PLAN = EPISODE/'final-assembly-plan-v1-768p.json'
EXPECTED = [f'S{index:02}' for index in range(1, 49)]
sys.path.insert(0, str(ROOT/'video-maker/tools'))
import local_video_finisher
from local_video_pipeline import validate
import reference_finisher


def read(file):
    return json.loads(file.read_text(encoding='utf-8'))


def write_once(file, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    if file.exists() and file.read_bytes() != data:
        raise ValueError('Preserve existing immutable plan; use a separate delivery version')
    if not file.exists():
        file.write_bytes(data)


def adoption_status():
    ledger = read(DIRECTORY/'source-imports.json')
    ids = [row['id'] for row in ledger['shots']]
    if len(set(ids)) != len(ids) or set(ids)-set(EXPECTED):
        raise ValueError('Duplicate or unknown adopted shot')
    return ledger, [sid for sid in EXPECTED if sid not in ids]


def workers():
    return {str(Path(file).resolve().relative_to(ROOT).as_posix()): reference_finisher.sha(file)
            for file in [__file__, ROOT/'video-maker/tools/local_video_finisher.py',
                         ROOT/'video-maker/tools/reference_finisher.py']}


def prepare_plan():
    ledger, missing = adoption_status()
    if missing:
        raise ValueError('Explicit complete-frame acceptance still missing: '+', '.join(missing))
    director = EPISODE/'director-v2.md'
    if not director.is_file():
        raise ValueError('The actual adopted-shot director document is required')
    timeline_file = ROOT/'series/vivhite/autumn-journey/episodes/01-autumn-journey/delivery-plan-v13-native-4k.json'
    timeline = read(timeline_file)
    if [s['id'] for s in timeline['shots']] != EXPECTED:
        raise ValueError('Original 48-shot timeline changed')
    sound_file = ROOT/'series/vivhite/autumn-journey/episodes/01-autumn-journey/final-assembly-plan-v12-768p.json'
    sound_descriptions = {row['id']: row['soundDescription'] for row in read(sound_file)['shots']}
    if list(sound_descriptions) != EXPECTED:
        raise ValueError('Approved music timeline must cover all48 shots')
    canonical = {}
    for file in ['production-plan-v1-pilot-768p.json', 'production-plan-v1-batch02-768p.json',
                 'production-plan-v1-batch03-768p.json', 'source-review-plan-v1-landscapes.json']:
        canonical.update({row['id']: row for row in read(EPISODE/file)['shots']})
    actual_actions = {}
    for line in director.read_text(encoding='utf-8').splitlines():
        if line.startswith('| S'):
            cells = [cell.strip() for cell in line.split('|')]
            sid, time_range, seconds, action = cells[1:5]
            start, end = time_range.split('–')
            def clock_seconds(value):
                minutes, seconds_part = map(int, value.split(':'))
                return minutes*60+seconds_part
            original = next(row for row in timeline['shots'] if row['id'] == sid)
            if (sid in actual_actions or int(seconds) != original['seconds']
                    or clock_seconds(start)*30 != original['startFrame']
                    or clock_seconds(end)-clock_seconds(start) != int(seconds) or not action):
                raise ValueError('Actual director and original film timing differ: '+sid)
            actual_actions[sid] = action
    if list(actual_actions) != EXPECTED:
        raise ValueError('Actual director must describe all48 shots in order')
    checked_rows, shots = [], []
    proof_helper = runpy.run_path(str(EPISODE/'production/adopt-reviewed-sources-v1.py'))
    checks = ['noHumanFaces', 'noAddedPeople', 'allCharactersFemale', 'costumeStyle',
              'motionAndContinuity', 'merchandiseBehavior', 'referenceAppearance']
    adopted = {row['id']: row for row in ledger['shots']}
    for original in timeline['shots']:
        sid = original['id']
        entry = adopted[sid]
        review_plan = EPISODE/entry['sourceReviewPlan']
        current_review_file = EPISODE/entry['sourceReviewRecord']
        current_review = read(current_review_file)
        row = entry['actualAcceptance']
        source = DIRECTORY/entry['path']
        source_seconds = 10 if sid == 'S20' else 14 if sid == 'S48' else 5
        if (reference_finisher.sha(review_plan) != entry['sourceReviewPlanSha256']
                or current_review['sourcePlanSha256'] != entry['sourceReviewPlanSha256']
                or row not in current_review['shots']
                or row.get('decision') != 'accepted' or row.get('method') != 'assistant-frame-review'
                or row.get('allSourceFrameReview') is not True or row.get('allUsedFrameReview') is not True
                or any(row.get(key) != 'passed' for key in checks)
                or row['reviewedNativeFrames'] != source_seconds*24
                or row['sourceSha256'] != entry['sha256'] or reference_finisher.sha(source) != entry['sha256']):
            raise ValueError('Adopted source or original explicit acceptance changed: '+sid)
        for item in row['frameEvidence']:
            proof_helper['episode_proof'](item)
        transferred = copy.deepcopy(row)
        transferred['originReviewPlanSha256'] = entry['sourceReviewPlanSha256']
        transferred['originReviewRecordCurrentSha256'] = reference_finisher.sha(current_review_file)
        transferred['reviewTransfer'] = 'Exact reviewed bytes and original dated decision; no new watching or semantic acceptance is inferred.'
        checked_rows.append(transferred)
        shot = copy.deepcopy(canonical[sid])
        action = actual_actions[sid]
        if 'generationAction' in shot:
            shot['originalGenerationAction'] = shot.pop('generationAction')
        shot.update(startFrame=original['startFrame'], finalFilmStartFrame=original['startFrame'],
                    seconds=original['seconds'], sourceSeconds=source_seconds,
                    action=action, prompt='Assembly of the explicitly selected reviewed source: '+action,
                    sourceFile=entry['path'], sourceSha256=entry['sha256'],
                    soundDescription=sound_descriptions[sid])
        shots.append(shot)
    plan = read(EPISODE/'production-plan-v1-pilot-768p.json')
    plan.update(totalFrames=6150, shots=shots, shotDurationExceptions={'S20': 10, 'S48': 14},
                referenceAppearanceRequired=True, assemblyOnly=True,
                director='director-v2.md', directorSha256=reference_finisher.sha(director),
                originalTimelineSha256=reference_finisher.sha(timeline_file),
                referenceSoundDescriptionsPlanSha256=reference_finisher.sha(sound_file),
                sourceAdoptionsSha256=reference_finisher.sha(DIRECTORY/'source-imports.json'),
                episodeAssemblyWorkers=workers(), closingCredit='',
                titleOverlays=[{'shotId': 'S06', 'text': '大肥鱼 / 秋日旅程',
                                'subtitle': 'DeepSeek · Autumn Journey'},
                               {'shotId': 'S48', 'text': '大肥鱼 / 秋日旅程',
                                'subtitle': 'DeepSeek · Autumn Journey',
                                'dedication': '献给世界上最可爱的你',
                                'dedicationDelaySeconds': 3, 'dedicationFadeInMs': 1800}],
                soundtrack={'path': 'soundtrack.wav', 'sha256': '46ef587715d277e778c805e566d643ce7b8430d3486ee8143b36dda34a74205b',
                            'source': 'Unchanged approved205second procedural instrumental and ambience master',
                            'nativeModelAudioInFinalMix': False},
                scope='Assembly-only plan for48 exact actually reviewed sources. Includes disclosed postproduction and3 unchanged character-free landscapes. No HTTP submission or final encoded/user acceptance.')
    validate(plan)
    if reference_finisher.sha(DIRECTORY/'soundtrack.wav') != plan['soundtrack']['sha256']:
        raise ValueError('Approved full-length music master changed')
    write_once(SOURCE_PLAN, plan)
    decisions = {'schemaVersion': 'vivhite-clip-decisions-1',
                 'sourcePlanSha256': reference_finisher.sha(SOURCE_PLAN), 'shots': checked_rows,
                 'scope': 'Rebind existing complete-source decisions to exact unchanged source bytes in the full timeline. Original review timestamps and evidence preserved; not a new playback review.'}
    destination = DIRECTORY/'clip-decisions.json'
    if destination.exists() and read(destination) != decisions:
        prior_landscape_review = read(EPISODE/'production/source-review-v1-landscapes.json')
        if read(destination) != prior_landscape_review:
            raise ValueError('Preserve an unexpected existing full-run decision record')
        history = DIRECTORY/'review-history'
        history.mkdir(exist_ok=True)
        snapshot = history/('landscapes-'+reference_finisher.sha(destination)+'.json')
        if snapshot.exists() and snapshot.read_bytes() != destination.read_bytes():
            raise ValueError('Historical landscape decision bytes changed')
        if not snapshot.exists():
            snapshot.write_bytes(destination.read_bytes())
        from local_video_pipeline import save
        save(destination, decisions)
    else:
        write_once(destination, decisions)
    write_once(EPISODE/'production/source-review-v1-full-timeline.json', decisions)
    print('Prepared actual48-shot source plan and exact-byte review transfer; formal gates remain required.')


def source_assets(plan):
    paths = [DIRECTORY/shot['sourceFile'] for shot in plan['shots']]
    paths += [DIRECTORY/'soundtrack.wav', EPISODE/plan['director']]
    for shot in plan['shots']:
        paths += [EPISODE/p for p in shot.get('references', [])]
    return list(dict.fromkeys(path.resolve() for path in paths))


def assemble():
    plan = read(SOURCE_PLAN)
    if plan['episodeAssemblyWorkers'] != workers():
        raise ValueError('Reviewed assembly worker bytes changed')
    args = [sys.executable, '-X', 'utf8', str(ROOT/'scripts/character_review.py'), 'check',
            '--episode', str(EPISODE/'episode.json'), '--document', str(SOURCE_PLAN)]
    for path in source_assets(plan):
        args += ['--asset', str(path)]
    subprocess.run(args, check=True, cwd=ROOT)
    if FINAL_PLAN.exists():
        final = read(FINAL_PLAN)
        if final['sourcePlanSha256'] != reference_finisher.sha(SOURCE_PLAN):
            raise ValueError('Preserve a differently bound final plan')
        reference_finisher.bound_files(final, DIRECTORY)
        return
    local_video_finisher.prepare(SOURCE_PLAN, DIRECTORY, FINAL_PLAN)


def finish():
    if read(SOURCE_PLAN)['episodeAssemblyWorkers'] != workers():
        raise ValueError('Reviewed finishing worker bytes changed')
    film = DIRECTORY/'film.mp4'
    if film.exists():
        receipt = read(DIRECTORY/'final-assembly-receipt.json')
        if (receipt['planSha256'] != reference_finisher.sha(FINAL_PLAN)
                or receipt['filmSha256'] != reference_finisher.sha(film)):
            raise ValueError('Preserve a different or unbound film')
        reference_finisher.bound_files(read(FINAL_PLAN), DIRECTORY)
        print('Exact previously finished movie retained:', film)
        return
    reference_finisher.finish(EPISODE/'episode.json', FINAL_PLAN, DIRECTORY, sys.executable)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['status', 'prepare-plan', 'assemble', 'finish'])
    command = parser.parse_args().command
    if command == 'status':
        ledger, missing = adoption_status()
        print(json.dumps({'adoptedShots': len(ledger['shots']), 'totalShots': 48,
                          'adoptionPercent': round(len(ledger['shots'])/48*100, 2),
                          'missingExplicitAcceptances': missing}, ensure_ascii=False, indent=2))
    elif command == 'prepare-plan':
        prepare_plan()
    elif command == 'assemble':
        assemble()
    else:
        finish()
