"""Import explicitly selected, actually reviewed source bytes; never infer approval.

Copies preserve all rejected candidates and original runs. GPL-3.0-only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
MEDIA = ROOT.parent/'vivhite-analysis-output/deepseek/autumn-journey'
DESTINATION = MEDIA/'production-v1-768p-full-001'


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def episode_proof(item):
    marker = EPISODE.relative_to(ROOT).as_posix()+'/'
    original = item['path'].replace('\\', '/')
    if marker not in original:
        raise ValueError('Review evidence does not belong to this episode')
    relative = original.split(marker, 1)[1]
    actual = (EPISODE/relative).resolve()
    if not actual.is_relative_to(EPISODE) or sha(actual) != item['sha256']:
        raise ValueError('Original complete-frame proof changed')
    return {'pathRelativeToEpisode': relative, 'sha256': item['sha256'], 'items': item['items']}


def adopt(plan_file, review_file, directory, ids):
    plan_file, review_file, directory = plan_file.resolve(), review_file.resolve(), directory.resolve()
    if not plan_file.is_relative_to(EPISODE) or not review_file.is_relative_to(EPISODE) or not directory.is_relative_to(MEDIA):
        raise ValueError('Keep actual plans, review records and source media in this episode')
    review = json.loads(review_file.read_text(encoding='utf-8'))
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    if review['schemaVersion'] != 'vivhite-clip-decisions-1' or review['sourcePlanSha256'] != sha(plan_file):
        raise ValueError('Actual source-review plan changed')
    ledger_file = DESTINATION/'source-imports.json'
    ledger = json.loads(ledger_file.read_text(encoding='utf-8')) if ledger_file.exists() else {
        'schemaVersion': 'deepseek-actually-reviewed-source-imports-1', 'expectedShots': 48, 'shots': [],
        'scope': 'Partial source adoption only; final assembly, encoded review and user acceptance are separate.'}
    checks = ('noHumanFaces', 'noAddedPeople', 'allCharactersFemale', 'costumeStyle',
              'motionAndContinuity', 'merchandiseBehavior', 'referenceAppearance')
    for sid in ids:
        if not re.fullmatch(r'S\d{2}', sid):
            raise ValueError('Use actual shot IDs')
        row = next(item for item in review['shots'] if item['id'] == sid)
        shot = next(item for item in plan['shots'] if item['id'] == sid)
        source = directory/'sources'/f'{sid}.mp4'
        if (row.get('decision') != 'accepted' or row.get('method') != 'assistant-frame-review'
                or row.get('allSourceFrameReview') is not True or row.get('allUsedFrameReview') is not True
                or any(row.get(key) != 'passed' for key in checks)
                or row['sourceSha256'] != sha(source)
                or row['reviewedNativeFrames'] != shot['sourceSeconds']*24):
            raise ValueError('Actual full-source acceptance is unresolved or stale')
        proof = [episode_proof(item) for item in row['frameEvidence']]
        probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-count_frames',
                          '-show_streams', '-of', 'json', str(source)]))['streams'][0]
        if (probe['width'], probe['height'], probe['avg_frame_rate'], int(probe['nb_read_frames'])) != (
                1344, 768, '24/1', row['reviewedNativeFrames']):
            raise ValueError('Selected source format differs from actual reviewed full source')
        previous = next((item for item in ledger['shots'] if item['id'] == sid), None)
        target = DESTINATION/'sources'/f'{sid}.mp4'
        if previous and previous['sha256'] != row['sourceSha256']:
            raise ValueError('Preserve adopted source; a different candidate needs a new delivery run')
        if target.exists() and sha(target) != row['sourceSha256']:
            raise ValueError('Different final-run source already exists')
        if not target.exists():
            shutil.copyfile(source, target)
        entry = {'id': sid, 'path': target.relative_to(DESTINATION).as_posix(), 'sha256': row['sourceSha256'],
                 'originRunRelativeToRepositoryParent': directory.relative_to(ROOT.parent).as_posix(),
                 'sourceReviewPlan': plan_file.relative_to(EPISODE).as_posix(), 'sourceReviewPlanSha256': sha(plan_file),
                 'sourceReviewRecord': review_file.relative_to(EPISODE).as_posix(), 'sourceReviewRecordSha256AtImport': sha(review_file),
                 'actualAcceptance': row, 'completeFrameProof': proof}
        ledger['shots'] = [item for item in ledger['shots'] if item['id'] != sid]+[entry]
        print(sid, row['sourceSha256'], flush=True)
    ledger['shots'].sort(key=lambda item: item['id'])
    ledger['adoptedShots'] = len(ledger['shots'])
    for file in (ledger_file, EPISODE/'production/source-adoptions-v1.json'):
        file.write_text(json.dumps(ledger, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--review', required=True, type=Path)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--shots', required=True)
    args = parser.parse_args()
    adopt(args.plan, args.review, args.directory, args.shots.split(','))
