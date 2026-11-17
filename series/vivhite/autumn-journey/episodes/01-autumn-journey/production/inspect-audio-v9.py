"""Compare the complete delivered AAC with the bound procedural WAV.

Numerical evidence does not assert listening or semantic sound recognition.
GPL-3.0-only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import wave

import numpy as np


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inspect(directory):
    directory = directory.resolve()
    film, soundtrack = directory/'film.mp4', directory/'soundtrack.wav'
    probe = json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(film)]))
    audio = next(s for s in probe['streams'] if s['codec_type'] == 'audio')
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    if (int(audio['sample_rate']), audio['channels']) != (48000, 2):
        raise ValueError('Expected the original stereo 48 kHz soundtrack')
    if any(abs(float(value)-205) > 0.00001 for value in
           (audio['duration'], video['duration'], probe['format']['duration'])):
        raise ValueError('All streams and container must remain exactly 205 seconds')
    with wave.open(str(soundtrack), 'rb') as stream:
        if (stream.getframerate(), stream.getnchannels(), stream.getsampwidth(), stream.getnframes()) != (48000, 2, 2, 9840000):
            raise ValueError('Unexpected source WAV format or sample count')
        reference = np.frombuffer(stream.readframes(stream.getnframes()), dtype='<i2').astype(np.float32).reshape(-1, 2)/32768
    decoded = directory/'decoded-final-audio.f32le'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(film), '-map', '0:a:0',
                    '-f', 'f32le', '-acodec', 'pcm_f32le', str(decoded)], check=True, timeout=120)
    samples = np.fromfile(decoded, dtype='<f4').reshape(-1, 2)
    expected = len(reference)
    if not expected <= len(samples) < expected+1024 or not np.isfinite(samples).all():
        raise ValueError('Unexpected AAC padding, truncated audio or invalid sample')
    correlation = float(np.corrcoef(reference.ravel(), samples[:expected].ravel())[0, 1])
    if correlation < .999:
        raise ValueError('Delivered AAC no longer matches the bound soundtrack')
    intervals = []
    for start in range(0, 205, 4):
        block = samples[start*48000:min((start+4)*48000, expected)]
        intervals.append({'startSeconds':start, 'peak':round(float(np.max(np.abs(block))), 6),
                          'rms':round(float(np.sqrt(np.mean(block**2))), 6)})
    result = {'schemaVersion':'vivhite-final-audio-comparison-1', 'filmSha256':sha(film),
              'soundtrackSha256':sha(soundtrack), 'expectedSamplesPerChannel':expected,
              'decodedAacSamplesPerChannel':len(samples),
              'decodedPcmCorrelationWithBoundProceduralWav':correlation,
              'allFourSecondIntervalsAnalysed':intervals, 'modelAudioInMix':False,
              'humanListening':False,
              'method':'Complete AAC decode and numerical comparison to the exact bound procedural WAV; no claim of human listening.'}
    (directory/'final-audio-comparison.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('205-second complete AAC/WAV correlation:', correlation)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    inspect(parser.parse_args().directory)
