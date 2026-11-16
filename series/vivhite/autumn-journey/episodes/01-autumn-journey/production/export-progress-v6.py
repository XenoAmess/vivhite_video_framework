"""Snapshot the current 48-shot source batch without granting review approval.

GPL-3.0-only.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0, str(ROOT / 'video-maker/tools'))
from reference_finisher import sha, write_json


def read(path, default):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else default


def export(base):
    plan_file = EP / 'production-plan-v6-bf16-768p.json'
    plan = read(plan_file, {})
    checks = ('noHumanFaces', 'noAddedPeople', 'allCharactersFemale', 'costumeStyle',
              'motionAndContinuity', 'merchandiseBehavior', 'referenceAppearance')
    shots = []
    for shot in plan['shots']:
        identity = shot['id']
        run_name = {'S20': 'production-v6-bf16-768p-S20-001',
                    'S43': 'production-v6-bf16-768p-S43-image-only-001'}.get(
                        identity, 'production-v5-bf16-768p-002')
        run = base / run_name
        selection = read(run / 'source-selections.json', {'selections': {}})[
            'selections'].get(identity)
        source = run / (selection['path'] if selection else f'sources/{identity}.mp4')
        job = read(run / f'jobs/{identity}.json', {})
        decisions = read(run / 'clip-decisions.json', {'shots': []})
        decision = next((row for row in decisions['shots'] if row['id'] == identity), {})
        digest = sha(source) if source.exists() else None
        accepted = bool(digest and digest == decision.get('sourceSha256')
                        and decision.get('allSourceFrameReview') is True
                        and decision.get('reviewedNativeFrames') == shot['sourceSeconds'] * 24
                        and all(decision.get(key) == 'passed' for key in checks))
        shots.append({'id': identity, 'seconds': shot['seconds'],
                      'sourceSeconds': shot['sourceSeconds'], 'run': run_name,
                      'source': source.relative_to(base).as_posix(), 'sourceSha256': digest,
                      'jobStatus': job.get('status'), 'jobId': job.get('jobId'),
                      'acceptedWithReferenceComparison': accepted,
                      'sourceReviewPlanSha256': decisions.get('sourcePlanSha256'),
                      'reviewedAt': decision.get('reviewedAt') if accepted else None,
                      'generationPlanSha256': selection.get('generationPlanSha256')
                          if selection else job.get('planSha256')})
    generated = sum(bool(row['sourceSha256']) for row in shots)
    accepted = sum(row['acceptedWithReferenceComparison'] for row in shots)
    result = {'schemaVersion': 'vivhite-local-production-progress-v6-1',
              'snapshotAt': datetime.now(timezone.utc).isoformat(),
              'targetPlanSha256': sha(plan_file), 'totalShots': len(shots),
              'totalSeconds': sum(row['seconds'] for row in shots),
              'completedSources': generated, 'acceptedSources': accepted,
              'generationPercent': round(100 * generated / len(shots), 2),
              'acceptedPercent': round(100 * accepted / len(shots), 2),
              'final768FilmDelivered': False, 'final2KFilmDelivered': False,
              'humanFullPlayback': False, 'excludedHistoricalSources': ['S20A', 'S20B'],
              'scope': 'Source availability and actual matching review records only. '
                       'This snapshot grants no review, new-plan binding or film approval.',
              'shots': shots}
    write_json(EP / 'production/run-progress-v6.json', result)
    print(json.dumps({key: result[key] for key in ('completedSources', 'acceptedSources',
                                                  'generationPercent', 'acceptedPercent')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    export(parser.parse_args().base.resolve())
