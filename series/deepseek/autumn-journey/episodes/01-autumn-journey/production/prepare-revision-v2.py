"""Prepare the user's seven requested corrections without changing timing. GPL-3.0-only."""
import copy
import hashlib
import json
from pathlib import Path

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]


def write_new(path, data):
    if path.exists():
        raise ValueError('Keep immutable prior revision: '+str(path))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def prepare():
    base = json.loads((EPISODE/'production-plan-v1-768p.json').read_text(encoding='utf-8'))
    originals = {s['id']: s for s in base['shots']}
    actions = {
        'S16': 'Low REAR view of the existing woman climbing FORWARD UP these stone stairs. Camera sees heels and backs of shoes; all toes face AWAY from camera UPHILL throughout. Beginning immediately, left foot lifts forward onto next higher real tread, left sole plants and supports weight, then right foot passes it FORWARD and lands on the following higher tread. Continue alternating naturally uphill for five seconds. Hips gain height and move AWAY from camera; no backward shuffle, walking down, sliding feet or reverse playback. Camera stays behind below waist, no head, chin, face, hands or additional person. Keep original shoes, stockings, skirt, railing and continuous stair geometry. Bag tiny whale motif is inert.',
        'S10': 'Same whale-maid FROM BEHIND resting both original hands on the river railing for five seconds. Locked camera; only very soft hair-tip and skirt breeze and ordinary flowing river. Keep the corrected short curved SINGLE tail stalk attached at lower back, terminating in exactly TWO broad left/right fluke lobes. Tail remains still and keeps its first-frame topology. No central third spike, vertical dangling extension, extra fin, tail duplication, head turn or new person.',
        'S23': 'Same whale-maid FROM BEHIND looking at mountain ridges for five seconds. Locked camera, body stays in original stance, only slight hair and hem breeze. Keep corrected tail rigidly coherent: one curved stalk from lower back ENDS at exactly two broad left/right fluke lobes. No continuation beyond split, central third prong, extra fin or new tail. No head turn, face, new person or background reset.',
        'S34': 'Smooth rear tracking below the shoulders of this same woman walking FORWARD along the existing coastal path, natural alternating planted steps from the first frame. Only original two arms and legs. Keep corrected tail shape attached beneath waist bow: ONE short curved stalk ENDS at two broad left/right flukes, no extra central protrusion. Tail keeps the original exact topology and moves only with the skirt. Head and face always outside crop. No new person, limb, scene cut or background reset.',
        'S37': 'Smooth REAR tracking of the SAME cropped woman walking naturally FORWARD on this empty farm lane for five seconds, alternating supported footsteps immediately. Original right hand holds original rectangular cloth pouch by its top corner; keep pouch broad face facing camera, gentle whole-pouch sway only, fabric nearly flat. The ENTIRE printed chibi character is dry ink, fixed relative to pouch seams: blue OPEN eyes, hair, body, shoes and tail absolutely unchanged, never independent motion, blinking or facial redraw. Keep corrected costume tail: one curved stalk terminating in exactly TWO broad flukes; no central third spike, dangling stem beyond fork, extra fin or second tail. Only original two arms and two legs, no face, reflected person, new person or cut.'
    }
    shots = []
    frame = 0
    for sid in ['S16','S10','S23','S34','S37']:
        reference = f'assets/generated/production-v2-firstframes-001/scenes/{sid}-v1.png'
        action = actions[sid]
        row = copy.deepcopy(originals[sid])
        for key in ['sourceFile','sourceSha256','originalGenerationAction']:
            row.pop(key, None)
        row.update(startFrame=frame, finalFilmStartFrame=originals[sid]['startFrame'],
                   references=[reference], referenceSha256=[hashlib.sha256((EPISODE/reference).read_bytes()).hexdigest()],
                   seed=2026112400+int(sid[1:]), action=action, generationAction=action,
                   prompt='Use <Picture 1> as the exact first frame of one uninterrupted realistic shot. Same location, composition, exposure and subject count. No speech, song, text or new object. '+action)
        shots.append(row)
        frame += 150
    plan = copy.deepcopy(base)
    for key in ['assemblyOnly','sourceAdoptionsSha256','episodeAssemblyWorkers','soundtrack','directorSha256']:
        plan.pop(key,None)
    plan.update(revision=2, shots=shots, totalFrames=frame, shotDurationExceptions={},titleOverlays=[],
                director='director-v4.md', scope='User-requested correction generation only. Preserve v1. Final film remains205seconds; no source automatically accepted.')
    write_new(EPISODE/'production-plan-v2-repair01-768p.json',plan)
    deployment=(EPISODE/'production/deploy-generation-batch-v1.py').read_text(encoding='utf-8')
    for prefix in ['production-plan-', 'production-', 'Journey-', 'source-generation-', 'deployment-']:
        deployment = deployment.replace(prefix+'v1-', prefix+'v2-')
    target=EPISODE/'production/deploy-generation-batch-v2.py'
    if target.exists():
        raise ValueError('Keep deployment version')
    target.write_text(deployment,encoding='utf-8')


if __name__ == '__main__':
    prepare()
