"""Prepare immutable image-first 768P generation batches; never submit HTTP. GPL-3.0-only."""
import argparse
import hashlib
import json
from pathlib import Path

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
COMMON = (
    'Use <Picture 1> as the exact first-frame composition of one uninterrupted realistic travel shot. '
    'Preserve the same ordinary location, lighting and object count. All whale-maid illustrations '
    'and embroidered faces remain inert: identical blue OPEN eyes, long navy/sea-blue hair, white '
    'frilled headband, side fins, navy/white apron dress and one whale tail. No blink, facial redraw '
    'or autonomous expression. Printed and sewn faces inherit scene shadows, never glow. '
    'Any existing real woman remains in the same feminine navy/white body crop, head/chin/face '
    'entirely outside frame. No additional person, real face, reflected human, extra hand, detached '
    'wrist, readable text, speech, singing, humming, scene cut or background reset. '
)
ACTIONS = {
    'S48': 'Locked wide fourteen-second coast. Keep exact open sky, sea, pebble shore, road, railing and houses. Existing seated whale-maid plush and hiking bag stay stable on lower-right stones. Existing whale-tail charm sways a few millimetres, waves roll gently. No tree, branch, butterfly, extra prop or enlarged toy. Full continuous fourteen seconds, no camera movement.',
    'S01': 'Same anatomically LEFT hand keeps its BACK/knuckles toward camera and palm toward curtain. Thumb and index maintain the existing opposed cloth pinch. During first three seconds gently draw the beige curtain a few centimetres LEFT, then hold. No wrist roll, palm flip, handedness swap, regrip or detached finger. Only the original connected left arm/hand visible; train scenery slides backward continuously, bag and acrylic charm remain in place.',
    'S05': 'Smooth drive-side bicycle tracking for five seconds. Woman remains SEATED on visible black saddle, rails, clamp and seatpost continuously joined to frame; hips supported. Two navy boots remain on their own opposed flat pedals, cranks180degrees apart, calm alternating pedaling immediately from frame one, about two revolutions. Preserve wheels, chainring, chain, fork and all tubes. Forest/road flow backward continuously, no reset. Torso/head/hands stay outside crop. Frame-tube whale-maid sticker stays attached and inert.',
    'S44': 'Start with fully opaque tent door ZIPPED COMPLETELY CLOSED and no outdoors visible. Hold closed0.4seconds. Existing RIGHT hand pulls the same brass slider DOWN smoothly from0.4to2seconds, teeth separating behind it. Release slider and draw the free fabric edge LEFT from2to3.2seconds, exposing an ordinary EMPTY grassy campsite; hold OPEN. Complete opening within four seconds, never reverse or close. Cloth folds aside, never dissolves. Same attached hand/wrist/forearm and navy pouch, no other limb.',
    'S47': 'Same faceless woman BEHIND bench, two attached UNCROSSED arms. Her right hand stays imageLEFT, left hand imageRIGHT, original palm/thumb orientation. Original fingertips support the doll lower sides. During0to2seconds straighten the WHOLE inert plush a few centimetres, settle its base on bench. During2to3seconds release grips, before4seconds move hands slightly outward along OWN sides and rest; hold through5seconds. No crossing, palm flip, bent-back wrist, extra finger, arm swap, hand through doll or touching its face. Preserve original sewn eyes and whole toy.'
}
ACTIONS.update({
    'S03':'Below-waist tracking of the same woman walking forward continuously. Navy/white skirt and bag sway gently, shoes take alternating supported steps, round whale-maid badge stays printed and open-eyed. Same empty platform and coherent background.',
    'S04':'Locked empty station-bench view. Existing travel bag stays still; attached whale-maid acrylic charm sways gently once with a slight breeze, retaining rigid clear contour and printed expression. Background only soft natural motion.',
    'S06':'Fixed empty tram-window composition. Sticker remains adhered to exactly the same glass spot, no redraw or blink; exterior buildings move smoothly across the window. Only original seat reflection, no new reflected person. No generated title; lettering added in post.',
    'S07':'The same two legs begin ordinary walking IMMEDIATELY. Continuous alternating steps and sensible weight transfer, natural knees/ankles, no initial freeze or limp. Navy skirt and printed pouch sway with steps; smooth low tracking with continuous leaf-covered path.',
    'S08':'Fixed empty forest-bench view. Whole seated sewn plush and bag remain stable. Leaf shadows drift slowly over the headband, blue fabric hair and embroidered face; eyes remain sewn OPEN with constant shape. No doll animation or extra object.',
    'S09':'Same one hand gently glides a few centimetres along the wooden rail, wrist attached naturally. Bottle stays planted on the rail, printed character fixed; lake ripples softly, no additional hand or bottle.',
    'S10':'Keep illustrated whale-girl FROM BEHIND, two hands resting naturally on rail. Only long blue hair, skirt hem and tail tip move slightly in breeze, torso stable and no head turn. Ordinary water and park background remain empty; no profile or face ever revealed.',
    'S11':'Same hand holds card steadily BY ITS EDGE with natural finger joints. One original yellow leaf drifts past in front; printed character remains fixed to transparent card, actual scene visible through unprinted area. No face or extra hand.',
    'S12':'Same connected female hand makes ONE small deliberate oar stroke. Oar rotates coherently in its original rowlock, pushes a ripple in the lake; boat and sticker remain rigid and consistent. Preserve thumb/grip, no additional hand or oar.',
    'S13':'Same hand maintains umbrella grip as camera tracks slowly along empty wet street. Attached acrylic charm sways slightly near cuff, fixed printed eyes; no wrist flip, extra hand, added pedestrian or face/reflection.',
    'S14':'Locked close shot of wet bag and badge. One existing water droplet slides gently along metal rim and onto fabric; printed eyes and whole badge remain unchanged. Original rainy shelter and wet street, empty throughout.',
    'S15':'Same TWO connected hands grasp the cup securely; during first two seconds lift the whole cup from table slowly by about8cm, then hold it steadily through the remaining take. Fingers maintain real contact, cup never deforms, no repetitive touching, no mouth or face revealed.',
    'S16':'Below-waist view: the same two shoes make two small deliberate alternating uphill steps on the EXISTING stairs, soles land on their real treads and weight shifts naturally. Navy skirt and printed bag move with body, no freeze, detached foot or new step geometry.',
    'S17':'Fixed medium-wide greenhouse view. Complete clear acrylic standee and its base remain rigid and stationary, printed OPEN blue eyes and body never animate. Only existing foliage and soft leaf shadows move slightly; clear edges and transparency preserved.',
    'S18':'Locked real autumn meadow. Grass and reeds move gently in one breeze. Existing cropped bag and attached blue whale-tail charm stay in place with tiny physically attached sway. No new person, butterfly, floating symbol or prop.',
    'S19':'Fixed bus-window view: same relaxed female hands stay naturally attached and resting, existing printed navy pouch remains below. Original mountain scenery slides continuously outside, soft travel vibration, no new limb or facial reflection.',
    'S20':'One uninterrupted TEN-SECOND alpine-lake shot, same seated fabric whale-maid plush and hiking bag on foreground rock. Camera very slowly retreats a short distance, revealing slightly more ordinary lake; gentle water and cloud shadows. Plush/bag remain securely supported and inert, eyes fixed OPEN. No cut or resetting scene.',
    'S21':'Same cable-car low crop, boots and knees stationary, plush supported in existing bag opening. Snowline and dark trees move slowly below outside window. Tiny natural vibration only; no toy animation, limb change or reflected human face.',
    'S22':'Fixed snowy bag/badge close view. A few existing tiny snow grains soften into water at metal rim. Keep printed open eyes and blue portrait entirely fixed; no facial change or camera cut.',
    'S23':'Same illustrated whale-girl FROM BEHIND on mountain path, stable stance. Blue long hair and navy skirt move softly with wind, one attached tail remains coherent. No head turn or human face; distant ridges and sky steady.',
    'S24':'Same crouched faceless woman lets a small amount of sand fall slowly from the original open hand; other hand remains on bag with natural anatomy. Thin sand stream obeys gravity, navy charm moves only with breeze. No limb duplication or hand flip.',
    'S26':'Empty car interior. Existing navy printed pouch stays on seat with light road vibration, outside dry fields and road move continuously backward. Print inert, no facial animation or added passenger/reflection.',
    'S27':'Fixed close view of original attached acrylic charm, ring and seat fabric. One gentle vehicle bump makes chain and its shadow swing once then settle. Charm remains one rigid physical piece; no floating ring or new object.',
    'S28':'Same TWO hands slowly unfold the EXISTING paper OUTWARD and DOWN on both sides of bread, bringing it flat on table during first three seconds, then resting by edges. Bread above remains clean and solid: no steam, white ghost sheet or floating patch. Existing cup stays stable, print inert. No other hand or face.',
    'S29':'Fixed empty harbor tabletop/bench. Plush stays seated securely against original bag, badge and embroidered eyes fixed. Gentle small boat/water motion in background, slight reflected light only, no new person or boat.',
    'S30':'Same one visible hand moves lightly a few centimetres over original rope knot, preserving connected wrist and finger contacts. Existing printed cloth bag sways softly with ferry. Keep rail and rope structure coherent; no other hand.',
    'S31':'Same faceless female crop and hand resting on ferry rail, navy bag and attached charm. Breeze tilts charm gently backward; white wake expands continuously behind ferry. Real limb connections and print remain fixed.',
    'S32':'Same TWO hands keep holding original camera naturally. Make one small framing adjustment with connected thumbs/fingers, keep lens rigid and sticker fixed; no face enters crop or reflection, sea/rail background remains continuous.',
    'S34':'Same illustrated whale-girl FROM BEHIND takes ONE slow small step forward along existing path, complete anatomy and one attached tail coherent. Long blue hair and skirt ties move with wind; no turning toward camera or revealing face.',
    'S35':'Same original hand gently skims a small patch of shallow stream water with naturally connected fingers/wrist. Bottle stays on dry rock, printed character inert; ripples spread from contact, no new hand or floating bottle.',
    'S36':'Fixed empty waterfall/card scene. Transparent card stays supported at original position, print remains fixed OPEN-eyed. A few existing water droplets slide along card EDGE, not over changing face; background water flows softly.',
    'S37':'Same cropped female lower body walks forward naturally with alternating supported steps, navy/white skirt and printed tote swaying together. Ordinary crops ripple in breeze, same empty lane, no extra limb or person.',
    'S38':'Same original hand rests then relaxes slightly on bridge rail, thumb/wrist orientation unchanged. Existing acrylic charm sways faintly in warm lamp light, quiet water below; no glowing face, new human or reflection.',
    'S39':'Locked EMPTY dusk street. Existing lantern sways gently and its reflection shifts over glass. Small matte whale silhouette sticker stays physically adhered and inert at original corner, no flying whale or new person.',
    'S40':'Locked EMPTY night-train glass view. Original whale-maid sticker stays exactly fixed and open-eyed. Exterior blue/pink light bands move smoothly across glass; original seat reflection only, no passenger or face.',
    'S41':'Fixed empty twilight lookout bench. Plush remains seated against bag with eyes embroidered OPEN and unchanging. Light breeze moves existing loose fabric and nearby foliage a little; distant town lights shimmer gently under same dusk exposure.',
    'S42':'Same hand slowly lowers existing ceramic mug by its HANDLE onto table during first1.5seconds, cup base makes firm contact. Relax grip and withdraw fingers naturally by2.5seconds, hold through end. Other original hand stays resting on lap. Preserve two connected arms only, no deforming handle or new face.',
    'S43':'Fixed EMPTY campsite. Clear card remains upright and stable on table with identical whole printed whale-maid and clear unprinted area. Existing tent fabric moves softly in breeze, warm lamp flickers very gently, no new person, floating card or animated face.',
    'S45':'Low cropped view of same luggage wheels and two navy boots moving FORWARD over existing pavement. Natural continuous wheel rotation and alternating steps, existing attached acrylic charm swings briefly. No extra foot, backwards wheel or other person.',
    'S46':'Same ONE female forearm and hand at vehicle window slowly relaxes and opens fingers in natural connected sequence, no palm flip or backward thumb. Printed sticker stays fixed on glass; coast moves smoothly outside, no reflected face or extra hand.'
})


def prepare(name, ids):
    base = json.loads((ROOT/'series/vivhite/autumn-journey/episodes/01-autumn-journey/delivery-plan-v13-native-4k.json').read_text(encoding='utf-8'))
    source = {row['id']: row for row in base['shots']}
    frame, shots, exceptions = 0, [], {}
    selections_file = EPISODE/'production/first-frame-selections-v1.json'
    selections = json.loads(selections_file.read_text(encoding='utf-8')) if selections_file.exists() else {}
    for sid in ids:
        old = source[sid]
        relative = selections.get(sid, f'assets/generated/production-v1-firstframes-001/scenes/{sid}-v1.png')
        actual = EPISODE/relative
        digest = hashlib.sha256(actual.read_bytes()).hexdigest()
        seconds = old['seconds']
        if sid in ('S20', 'S48'):
            exceptions[sid] = seconds
        action = ACTIONS[sid]
        prompt = COMMON+action
        if sid in ('S04','S06','S08','S14','S17','S18','S20','S22','S26','S27','S29','S36','S39','S40','S41','S43','S48'):
            start = COMMON.index('Any existing real woman')
            end = COMMON.index('No additional person', start)
            prompt = (COMMON[:start]+COMMON[end:]+
                'OBJECT-ONLY unoccupied composition: every foreground and background item is the original '
                'nonliving merchandise, furniture or landscape. No human torso, neck, arms, legs or '
                'humanoid silhouette occupies this shot. Keep the exact same empty space around all objects. '+action)
        shots.append({'id':sid, 'seconds':seconds, 'sourceSeconds':seconds if sid in exceptions else 5,
            'startFrame':frame, 'finalFilmStartFrame':old['startFrame'], 'seed':2026112300+int(sid[1:]),
            'mode':('A' if sid in ('S10','S23','S34') else 'I' if sid in ('S06','S18','S39','S40','S48')
                    else 'O' if sid in ('S04','S08','S14','S17','S20','S22','S26','S27','S29','S36','S41','S43') else 'H'),
            'action':action, 'generationAction':action,
            'soundDescription':'Quiet location ambience; final instrumental is mixed separately.',
            'prompt':prompt, 'references':[relative], 'referenceSha256':[digest]})
        frame += seconds*30
    plan = {'schemaVersion':'vivhite-local-two-stage-video-1', 'episodeId':'01-autumn-journey',
        'revision':1, 'stage':'draft', 'model':'fasth3-omni-bf16', 'width':1344, 'height':768,
        'sourceSize':'1344x768', 'fps':30, 'sourceFps':24, 'sourceSeconds':5, 'maxShotSeconds':5,
        'totalFrames':frame, 'noSpeech':True, 'noHumanFaces':True, 'noAddedPeople':True,
        'allCharactersFemale':True, 'decoderLayers':36, 'numInferenceSteps':8,
        'shotDurationExceptions':exceptions, 'shots':shots, 'titleOverlays':[], 'closingCredit':'',
        'scope':'Generation batch only; finalFilmStartFrame retains the original205second positions. No finished-film approval.',
        'director':'director-v1.md', 'finalTargetFrames':6150, 'finalTargetSeconds':205}
    target = EPISODE/f'production-plan-v1-{name}-768p.json'
    if target.exists():
        raise ValueError('Never overwrite an already prepared plan')
    target.write_text(json.dumps(plan, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--shots', required=True)
    args = parser.parse_args()
    prepare(args.name, args.shots.split(','))
