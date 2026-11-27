"""Check the art short's review, stage its Live2D inputs, and render a silent MP4."""

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
    for name in ("episode", "archive", "runtime", "chrome", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    episode, archive, runtime, chrome, output = (
        path.resolve() for path in (args.episode, args.archive, args.runtime, args.chrome, args.output)
    )
    output.mkdir(parents=True)
    inputs = output / "inputs"
    inputs.mkdir()
    plan_path = Path(shutil.copyfile(episode.parent / "production-plan.json", inputs / "production-plan.json"))
    artwork = Path(shutil.copyfile(episode.parent / "artwork.js", inputs / "artwork.js"))
    archive = Path(shutil.copyfile(archive, inputs / "model.zip"))
    plan = json.loads(plan_path.read_bytes())
    if plan["schemaVersion"] != "vivhite-live2d-art-1":
        raise ValueError("Unsupported art short production plan.")
    if sha256(archive) != plan["modelArchiveSha256"]:
        raise ValueError("Delta archive hash does not match the production plan.")
    if sha256(runtime / "live2dcubismcore.min.js") != plan["coreSha256"]:
        raise ValueError("Cubism Core hash does not match the production plan.")
    run([
        sys.executable, str(REPO / "scripts/character_review.py"), "check",
        "--episode", str(episode), "--document", str(plan_path),
        "--asset", str(archive), "--asset", str(artwork),
    ], 60)
    model = output / "model"
    stage_model(archive, plan["model"], model)
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
