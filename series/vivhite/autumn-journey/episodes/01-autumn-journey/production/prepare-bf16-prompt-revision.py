"""Preserve calibration outputs and prepare scene-specific remaining requests.

No inference submission or semantic acceptance is performed here. GPL-3.0-only.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0,str(ROOT/'video-maker/tools'))
from reference_finisher import sha,write_json

VISUALS = {
 'S01':'The existing cropped female forearm gently draws the train curtain aside. Her small acrylic bag charm sways slightly while ordinary fields pass outside the window.',
 'S02':'The unoccupied lake, curved bank and distant terrain remain exactly as pictured. Natural cloud shadows drift slowly across the water; the camera is steady.',
 'S03':'The existing woman is visible only from the waist down on the platform, carrying the same badge-decorated bag. Her white legwear, violet boots and feminine skirt keep their original appearance as she walks.',
 'S04':'The same bag rests beside the terrace bench. Only the existing small acrylic charm and its shadow sway subtly over the wood grain.',
 'S05':'Only the same cropped female legs, white legwear, violet boots, bicycle pedal and frame are visible. One gentle pedalling movement carries the fixed frame sticker through tree shadows.',
 'S06':'The original small Vivhite sticker stays fixed in the corner of the tram glass. Ordinary colored building fronts slide past outside. The broad blank glass stays clean and unlettered.',
 'S07':'The same violet boots step gently over thin fallen leaves. The small fabric pouch at the edge of the feminine skirt sways with that one person.',
 'S08':'The exact one silver-lavender-haired Vivhite fabric doll and bag stay seated on the forest bench. Only leaf shadows and a little cloth edge move in the breeze.',
 'S09':'The same cropped female hand glides along the wooden railing beside the existing water bottle strap. Its small printed Vivhite illustration stays fixed to the material.',
 'S10':'The single existing illustrated woman rests at the bridge railing, seen strictly from behind. The back of her hat and silver-blue bob stay toward the camera while her ribbons move lightly.',
 'S11':'The existing cropped hand holds the transparent character sheet steadily by its edge. One yellow leaf passes slowly in front, with the sheet illustration unchanged.',
 'S12':'The same female hand and sleeve hold the oar for one gentle stroke beside the small boat. Water ripples spread near the existing fixed boat-edge sticker.',
 'S13':'The original cropped female hand holds the umbrella handle in ordinary rain. The same small acrylic charm touches the white-violet sleeve lightly.',
 'S14':'The original bag remains under the eaves. One water drop slides slowly across the existing metal badge toward its edge while background wet-road lights remain soft.',
 'S16':'The same woman is framed only below the knees as her violet boots climb the stone steps. The existing fabric pouch remains attached to her bag.',
 'S17':'The existing rigid acrylic character stand stays motionless on the greenhouse table. Natural leaf shadows cross its surface while the camera gently approaches its thin edge.',
 'S18':'Only the existing slender pink-violet grass heads, pale reeds and small blue corner graphic fill this unoccupied field view. The original plants sway gently together in the wind.',
 'S19':'The same cropped sleeve and female hand rest at the bus window beside the gray-violet pouch. Ordinary mountain scenery slides past outside the original glass.',
 'S20B':'A wide view of the same ordinary alpine lake, rocky mountains and clouded sky. The exact one silver-lavender-haired Vivhite doll and charcoal bag remain small together on the lower-left rock. Camera nearly fixed; slow cloud shadows and fine water ripples.',
 'S21':'The existing violet boots and white-covered lower legs stay inside the cable-car cabin beside the same Vivhite doll at the bag opening. Snow line and dark trees move slowly below.',
 'S22':'Close view of the original bag corner and its same round badge. A few small snow grains settle and melt slowly along the metal edge.',
 'S23':'The same illustrated woman stands quietly on the mountain path, strictly back-facing throughout. The back of her silver-blue bob, white hat and feminine violet-white costume remain toward camera; cloth shifts lightly in the mountain breeze.',
 'S24':'The same cropped female hand lets a small stream of fine sand fall through her fingers. The existing bag charm moves gently in the same breeze over the ordinary sandy ground.',
 'S25':'The same empty sandstone canyon and ordinary light remain unchanged. A thin low dust wisp crosses gently near the ground in a steady wide view.',
 'S26':'The original Vivhite fabric pouch rests beside the vehicle window. Its corner trembles subtly with the moving car while the ordinary open road passes outside.',
 'S27':'Close view of only the existing acrylic charm, seat fabric and the charm shadow. A single small vehicle jolt makes the shadow rise and settle.',
 'S28':'Only the same cropped female hand unwraps the pastry paper beside the cup and its existing fixed Vivhite sticker. A little steam rises; background remains the pictured fruit and fabric.',
 'S29':'The original one Vivhite doll is supported by the same bag on the harbor wood surface. Small colored boats remain in the background while water reflections move subtly.',
 'S30':'The same cropped female hand gently touches the boat rope knot beside the existing printed fabric pouch. Rope, cloth and water shift softly with the boat.',
 'S31':'Only the same female forearm and lower bag remain beside the ferry railing. The existing charm leans gently in the sailing breeze above the original wake.',
 'S32':'The same cropped female hands hold the camera with its original fixed Vivhite sticker. A very small camera drift keeps the hands, strap and distant coast in the same composition.',
 'S33':'The unoccupied dark coastal rocks stay exactly as pictured. One small wave recedes, leaving a thin bright wet line on the rock.',
 'S34':'The same single illustrated woman remains strictly back-facing on the coastal path. One relaxed forward step and a light movement of her ribbons occur under the original broad sky.',
 'S35':'The existing cropped female hand skims the shallow stream beside the original sticker-decorated water bottle on dry rock. Water flows gently between the fingers.',
 'S36':'The same transparent character plate rests at the stream railing. A few drops move slowly along its edge while the distant waterfall remains softly textured.',
 'S37':'The same woman is framed only from the waist down on the rural path. She walks slowly in her feminine white-violet skirt, white legwear and violet boots while the existing tote brushes her skirt.',
 'S38':'The same cropped female hand rests softly on the evening bridge railing. The existing small bag charm catches one warm light while water shadows move slowly below.',
 'S39':'The same unoccupied small street and lanterns remain at dusk. The existing tiny blue graphic stays anchored in the corner of the plain glass as the lanterns sway subtly.',
 'S40':'The existing small Vivhite sticker stays perfectly fixed in the night-train window corner. Soft pink-blue exterior light passes slowly; only the original seat-fabric reflection remains inside.',
 'S41':'The same one Vivhite fabric doll and bag rest on the viewpoint bench. Ordinary town lights twinkle softly and one cloth edge lifts slightly in the night breeze.',
 'S42':'Only the same female hand and forearm gently place the hot cup on the camping table. The existing cup illustration remains identical while a little steam rises into the dark-blue background.',
 'S43':'The same little lamp illuminates the existing transparent character plate outside the tent. Ordinary night sky remains beyond it; the original tent cloth moves softly in the breeze.',
 'S44':'Only the same cropped female hand and forearm gather the tent flap and move the zipper gently. The original Vivhite fabric pouch shifts slightly beside the tent cloth.',
 'S45':'Low view of the same luggage wheels, female violet boots and white legwear moving over the ordinary pavement. The existing bag charm sways once near the edge.',
 'S46':'Only the same female forearm and relaxed open hand remain at the vehicle window. The original fixed Vivhite sticker shares the frame with the coast outside.',
 'S47':'Only the same cropped female hand gently sets the exact existing Vivhite fabric doll beside the bag on the seaside bench, then withdraws. The soft hat settles naturally.',
 'S48':'Only the original sea, small waves, stony and sandy shore, distant coastal houses, roadside rails and utility poles appear beneath the ordinary dusk sky. The existing tiny blue butterfly graphic stays in the lower-right corner. Its two wings perform just one very slow, smooth opening and closing over about four seconds. Steady camera, restrained sea motion, unoccupied shore and clean sky.'
}


def prepare(previous,output):
    previous,output = previous.resolve(),output.resolve()
    if previous == output or output.is_relative_to(previous) or previous.is_relative_to(output):
        raise ValueError('Preserve calibration in its own directory')
    old_file = EP/'production-plan-v5-bf16-768p.json'
    plan = json.loads(old_file.read_text(encoding='utf-8'))
    old_hash = sha(old_file)
    output.mkdir(parents=True,exist_ok=True)
    for name in ('motion-reference','uploads'):
        for source in (previous/name).glob('*'):
            if source.is_file():
                target = output/name/source.name
                target.parent.mkdir(exist_ok=True)
                if target.exists() and sha(target) != sha(source):
                    raise ValueError('Existing revision input differs')
                if not target.exists():
                    shutil.copyfile(source,target)
    for name in ('soundtrack.wav','soundtrack-receipt.json'):
        if not (output/name).exists():
            shutil.copyfile(previous/name,output/name)
    decisions = json.loads((previous/'clip-decisions.json').read_text(encoding='utf-8'))
    keep = ('S15','S20A')
    plan['reusedSources'] = []
    for identity in keep:
        decision = next(row for row in decisions['shots'] if row['id']==identity)
        if not decision['allSourceFrameReview'] or any(decision[key]!='passed' for key in
                ('noHumanFaces','noAddedPeople','allCharactersFemale','costumeStyle','motionAndContinuity','merchandiseBehavior')):
            raise ValueError('Only actually accepted calibration sources may be reused')
        job = json.loads((previous/'jobs'/f'{identity}.json').read_text(encoding='utf-8'))
        for relative in (job['sourceFile'],job['rawFile'],f'jobs/{identity}.json',f'requests/{identity}.json',
                         f'clip-inspection/{identity}.json',f'clip-inspection/{identity}-frame-metrics.jsonl',
                         f'logs/{identity}-polls.jsonl',f'logs/{identity}-server.log'):
            source,target = previous/relative,output/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and sha(target) != sha(source):
                raise ValueError('Preserve existing revision result')
            if not target.exists():
                shutil.copyfile(source,target)
        plan['reusedSources'].append({'shotId':identity,'path':job['sourceFile'],
            'sha256':job['sourceSha256'],'sourcePlanSha256':old_hash,'sourceJobId':job['jobId'],
            'scope':'Same newly generated native 768P bytes and unchanged shot action/seed/prompt; all 120 source frames actually reviewed.'})
    for shot in plan['shots']:
        if shot['id'] in keep:
            continue
        framing = ('The same one adult woman remains visible only in the original feminine body crop; '
                   'her head stays wholly above or beyond the frame. The original white/deep-violet/gold costume remains identical. '
                   if shot['mode']=='H' else
                   'Only the existing illustrated woman appears, strictly from behind for the entire shot. '
                   if shot['mode']=='A' else 'The original environment remains unoccupied by people throughout. ')
        illustration = ('The exact existing Vivhite fabric doll keeps the same sewn face pattern, expression, costume and seated pose, as an inert physical object. '
                        if shot.get('designMaster','').endswith('M04-plush-v1.png') else
                        'Any existing printed illustration stays fixed to its original surface. '
                        if shot['mode'] not in ('A','W') and shot['id'] not in ('S18','S39','S48') else '')
        shot['prompt'] = ('One uninterrupted, quiet realistic travel shot. Picture 1 defines the first-frame composition and all scene contents. '
            'Video 1 supplies the restrained camera tempo. Keep the same ordinary location, natural lighting, colors and physical objects. '
            + framing + VISUALS[shot['id']]+' '+illustration+
            'Preserve the exact original population and object count. No extra person or body part, no real face or facial fragment anywhere, including reflections and background. '
            'No cuts, readable lettering, subtitles, credits, speech, singing or other voices.')
        if shot['id']=='S48':
            shot['seed'] += 100
    plan['promptRevision'] = {'id':'scene-specific-positive-002','previousPlanSha256':old_hash,
        'reason':'Rejected S48 introduced an unrelated giant toy and flowers absent from verified references. Remaining prompts now describe only their actual scene elements, without irrelevant merchandise nouns in pure landscape shots.'}
    destination = EP/'production-plan-v5-bf16-768p-r2.json'
    write_json(destination,plan)
    revised_decisions = {'schemaVersion':'vivhite-clip-decisions-1','sourcePlanSha256':sha(destination),
        'shots':[copy.deepcopy(row) for row in decisions['shots'] if row['id'] in keep]}
    for row in revised_decisions['shots']:
        row['reviewReuseFromPlanSha256'] = old_hash
    write_json(output/'clip-decisions.json',revised_decisions)
    write_json(EP/'production/rejected-S48-v5-001.json',{
        'schemaVersion':'vivhite-rejected-calibration-1','shotId':'S48','sourcePlanSha256':old_hash,
        'sourceSha256':next(row['sourceSha256'] for row in decisions['shots'] if row['id']=='S48'),
        'decision':'rejected','method':'assistant-all-120-source-frame-review',
        'reason':'Invented giant unrelated teddy bear, blinking and new foreground flowers. Both uploaded references were checked and contain none of these additions.',
        'entersFilm':False,'enters2K':False,'originalAndAllEvidencePreserved':True})
    print('Prepared separate prompt revision with 2 exactly reused, actually accepted native sources; 47 outputs still required.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    prepare(args.previous,args.output)
