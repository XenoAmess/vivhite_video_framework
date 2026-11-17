"""Keep the original and create a separately reviewed five- or ten-second slow-motion candidate.

Changes timing only; does not select or approve a source. GPL-3.0-only.
"""
import argparse
import json
import math
from pathlib import Path

from reference_finisher import run,sha,write_json


def retime(source,destination,factor,reason,start_seconds=0,output_seconds=5):
    source,destination = Path(source).resolve(),Path(destination).resolve()
    if (not math.isfinite(factor) or not 1 < factor <= 16
            or not math.isfinite(start_seconds) or start_seconds < 0
            or not isinstance(output_seconds,int) or output_seconds not in (5,10) or isinstance(output_seconds,bool)
            or not reason.strip() or source == destination):
        raise ValueError('Specify a separate output, a slowdown factor and its actual reason')
    receipt_file = destination.with_suffix('.json')
    expected_frames = output_seconds*24
    identity = {'parentSha256':sha(source),'factor':factor,'frames':expected_frames,'fps':24,
                'recipe':'setpts-mci-aobmc-bidir-vsbmc-crf16-1','workerSha256':sha(__file__)}
    timing = f'setpts={factor}*PTS'
    if start_seconds:
        identity.update(startSeconds=start_seconds,recipe='trim-start-setpts-mci-aobmc-bidir-vsbmc-crf16-2')
        timing = f'trim=start={start_seconds},setpts={factor}*(PTS-STARTPTS)'
    if output_seconds == 10:
        timing += ',tpad=stop_mode=clone:stop_duration=0.25'
        identity.update(recipe='trim-setpts-edgepad-mci-ten-seconds-3',edgePaddingSeconds=.25)
    if destination.exists():
        record = json.loads(receipt_file.read_text(encoding='utf-8'))
        if record['identity'] != identity or record['sha256'] != sha(destination):
            raise ValueError('Preserve this output; use a new version path')
        return record
    destination.parent.mkdir(parents=True,exist_ok=True)
    run(['ffmpeg','-v','error','-n','-i',str(source),'-map','0:v:0','-an',
         '-vf',f'{timing},minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1',
         '-frames:v',str(expected_frames),'-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p',
         '-movflags','+faststart',str(destination)],timeout=1800)
    probe = json.loads(run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(destination)]))
    stream = probe['streams'][0]
    if len(probe['streams']) != 1 or int(stream['nb_read_frames']) != expected_frames or stream['avg_frame_rate'] != '24/1':
        raise ValueError('Candidate duration is incorrect; inspect the retained output')
    run(['ffmpeg','-v','error','-xerror','-i',str(destination),'-f','null','-'])
    record = {'schemaVersion':'vivhite-local-retime-candidate-1','identity':identity,
              'sha256':sha(destination),'reason':reason,'nativeSize':[stream['width'],stream['height']],
              'durationSeconds':output_seconds,'sourceIntervalSeconds':[start_seconds,start_seconds+output_seconds/factor],
              'originalPreserved':True,'semanticReview':'pending','entersFilm':False}
    write_json(receipt_file,record)
    print('Created separate slow-motion candidate; actual all-frame review required.')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--destination',required=True,type=Path)
    parser.add_argument('--factor',required=True,type=float)
    parser.add_argument('--start-seconds',type=float,default=0)
    parser.add_argument('--output-seconds',type=int,choices=(5,10),default=5)
    parser.add_argument('--reason',required=True)
    args = parser.parse_args()
    retime(args.source,args.destination,args.factor,args.reason,args.start_seconds,args.output_seconds)
