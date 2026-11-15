"""Decode every source frame, collect motion/cut/face candidates and temporal evidence.

Face candidates are neither a face-free certificate nor a semantic verdict.
Uses the separately installed OpenCV/NumPy/Pillow review environment. GPL-3.0-only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect(source, shot, evidence, output, face_model):
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    source = Path(source)
    digest = fingerprint(source)
    identity = {"sourceSha256":digest, "usedSeconds":shot["seconds"], "workerSha256":fingerprint(__file__),
                "faceModelSha256":fingerprint(face_model), "faceScoreThreshold":.6}
    report_file = output/f"{shot['id']}.json"
    if report_file.exists():
        cached = json.loads(report_file.read_text(encoding="utf-8"))
        if cached.get("identity") == identity and cached.get("status") == "decoded":
            return cached
    cap = cv2.VideoCapture(str(source))
    if not cap.isOpened():
        raise ValueError(f"Cannot decode {source.name}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    count = 0
    previous = None
    metrics, faces, samples, crops, all_used_frames = [], [], [], [], []
    detector = cv2.FaceDetectorYN.create(str(face_model), "", (832,480), .6, .3, 5000)
    cv2.setNumThreads(2)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    evidence.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    last_used = None
    next_sample = 0
    next_face_image = 0
    started = time.monotonic()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            moment = count/fps
            count += 1
            # Analyse every decoded frame, including the small unused model tail.
            small = cv2.resize(frame, (416,240))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            difference = 0 if previous is None else float(np.mean(cv2.absdiff(gray,previous)))
            previous = gray
            detector.setInputSize((frame.shape[1],frame.shape[0]))
            _, detected = detector.detect(frame)
            boxes = []
            if detected is not None:
                for face in detected:
                    x,y,w,h = face[:4]
                    boxes.append({"x":int(x),"y":int(y),"width":int(w),"height":int(h),
                                  "score":round(float(face[-1]),5),"classifier":"YuNet-2023mar"})
            used = moment < shot["seconds"]-1e-5
            metrics.append({"frame":count-1,"timeSeconds":round(moment,5),"used":used,
                            "meanDifference":round(difference,4),"cutCandidate":difference>18,
                            "faceCandidates":boxes})
            if boxes:
                faces.append({"frame":count-1,"timeSeconds":moment,"used":used,"boxes":boxes})
                if used and moment >= next_face_image:
                    for box in boxes:
                        x,y,w,h = (box[k] for k in ("x","y","width","height"))
                        margin = round(w*.4)
                        area = frame[max(0,y-margin):min(frame.shape[0],y+h+margin),
                                     max(0,x-margin):min(frame.shape[1],x+w+margin)]
                        crops.append((Image.fromarray(cv2.cvtColor(area,cv2.COLOR_BGR2RGB)),f"f{count-1} {moment:.2f}s"))
                    next_face_image = moment+.5
            if used:
                last_used = (Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)),f"f{count-1} {moment:.2f}s")
                all_used_frames.append((last_used[0].resize((416,240)),last_used[1]))
                if moment+1e-5 >= next_sample or difference>18:
                    samples.append(last_used)
                    next_sample = moment+.5
    finally:
        cap.release()
    if count < math.ceil(shot["seconds"]*fps) or last_used is None:
        raise ValueError("Source does not cover the entire used shot")
    if not samples or samples[-1][1] != last_used[1]:
        samples.append(last_used)

    def sheet(items, name, cell=(416,268), columns=3):
        if not items:
            return None
        canvas = Image.new("RGB",(columns*cell[0],math.ceil(len(items)/columns)*cell[1]),"#242424")
        draw = ImageDraw.Draw(canvas)
        for i,(picture,label) in enumerate(items):
            x,y = i%columns*cell[0],i//columns*cell[1]
            picture.thumbnail((cell[0],cell[1]-28))
            canvas.paste(picture,(x+(cell[0]-picture.width)//2,y+28))
            draw.text((x+5,y+4),f"{shot['id']} | {label}",font=font,fill="white")
        destination = evidence/f"{shot['id']}-{digest[:10]}-{name}.png"
        if not destination.exists():
            canvas.save(destination)
        return {"path":str(destination),"sha256":fingerprint(destination),"items":len(items)}

    contact = sheet(samples,"temporal")
    candidate_sheet = sheet(crops,"face-candidates",cell=(208,236),columns=5)
    all_frame_sheets = [sheet(all_used_frames[offset:offset+32], f"all-frames-{offset//32+1:02}",columns=4)
                        for offset in range(0,len(all_used_frames),32)]
    result = {"schemaVersion":"vivhite-reference-clip-inspection-1","status":"decoded","shotId":shot["id"],
              "identity":identity,"sourceFps":fps,"decodedFrames":count,
              "usedFramesAnalysed":sum(m["used"] for m in metrics),
              "meanMotion":round(float(np.mean([m["meanDifference"] for m in metrics[1:]])),5),
              "cutCandidateFrames":[m["frame"] for m in metrics if m["used"] and m["cutCandidate"]],
              "faceCandidateFrames":faces,"temporalEvidence":contact,"faceEvidence":candidate_sheet,
              "allUsedFrameEvidence":all_frame_sheets,
              "faceRecognitionLimit":"YuNet candidates on all decoded frames; printed/anime faces and false positives require semantic review; missed faces remain possible.",
              "semanticReview":"not_automatically_decided","humanFullPlayback":False,
              "elapsedSeconds":round(time.monotonic()-started,3)}
    (output/f"{shot['id']}-frame-metrics.jsonl").write_text(''.join(json.dumps(m)+"\n" for m in metrics),encoding="utf-8")
    report_file.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"{shot['id']}: {count} frames; motion {result['meanMotion']}; {len(faces)} face-candidate frames",flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan",type=Path,required=True)
    parser.add_argument("--directory",type=Path,required=True)
    parser.add_argument("--evidence",type=Path,required=True)
    parser.add_argument("--face-model",type=Path,required=True)
    parser.add_argument("--watch",action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    results = {}
    deadline = time.monotonic()+8*60*60
    while True:
        selections_file = args.directory/"source-selections.json"
        selections = json.loads(selections_file.read_text(encoding="utf-8"))["selections"] if selections_file.exists() else {}
        for shot in plan["shots"]:
            selected = selections.get(shot["id"])
            source = args.directory/selected["path"] if selected else args.directory/"sources"/f"{shot['id']}.mp4"
            if selected and (not source.resolve().is_relative_to(args.directory.resolve())
                             or fingerprint(source) != selected["sha256"]):
                raise ValueError("Selected corrected source escaped the run or changed")
            if source.exists():
                results[shot["id"]]=inspect(source,shot,args.evidence,args.directory/"clip-inspection",args.face_model)
        if len(results)==len(plan["shots"]) or not args.watch:
            break
        if time.monotonic()>deadline:
            raise TimeoutError("Review watcher timed out; existing evidence retained")
        time.sleep(5)
    summary={"schemaVersion":"vivhite-reference-inspection-summary-1","shots":list(results.values()),
             "expectedShots":len(plan["shots"]),"decodedFrames":sum(r["decodedFrames"] for r in results.values()),
             "semanticReview":"not_automatically_decided","humanFullPlayback":False}
    (args.directory/"clip-inspection-summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
