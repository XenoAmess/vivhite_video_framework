"""Prepare the two rejected motion revisions without changing the film timeline. GPL-3.0-only."""
import copy
import hashlib
import json
from pathlib import Path

EPISODE = Path(__file__).resolve().parent.parent

ACTIONS = {
    'S37': '田边短暂停步，女性背影局部的原手放在木栏左侧；完整原布包稳放栏木右侧，包底、四角、拉链和整张印花共同固定，背景草叶与发梢微动。单尾柄只以左右两叶收束，不出现头脸。',
    'S47': '女性原有双手从玩偶下部两侧扶稳，将整个玩偶沿椅面向画面左侧平移约8–10厘米，底部不离开椅面；玩偶留在新的位置后松开双手。四秒内完成，最后至少一秒稳放；手腕自然相连、不交叉，不把玩偶颠起后放回原位。',
}
GENERATION = {
    'S37': 'Locked-off TRIPOD, absolutely no camera translation, zoom or reframing. The SAME cropped female traveler pauses beside the same gate. Her original right hand rests on the wood LEFT of the pouch and NEVER touches or crosses the pouch. Keep the ENTIRE upright structured ivory pouch fully motionless on the horizontal gate ledge: its bottom, outer silhouette, four corners, zipper and WHOLE dry ink character remain together as one physically supported still object. Blue eyes OPEN and inert. Only a subtle ordinary breeze in background grasses, hair tips and skirt hem, plus very small natural settling of the original stance. Costume tail has one stalk ending in exactly TWO flukes, no center third spike. No new limb, person, face, chin, head, reflected human or camera cut. Do not animate or redraw any part of the print.',
    'S47': 'Locked tripod, same bench, same sea, same faceless female torso, exactly the original TWO naturally attached UNCROSSED arms and hands. Perform ONE purposeful horizontal repositioning of the WHOLE INERT plush, NOT a bounce. Starting immediately, both original hands at its LOWER SIDES gently SLIDE the entire seated doll to IMAGE LEFT by about ONE QUARTER OF ITS BODY WIDTH (about8to10cm, roughly80to110 image pixels), while the bottom remains in continuous contact with the bench. Slide happens during0to2seconds. By2.5seconds stop at this NEW LEFT position, then release both grips by3seconds and let hands withdraw just slightly outward on their OWN sides. From3to5seconds hold doll stably at its NEW position, never return it to the starting point. NO LIFTING, no up-down bob, no springback, no face touching, no arm crossing, no palm flip, no hand through doll, no extra finger/hand/person. Preserve entire inert toy proportions, fabric embroidery, OPEN blue eyes, hair, dress, shoes and attached two-fluke whale tail. Head, neck, chin and human face stay outside the frame; ocean moves naturally. Whole action complete before4seconds.',
}


def save_new(path, value):
    content = (json.dumps(value, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    if path.exists() and path.read_bytes() != content:
        raise ValueError('Prior candidate retained: '+str(path))
    path.write_bytes(content)


def main():
    base = json.loads((EPISODE/'production-plan-v2-768p.json').read_text(encoding='utf-8'))
    director = (EPISODE/'director-v4.md').read_text(encoding='utf-8')
    director = director.replace('768P返修版导演稿 v4', '768P二次返修导演稿 v5')
    lines = director.splitlines()
    for index,line in enumerate(lines):
        for sid,action in ACTIONS.items():
            if line.startswith('| '+sid+' |'):
                cells = line.split('|')
                cells[4] = ' '+action+' '
                lines[index] = '|'.join(cells)
    director = '\n'.join(lines)+'\n\n## v3用户追加返修\n\n'
    director += 'v2的S37袋面关键帧投射仍被用户指出错位，本轮不再沿用该片。S37重新构图为田边停步，整个实体包稳放栏木；原包轮廓、拉链和印花一起保留，排除手部遮挡。S47重新生成沿椅面横向挪动，终点须与起点不同，不能只有上下颠动。仅替换这两镜，其余46镜源片、48镜时长、标题、献词及配乐保持v2；仍为205秒／6150帧。新源片及成片需要另行实际复核，旧版保留。\n'
    target = EPISODE/'director-v5.md'
    if target.exists() and target.read_text(encoding='utf-8') != director:
        raise ValueError('Keep prior director')
    target.write_text(director,encoding='utf-8',newline='\n')
    plan = copy.deepcopy(base)
    for key in ['assemblyOnly','sourceAdoptionsSha256','episodeAssemblyWorkers','soundtrack','directorSha256','supersedesSourcePlanSha256']:
        plan.pop(key,None)
    shots = []
    for index,sid in enumerate(['S47','S37']):
        shot = copy.deepcopy(next(s for s in base['shots'] if s['id']==sid))
        for key in ['sourceFile','sourceSha256','originalGenerationAction','actualCorrectionPlan']:
            shot.pop(key,None)
        reference = ('assets/generated/production-v3-firstframes-001/scenes/S37-v1.png' if sid=='S37'
                     else 'assets/generated/production-v1-firstframes-001/scenes/S47-v1.png')
        shot.update(seconds=5,sourceSeconds=5,startFrame=index*150,
                    finalFilmStartFrame=4410 if sid=='S37' else 5610,
                    action=GENERATION[sid],generationAction=GENERATION[sid],
                    references=[reference],referenceSha256=[hashlib.sha256((EPISODE/reference).read_bytes()).hexdigest()],
                    seed=2026112500+int(sid[1:]),
                    prompt='Use <Picture 1> as the exact first frame of a single uninterrupted realistic5second shot. No speech, lyrics, new text or added person. '+GENERATION[sid])
        shots.append(shot)
    plan.update(revision=3,shots=shots,totalFrames=300,titleOverlays=[],shotDurationExceptions={},
                director='director-v5.md',scope='Two user-rejected shots only. S47 source5seconds, final4seconds. S37 final5seconds. Final film205seconds unchanged. No automatic acceptance.')
    save_new(EPISODE/'production-plan-v3-repair01-768p.json',plan)
    deployer = (EPISODE/'production/deploy-generation-batch-v2.py').read_text(encoding='utf-8')
    deployer = deployer.replace('-v2-','-v3-')
    deployer = deployer.replace('assets/generated/production-v2-firstframes-001','assets/generated/production-v3-firstframes-001')
    out = EPISODE/'production/deploy-generation-batch-v3.py'
    if not out.exists(): out.write_text(deployer,encoding='utf-8',newline='\n')
    print('Prepared new immutable director and two-shot generation plan')


if __name__ == '__main__':
    main()
