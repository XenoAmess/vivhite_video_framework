"""Save reference overviews and original-pixel face crops for visual review.

Detection assists navigation only and never decides whether eyes are open.
GPL-3.0-only.
"""
import hashlib
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    episode = Path(__file__).resolve().parents[1]
    destination = episode / 'assets/generated/production-v5-bf16-001/review/eye-reference-audit-001'
    destination.mkdir(parents=True, exist_ok=True)
    plan_file = episode / 'production-plan-v5-bf16-768p-r2.json'
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    entries = []
    for shot in plan['shots']:
        entries.append((shot['id'], episode / shot['references'][0]))
    masters = sorted({shot['designMaster'] for shot in plan['shots'] if shot.get('designMaster')})
    entries.extend((Path(path).stem, episode / path) for path in masters)
    detector = cv2.FaceDetectorYN.create(
        'D:/workspace/vivhite-analysis-output/models/opencv-yunet-2023mar/face_detection_yunet_2023mar.onnx',
        '', (320, 320), .35, .3, 5000)
    records, crops = [], []
    for page in range(0, len(entries), 6):
        sheet = Image.new('RGB', (1440, 1320), (28, 28, 28))
        draw = ImageDraw.Draw(sheet)
        for local, (identity, path) in enumerate(entries[page:page + 6]):
            source = Image.open(path).convert('RGB')
            thumbnail = source.copy()
            thumbnail.thumbnail((716, 404))
            x, y = (local % 2) * 720, (local // 2) * 440
            sheet.paste(thumbnail, (x, y + 32))
            draw.text((x + 5, y + 8), identity, fill='white')
            frame = cv2.imread(str(path))
            height, width = frame.shape[:2]
            detector.setInputSize((width, height))
            _, faces = detector.detect(frame)
            boxes = []
            for face in ([] if faces is None else faces):
                bx, by, bw, bh = [float(value) for value in face[:4]]
                left, top = max(0, int(bx - bw * .3)), max(0, int(by - bh * .3))
                right, bottom = min(width, int(bx + bw * 1.3)), min(height, int(by + bh * 1.3))
                crop = source.crop((left, top, right, bottom))
                crops.append((identity, crop))
                boxes.append({'box': [left, top, right, bottom], 'detectorScore': float(face[-1])})
            records.append({'id': identity, 'source': str(path.relative_to(episode)),
                            'sha256': digest(path), 'faceCandidates': boxes})
        target = destination / f'references-{page // 6 + 1:02}.png'
        if target.exists():
            raise FileExistsError('Keep existing evidence; use a new audit directory')
        sheet.save(target)
        sheet.save(target.with_suffix('.jpg'), quality=90)
    for page in range(0, len(crops), 24):
        sheet = Image.new('RGB', (1440, 1056), (28, 28, 28))
        draw = ImageDraw.Draw(sheet)
        for local, (identity, crop) in enumerate(crops[page:page + 24]):
            crop.thumbnail((232, 226))
            x, y = (local % 6) * 240, (local // 6) * 264
            sheet.paste(crop, (x, y + 30))
            draw.text((x + 3, y + 8), identity, fill='white')
        target = destination / f'face-candidates-{page // 24 + 1:02}.png'
        sheet.save(target)
        sheet.save(target.with_suffix('.jpg'), quality=92)
    (destination / 'reference-evidence.json').write_text(json.dumps({
        'sourcePlanSha256': digest(plan_file), 'workerSha256': digest(Path(__file__)),
        'records': records, 'candidateCount': len(crops),
        'semanticReview': 'pending; detection is not an eye-state judgement',
        'method': 'Original reference pixels only; scaled overviews and region crops, no creative changes.'
    }, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'referenceEntries': len(entries), 'faceCandidates': len(crops)}))


if __name__ == '__main__':
    main()
