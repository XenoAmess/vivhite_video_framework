"""Check an art short's review, stage its character art, and render a silent MP4."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from fractions import Fraction
from pathlib import Path, PurePosixPath
from zipfile import ZipFile


REPO = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def stage_model(archive, model_name, output):
    with ZipFile(archive) as source:
        [model_member] = [
            name for name in source.namelist() if PurePosixPath(name).name == model_name
        ]
        bundle = PurePosixPath(model_member).parent
        settings_bytes = source.read(model_member)
        settings = json.loads(settings_bytes)
        references = settings["FileReferences"]
        files = {
            *references["Textures"],
            *(references[key] for key in ("Moc", "Physics", "UserData", "DisplayInfo") if key in references),
        }
        output.mkdir()
        for file in sorted(files):
            destination = (output / file).resolve()
            if not destination.is_relative_to(output) or ":" in file or "\\" in file:
                raise ValueError(f"Invalid model reference: {file}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            with source.open(str(bundle / file)) as reader, destination.open("xb") as writer:
                shutil.copyfileobj(reader, writer)
        (output / model_name).write_bytes(settings_bytes)


def run(args, timeout):
    subprocess.run(args, check=True, timeout=timeout)


def validate_media(path, plan):
    result = subprocess.check_output([
        "ffprobe", "-v", "error", "-count_frames", "-show_streams", "-of", "json", str(path),
    ], timeout=60)
    [stream] = json.loads(result)["streams"]
    if (stream["codec_name"] != "h264" or stream["pix_fmt"] != "yuv420p"
            or (stream["width"], stream["height"]) != (plan["width"], plan["height"])
            or Fraction(stream["avg_frame_rate"]) != plan["fps"]
            or int(stream["nb_read_frames"]) != plan["frameCount"]
            or Fraction(stream["duration"]) != Fraction(plan["frameCount"], plan["fps"])):
        raise ValueError("Rendered video does not match the delivery plan.")
    run(["ffmpeg", "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"], 60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("episode", "runtime", "chrome", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--plan", type=Path, help="Defaults to the episode's original production-plan.json")
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--archive", type=Path, help="Original Live2D asset archive")
    sources.add_argument("--portrait", type=Path, help="Transparent PNG for illustrated motion")
    args = parser.parse_args()
    episode, runtime, chrome, output = (
        path.resolve() for path in (args.episode, args.runtime, args.chrome, args.output)
    )
    source_plan = args.plan or episode.parent / "production-plan.json"
    output.mkdir(parents=True)
    inputs = output / "inputs"
    inputs.mkdir()
    plan_path = Path(shutil.copyfile(source_plan, inputs / "production-plan.json"))
    artwork = Path(shutil.copyfile(source_plan.with_name("artwork.js"), inputs / "artwork.js"))
    plan = json.loads(plan_path.read_bytes())
    live2d = plan["schemaVersion"] == "vivhite-live2d-art-1"
    if live2d and args.archive:
        asset = Path(shutil.copyfile(args.archive, inputs / "model.zip"))
        if sha256(asset) != plan["modelArchiveSha256"]:
            raise ValueError("Live2D archive hash does not match the production plan.")
        if sha256(runtime / "live2dcubismcore.min.js") != plan["coreSha256"]:
            raise ValueError("Cubism Core hash does not match the production plan.")
    elif plan["schemaVersion"] == "vivhite-illustrated-art-1" and args.portrait:
        asset = Path(shutil.copyfile(args.portrait, inputs / "portrait.png"))
        if sha256(asset) != plan["portraitSha256"]:
            raise ValueError("Portrait hash does not match the production plan.")
    else:
        raise ValueError("Choose --archive for a Live2D plan or --portrait for an illustrated plan.")
    run([
        sys.executable, str(REPO / "scripts/character_review.py"), "check",
        "--episode", str(episode), "--document", str(plan_path),
        "--asset", str(asset), "--asset", str(artwork),
    ], 60)
    model = output / "model" if live2d else inputs
    if live2d:
        stage_model(asset, plan["model"], model)
    frames = output / "frames"
    run([
        "node", str(TOOLS / "render_live2d_frames.cjs"), str(runtime), str(inputs),
        str(model), str(frames), str(chrome), "frames",
    ], 900)
    candidate = output / "afterimage.part.mp4"
    run([
        "ffmpeg", "-v", "error", "-xerror", "-framerate", str(plan["fps"]), "-i",
        str(frames / "frame-%04d.png"), "-an", "-c:v", "libx264", "-crf", "16", "-preset", "slow",
        "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p,setsar=1",
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
        "-movflags", "+faststart", str(candidate),
    ], 600)
    validate_media(candidate, plan)
    delivered = candidate.rename(output / "afterimage.mp4")
    print(f"{delivered} | SHA-256 {sha256(delivered)}")


if __name__ == "__main__":
    main()
