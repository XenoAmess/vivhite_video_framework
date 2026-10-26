"""Bind semantic review to a complete external persona and exact document bytes.

No semantic decisions are made by this program. Private findings never enter receipts.
GPL-3.0-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


REPO = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SHA = re.compile(r"[0-9a-f]{64}\Z")
METHODS = {"assistant-semantic-review", "human-semantic-review"}


class ReviewError(ValueError):
    pass


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (OSError, ValueError) as error:
        raise ReviewError("Required workflow JSON is missing or invalid") from error


def fingerprint(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_fingerprint(path: Path) -> str:
    try:
        with path.open("rb") as source:
            return hashlib.file_digest(source, "sha256").hexdigest()
    except OSError as error:
        raise ReviewError("A required review asset cannot be read") from error


def git(private_home: Path, *args: str) -> bytes:
    try:
        return subprocess.run(["git", "-C", str(private_home), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15).stdout
    except (OSError, subprocess.SubprocessError) as error:
        raise ReviewError("Cannot read the character repository revision") from error


def inside(base: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ReviewError("Missing relative file reference")
    candidate = (base / relative).resolve()
    if Path(relative).is_absolute() or not candidate.is_relative_to(base.resolve()):
        raise ReviewError("File reference must stay inside its owning directory")
    return candidate


def load_context(episode: Path, characters_home: Path | None = None,
                 document: Path | None = None, *, public_root: Path = REPO,
                 assets: list[Path] | None = None, require_document: bool = True) -> dict:
    episode = episode.resolve()
    root = public_root.resolve()
    if not episode.is_relative_to(root):
        raise ReviewError("Episode manifest must belong to the video project")
    manifest = read_json(episode)
    if manifest.get("schemaVersion") != "vivhite-episode-1":
        raise ReviewError("Unsupported episode manifest version")
    keys = ("series", "topic", "id")
    if any(not isinstance(manifest.get(key), str) or not SLUG.fullmatch(manifest[key]) for key in keys):
        raise ReviewError("Episode IDs must be stable lowercase slugs")
    cast = manifest.get("cast")
    if not isinstance(cast, list) or not cast or any(
            not isinstance(item, str) or not SLUG.fullmatch(item) for item in cast) or len(set(cast)) != len(cast):
        raise ReviewError("Declare unique character IDs in episode cast")
    private_home = (characters_home or Path(os.environ.get(
        "VIVHITE_CHARACTERS_HOME", str(root.parent / "vivhite_characters")))).resolve()
    if private_home.is_relative_to(root) or root.is_relative_to(private_home):
        raise ReviewError("The private character clone must be outside the public repository")
    registry = read_json(private_home / "characters.json")
    if registry.get("schemaVersion") != "vivhite-character-registry-1" or registry.get("visibility") != "private":
        raise ReviewError("Expected the separate private character registry")
    revision = git(private_home, "rev-parse", "HEAD").decode("ascii").strip()
    entries = registry.get("characters")
    if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
        raise ReviewError("Invalid character registry entries")
    characters = []
    for character_id in cast:
        matches = [entry for entry in entries if entry.get("id") == character_id]
        if len(matches) != 1:
            raise ReviewError(f"Missing or ambiguous complete persona for character {character_id}")
        path = inside(private_home, matches[0].get("personaFile"))
        try:
            data = path.read_bytes()
            if not data.decode("utf-8").strip():
                raise ValueError()
        except (OSError, ValueError) as error:
            raise ReviewError(f"Cannot read the complete persona for character {character_id}") from error
        relative = path.relative_to(private_home).as_posix()
        if git(private_home, "show", f"{revision}:{relative}") != data:
            raise ReviewError(f"Commit the complete persona before reviewing character {character_id}")
        characters.append({"id": character_id, "personaSha256": fingerprint(data),
                           "characterRepoRevision": revision, "personaFile": str(path)})
    document = (document.resolve() if document else inside(episode.parent, manifest.get("director")))
    document_sha = None
    try:
        document_sha = fingerprint(document.read_bytes())
    except FileNotFoundError as error:
        if require_document:
            raise ReviewError("The exact document to review does not exist") from error
    except OSError as error:
        raise ReviewError("Cannot read the exact document to review") from error
    asset_hashes = sorted({file_fingerprint(path) for path in assets or []})
    review_id = "/".join([*(manifest[key] for key in keys), document_sha]) if document_sha else None
    return {"schemaVersion": "vivhite-character-context-1", "episode": "/".join(manifest[key] for key in keys),
            "documentSha256": document_sha, "characters": characters, "reviewId": review_id,
            "assets": [{"sha256": sha} for sha in asset_hashes],
            "privateHome": str(private_home), "episodeDirectory": str(episode.parent)}


def receipt_for(context: dict) -> dict:
    if not context.get("documentSha256"):
        raise ReviewError("Write the complete document before recording semantic review")
    private_home = Path(context["privateHome"])
    review_path = inside(private_home, f"reviews/{context['reviewId']}.json")
    if not review_path.is_file():
        raise ReviewError(f"Semantic review required: reviews/{context['reviewId']}.json in the private character repository")
    review = read_json(review_path)
    if review.get("schemaVersion") != "vivhite-character-review-1" or review.get("reviewId") != context["reviewId"]:
        raise ReviewError("Private review does not match the current episode and document")
    if review.get("documentSha256") != context["documentSha256"]:
        raise ReviewError("Document changed; repeat both semantic reviews")
    if review.get("assets", []) != context["assets"]:
        raise ReviewError("Visible or audible asset changed; repeat both semantic reviews with actual assets")
    method = review.get("method")
    if method not in METHODS:
        raise ReviewError("Record the actual semantic review method")
    if not isinstance(review.get("coverage"), dict) or review["coverage"].get("allScenes") is not True:
        raise ReviewError("Review must cover every scene, not a sample")
    if not isinstance(review.get("findings"), list) or not review["findings"]:
        raise ReviewError("Record actual review evidence in the private repository")
    bindings = review.get("characters")
    if not isinstance(bindings, list) or len(bindings) != len(context["characters"]):
        raise ReviewError("Review must cover every cast member")
    safe_bindings = []
    for character in context["characters"]:
        matching = [binding for binding in bindings if isinstance(binding, dict) and binding.get("id") == character["id"]]
        if len(matching) != 1:
            raise ReviewError("Review cast bindings do not match")
        binding = matching[0]
        sha = binding.get("personaSha256")
        revision = binding.get("characterRepoRevision")
        if not isinstance(sha, str) or not SHA.fullmatch(sha) or sha != character["personaSha256"]:
            raise ReviewError("Complete persona changed; reread it and repeat both reviews")
        if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
            raise ReviewError("Review needs the exact character source revision")
        # A later review-only commit is allowed; the original source must contain identical persona bytes.
        path = Path(character["personaFile"]).relative_to(private_home).as_posix()
        if fingerprint(git(private_home, "show", f"{revision}:{path}")) != sha:
            raise ReviewError("Reviewed persona does not match its recorded Git revision")
        safe_bindings.append({"id": character["id"], "personaSha256": sha, "characterRepoRevision": revision})
    for field in ("personalityConsistency", "informationDisclosure"):
        if review.get(field) != "passed":
            raise ReviewError(f"Semantic review is not passed: {field}")
    return {"schemaVersion": "vivhite-character-review-receipt-1", "reviewId": context["reviewId"],
            "documentSha256": context["documentSha256"], "characters": safe_bindings,
            "assets": context["assets"],
            "method": method, "personalityConsistency": "passed", "informationDisclosure": "passed"}


def receipt_path(context: dict) -> Path:
    return Path(context["episodeDirectory"]) / "reviews" / f"{context['documentSha256']}.json"


def check(context: dict) -> dict:
    expected = receipt_for(context)
    if read_json(receipt_path(context)) != expected:
        raise ReviewError("Public receipt is missing or stale; export it after completing semantic review")
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("context", "receipt", "check"))
    parser.add_argument("--episode", type=Path, required=True)
    parser.add_argument("--characters-home", type=Path)
    parser.add_argument("--document", type=Path)
    parser.add_argument("--asset", action="append", type=Path, default=[],
                        help="Actual externally supplied visible/audible asset; repeat for multiple files")
    args = parser.parse_args()
    try:
        context = load_context(args.episode, args.characters_home, args.document,
                               assets=args.asset, require_document=args.command != "context")
        if args.command == "context":
            print(json.dumps(context, ensure_ascii=True, indent=2))
        elif args.command == "receipt":
            receipt = receipt_for(context)
            destination = receipt_path(context)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(json.dumps(receipt, ensure_ascii=True, indent=2) + "\n", encoding="utf-8", newline="\n")
            print("Exported version-bound character review receipt")
        else:
            check(context)
            print("Character review bindings passed (semantic decisions supplied by the reviewer)")
        return 0
    except ReviewError as error:
        print(f"Character review blocked: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
