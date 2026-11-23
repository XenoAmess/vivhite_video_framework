"""Package the actual v2 movie and recoverable reviewed inputs, never publish. GPL-3.0-only."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
MEDIA = ROOT.parent/'vivhite-analysis-output/deepseek/autumn-journey'
RUNTIME = MEDIA/'production-v2-768p-full-001'
OUTPUT = MEDIA/'review-release-v2-768p-final2'
PREFIX = 'deepseek-autumn-journey-v2-768p'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def prepare():
    review = json.loads((EPISODE/'production/final-film-review-v2-768p.json').read_text(encoding='utf-8'))
    film = RUNTIME/'film.mp4'
    if review['filmSha256'] != sha(film) or review['userAestheticAcceptance'] != 'pending':
        raise ValueError('Package the actually inspected user-review film')
    OUTPUT.mkdir(exist_ok=True)
    copies = {film: OUTPUT/(PREFIX+'.mp4'), EPISODE/'director-v4.md':OUTPUT/(PREFIX+'-director-v4.md'),
        EPISODE/'production/final-film-review-v2-768p.json':OUTPUT/(PREFIX+'-review.json'),
        RUNTIME/'titles.ass':OUTPUT/(PREFIX+'-titles.ass')}
    for source,target in copies.items():
        if target.exists() and sha(target) != sha(source):
            raise ValueError('Retain a different packaged candidate')
        if not target.exists():
            shutil.copyfile(source,target)
    plan = json.loads((EPISODE/'production-plan-v2-768p.json').read_text(encoding='utf-8'))
    inputs = {f'sources/S{i:02d}.mp4':RUNTIME/f'sources/S{i:02d}.mp4' for i in range(1,49)}
    for name in ['soundtrack.wav','titles.ass','clip-decisions.json','source-imports.json','segments.ffconcat']:
        inputs[name] = RUNTIME/name
    for name in ['README.md','director-v4.md','episode.json','delivery-plan-v2-768p.json',
                 'production-plan-v2-768p.json','final-assembly-plan-v2-768p.json']:
        inputs['episode/'+name] = EPISODE/name
    for source in EPISODE.glob('*v2*.json'):
        inputs['episode/'+source.name] = source
        for value in strings(json.loads(source.read_text(encoding='utf-8'))):
            candidate = (EPISODE/value).resolve()
            if candidate.is_relative_to(EPISODE) and candidate.is_file() and candidate.suffix == '.png':
                inputs['episode/'+candidate.relative_to(EPISODE).as_posix()] = candidate
    for shot in plan['shots']:
        for reference in shot.get('references',[]):
            inputs['episode/'+reference] = EPISODE/reference
    for source in (EPISODE/'assets/generated/production-v2-firstframes-001/originals').glob('*.png'):
        inputs['episode/'+source.relative_to(EPISODE).as_posix()] = source
    for source in (EPISODE/'assets/generated/production-v1-closing-composite-001').iterdir():
        if source.is_file() and source.suffix in ('.png','.json'):
            inputs['episode/'+source.relative_to(EPISODE).as_posix()] = source
    for source in (EPISODE/'production').glob('*v2*'):
        if source.is_file() and source.suffix in ('.py','.json','.md'):
            inputs['episode/production/'+source.name] = source
    for source in (ROOT/'video-maker/tools').glob('*.py'):
        inputs['tools/'+source.name] = source
    for source in (EPISODE/'reviews').glob('*.json'):
        inputs['episode/reviews/'+source.name] = source
    for source in [ROOT/'docs/deepseek-autumn-journey-v2-corrections.md',ROOT/'.gitattributes']:
        inputs[source.relative_to(ROOT).as_posix()] = source
    inventory = [{'path':name,'sha256':sha(file),'bytes':file.stat().st_size} for name,file in sorted(inputs.items())]
    archive = OUTPUT/(PREFIX+'-review-materials.zip')
    if archive.exists():
        raise ValueError('Existing package retained; verify before a new candidate')
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1) as bundle:
        for name,source in sorted(inputs.items()):
            bundle.write(source,name)
        bundle.writestr('package-inventory.json',json.dumps({'schemaVersion':'deepseek-review-package-2',
            'files':inventory,'filmSha256':sha(film),'scope':'Exact adopted48 native sources, unchanged WAV, ASS, plans, plan-declared generation references, original v2 artwork, provenance and workers. Postprocessed source bytes are authoritative; generation references are historical inputs and may differ from a final composite, particularly S48. Historical rejected/raw media remains local; all generated and inspection images remain in Git. Encoder binary versions and private semantic reviews are not bundled.'},indent=2)+'\n')
    with zipfile.ZipFile(archive) as bundle:
        bad = bundle.testzip()
        if bad:
            raise ValueError('Package CRC failure: '+bad)
    payload = sorted([*copies.values(),archive],key=lambda p:p.name)
    (OUTPUT/'SHA256SUMS.txt').write_text(''.join(f'{sha(file)}  {file.name}\n' for file in payload),encoding='utf-8')
    (OUTPUT/'package-verification.json').write_text(json.dumps({'schemaVersion':'deepseek-package-verification-2',
        'archiveSha256':sha(archive),'archiveBytes':archive.stat().st_size,'crcAllMembers':'passed',
        'sourceFiles':48,'files':[{'name':f.name,'sha256':sha(f),'bytes':f.stat().st_size} for f in payload]},indent=2)+'\n',encoding='utf-8')
    print(OUTPUT,flush=True)


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


if __name__ == '__main__':
    prepare()
