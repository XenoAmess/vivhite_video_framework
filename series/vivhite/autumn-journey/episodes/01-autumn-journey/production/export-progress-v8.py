"""Export actual seven-shot motion-revision progress, without granting approval.

GPL-3.0-only.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

EP = Path(__file__).resolve().parents[1]
SHOT_IDS = ('S05', 'S07', 'S15', 'S28', 'S44', 'S47', 'S48')


def read(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def export(base):
    run = base / 'production-v8-motion-768p-001'
    decisions = read(run / 'clip-decisions.json', {}).get('shots', [])
    rows = []
    for identity in SHOT_IDS:
        job = read(run / 'jobs' / f'{identity}.json', {})
        decision = next((item for item in decisions if item['id'] == identity), {})
        accepted = (decision.get('sourceSha256') == job.get('sourceSha256')
                    and decision.get('allSourceFrameReview') is True
                    and decision.get('decision') != 'rejected'
                    and all(decision.get(key) == 'passed' for key in (
                        'noHumanFaces', 'noAddedPeople', 'allCharactersFemale', 'costumeStyle',
                        'motionAndContinuity', 'merchandiseBehavior', 'referenceAppearance')))
        rows.append({'id': identity, 'status': job.get('status', 'not-submitted'),
                     'jobId': job.get('jobId'), 'sourceSha256': job.get('sourceSha256'),
                     'serverProgress': job.get('remote', {}).get('progress'),
                     'completeSourceAccepted': accepted})
    completed = sum(bool(row['sourceSha256']) for row in rows)
    accepted = sum(row['completeSourceAccepted'] for row in rows)
    receipt = read(EP / 'production/release-v8-768p.json', {})
    value = {'schemaVersion': 'vivhite-motion-revision-progress-1', 'revision': 8,
             'snapshotAt': datetime.now(timezone.utc).isoformat(), 'newShots': 7,
             'completedSources': completed, 'acceptedNewSources': accepted,
             'generationPercent': round(completed * 100 / 7, 2),
             'acceptancePercent': round(accepted * 100 / 7, 2),
             'first47TimingsLockedToV7': True, 'closingSeconds': 14,
             'targetSeconds': 205, 'targetFrames': 6150, 'twoKStatus': 'stopped-by-user',
             'automaticTwoKResumeAllowed': False, 'releasePublished': bool(receipt.get('releaseId')),
             'humanFullPlayback': False, 'shots': rows,
             'scope': 'Seven new replacements only. Server progress is not source acceptance or film completion.'}
    (EP / 'production/run-progress-v8-768p.json').write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: value[key] for key in (
        'completedSources', 'acceptedNewSources', 'generationPercent', 'acceptancePercent', 'releasePublished')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, type=Path)
    export(parser.parse_args().base.resolve())
