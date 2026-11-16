"""Keep the original and create a separately reviewed five-second slow-motion candidate.

Changes timing only; does not select or approve a source. GPL-3.0-only.
"""
import argparse
import json
from pathlib import Path

from reference_finisher import run,sha,write_json


def retime(source,destination,factor,reason):
    source,destination = Path(source).resolve(),Path(destination).resolve()
    if not 1 < factor <= 16 or not reason.strip() or source == destination:
        raise ValueError('Specify a separate output, a slowdown factor and its actual reason')
    receipt_file = destination.with_suffix('.json')
    identity = {'parentSha256':sha(source),'factor':factor,'frames':120,'fps':24,
                'recipe':'setpts-mci-aobmc-bidir-vsbmc-crf16-1','workerSha256':sha(__file__)}
    if destination.exists():
        record = json.loads(receipt_file.read_text(encoding='utf-8'))
        if record['identity'] != identity or record['sha256'] != sha(destination):
            raise ValueError('Preserve this output; use a new version path')
        return record
    destination.parent.mkdir(parents=True,exist_ok=True)
    run(['ffmpeg','-v','error','-n','-i',str(source),'-map','0:v:0','-an',
         '-vf',f'setpts={factor}*PTS,minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1',
         '-frames:v','120','-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p',
         '-movflags','+faststart',str(destination)],timeout=1800)
    probe = json.loads(run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(destination)]))
    stream = probe['streams'][0]
    if len(probe['streams']) != 1 or int(stream['nb_read_frames']) != 120 or stream['avg_frame_rate'] != '24/1':
        raise ValueError('Candidate is not exactly five seconds; inspect the retained output')
    run(['ffmpeg','-v','error','-xerror','-i',str(destination),'-f','null','-'])
    record = {'schemaVersion':'vivhite-local-retime-candidate-1','identity':identity,
              'sha256':sha(destination),'reason':reason,'nativeSize':[stream['width'],stream['height']],
              'durationSeconds':5,'sourceIntervalSeconds':[0,5/factor],
              'originalPreserved':True,'semanticReview':'pending','entersFilm':False}
    write_json(receipt_file,record)
    print('Created separate slow-motion candidate; actual all-frame review required.')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--destination',required=True,type=Path)
    parser.add_argument('--factor',required=True,type=float)
    parser.add_argument('--reason',required=True)
    args = parser.parse_args()
    retime(args.source,args.destination,args.factor,args.reason)
