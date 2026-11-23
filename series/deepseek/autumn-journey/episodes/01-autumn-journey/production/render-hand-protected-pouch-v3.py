"""Gate the actual hand-preserving whole-pouch inputs before compositing. GPL-3.0-only."""
import json
from pathlib import Path
import subprocess
import sys

EPISODE=Path(__file__).resolve().parent.parent
ROOT=EPISODE.parents[4]
sys.path.insert(0,str(ROOT/'video-maker/tools'))
from restore_original_occlusion import composite
from stabilize_carrier_plane import sha

plan_file=EPISODE/'postproduction-plan-v3-pouch02-768p.json'
plan=json.loads(plan_file.read_text(encoding='utf-8'))
for worker,expected in plan['workers'].items():
    if sha(ROOT/worker)!=expected:raise ValueError('Reviewed worker changed')
assets=[ROOT.parent/row['path'] for row in plan['inputs']]
for asset,row in zip(assets,plan['inputs']):
    if sha(asset)!=row['sha256']:raise ValueError('Actual reviewed input changed')
command=[sys.executable,'-X','utf8',str(ROOT/'scripts/character_review.py'),'check',
    '--episode',str(EPISODE/'episode.json'),'--document',str(plan_file)]
for asset in assets:command+=['--asset',str(asset)]
subprocess.run(command,check=True,cwd=ROOT)
destination=ROOT.parent/plan['runtimeRelativeToRepositoryParent']/'sources/S37.mp4'
if not destination.resolve().is_relative_to((ROOT.parent/'vivhite-analysis-output/deepseek/autumn-journey').resolve()):raise ValueError('Output escaped episode')
result=composite(assets[0],assets[1],destination,plan['definition'])
print('Hand-preserving candidate',result['sha256'],'actual complete review required')
