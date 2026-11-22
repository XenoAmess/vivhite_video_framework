"""Copy only hash-verified, character-free landscapes and the approved music master.

Fresh scene review remains separate from byte verification. GPL-3.0-only.
"""
import hashlib
import json
from pathlib import Path
import shutil
import wave

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
OLD_EPISODE = ROOT/'series/vivhite/autumn-journey/episodes/01-autumn-journey'
MEDIA = ROOT.parent/'vivhite-analysis-output'
OLD = MEDIA/'vivhite/autumn-journey/production-v12-saddle-768p-full-001'
DESTINATION = MEDIA/'deepseek/autumn-journey/production-v1-768p-full-001'


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def copy_checked(source, destination, digest):
    if sha(source) != digest:
        raise ValueError('Original adopted material changed')
    if destination.exists() and sha(destination) != digest:
        raise ValueError('Different imported file already present')
    if not destination.exists():
        shutil.copyfile(source, destination)


def main():
    delivery = json.loads((OLD_EPISODE/'delivery-plan-v12-768p.json').read_text(encoding='utf-8'))
    final_plan = OLD_EPISODE/delivery['finalAssemblyPlan']
    if sha(final_plan) != delivery['finalAssemblyPlanSha256']:
        raise ValueError('Original delivery plan changed')
    plan = json.loads(final_plan.read_text(encoding='utf-8'))
    bound = {row['path']: row['sha256'] for row in plan['files']}
    (DESTINATION/'sources').mkdir(parents=True, exist_ok=True)
    rows = []
    for sid in ('S02', 'S25', 'S33'):
        shot = next(row for row in plan['shots'] if row['id'] == sid)
        path = shot['sourceFile']
        target = DESTINATION/'sources'/f'{sid}.mp4'
        copy_checked(OLD/path, target, bound[path])
        rows.append({'id': sid, 'path': target.relative_to(DESTINATION).as_posix(),
                     'sha256': bound[path], 'role': 'unchanged-character-free-landscape',
                     'sourcePlan': final_plan.relative_to(ROOT).as_posix(), 'sourcePlanSha256': sha(final_plan),
                     'seconds': shot['seconds'], 'sourceSeconds': 5, 'newReview': 'pending'})
    soundtrack = DESTINATION/'soundtrack.wav'
    copy_checked(OLD/'soundtrack.wav', soundtrack, bound['soundtrack.wav'])
    with wave.open(str(soundtrack), 'rb') as audio:
        parameters = {'frames': audio.getnframes(), 'channels': audio.getnchannels(),
                      'sampleRate': audio.getframerate(), 'sampleWidth': audio.getsampwidth()}
    if parameters != {'frames': 9840000, 'channels': 2, 'sampleRate': 48000, 'sampleWidth': 2}:
        raise ValueError('Approved205second music master parameters changed')
    record = {'schemaVersion': 'deepseek-reused-material-imports-1', 'landscapes': rows,
              'soundtrack': {'path': 'soundtrack.wav', 'sha256': sha(soundtrack),
                            'durationSeconds': 205, **parameters,
                            'origin': 'Existing user-approved procedural instrumental and ambience master. No speech/lyrics or native-model audio.'},
              'scope': 'Byte-verified copies only; fresh landscape source-frame review is separate.'}
    for target in (DESTINATION/'reference-material-imports.json', EPISODE/'production/reference-material-imports-v1.json'):
        target.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
