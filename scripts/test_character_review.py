"""Meaningful boundary checks for version binding and private evidence exclusion."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import character_review as workflow


class CharacterReviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="vivhite-review-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.public = self.base / "video"
        self.private = self.base / "characters"
        self.episode = self.public / "series/math-education/inversion-count/episodes/02-rectangle-proof/episode.json"
        self.episode.parent.mkdir(parents=True)
        self.document = self.episode.parent / "director.md"
        self.document.write_text("A complete original script.\n", encoding="utf-8", newline="\n")
        self.save(self.episode, {"schemaVersion": "vivhite-episode-1", "series": "math-education",
                              "topic": "inversion-count", "id": "02-rectangle-proof",
                              "cast": ["vivhite"], "director": "director.md"})
        self.persona = self.private / "characters/vivhite/persona.md"
        self.persona.parent.mkdir(parents=True)
        self.persona.write_text("Complete persona\nPRIVATE_BACKGROUND_MARKER\n", encoding="utf-8", newline="\n")
        self.save(self.private / "characters.json", {"schemaVersion": "vivhite-character-registry-1",
                  "visibility": "private", "characters": [{"id": "vivhite", "personaFile": "characters/vivhite/persona.md"}]})
        self.git("init", "-b", "main")
        self.git("add", "--", "characters.json", "characters/vivhite/persona.md")
        self.git("-c", "user.name=Workflow Test", "-c", "user.email=test@example.invalid", "commit", "-m", "test persona")

    @staticmethod
    def save(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value) + "\n", encoding="utf-8", newline="\n")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.private), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15).stdout

    def context(self):
        return workflow.load_context(self.episode, self.private, public_root=self.public)

    def approve(self, context):
        bindings = [{key: item[key] for key in ("id", "personaSha256", "characterRepoRevision")}
                    for item in context["characters"]]
        record = {"schemaVersion": "vivhite-character-review-1", "reviewId": context["reviewId"],
                  "documentSha256": context["documentSha256"], "characters": bindings,
                  "assets": context["assets"],
                  "method": "assistant-semantic-review", "coverage": {"allScenes": True},
                  "personalityConsistency": "passed", "informationDisclosure": "passed",
                  "findings": [{"scene": "all", "evidence": "PRIVATE_FINDING_MARKER"}],
                  "arbitraryExtraPrivateField": "DO_NOT_EXPORT"}
        target = self.private / "reviews" / (context["reviewId"] + ".json")
        self.save(target, record)
        return target, record

    def test_receipt_whitelist_never_exports_persona_or_findings(self):
        context = self.context()
        self.approve(context)
        receipt = workflow.receipt_for(context)
        encoded = json.dumps(receipt)
        self.assertNotIn("PRIVATE_", encoded)
        self.assertNotIn("DO_NOT_EXPORT", encoded)
        self.assertNotIn(str(self.private), encoded)
        self.save(workflow.receipt_path(context), receipt)
        self.assertEqual(workflow.check(context), receipt)

    def test_missing_review_and_failed_review_block(self):
        context = self.context()
        with self.assertRaisesRegex(workflow.ReviewError, "Semantic review required"):
            workflow.receipt_for(context)
        path, record = self.approve(context)
        record["informationDisclosure"] = "failed"
        self.save(path, record)
        with self.assertRaisesRegex(workflow.ReviewError, "informationDisclosure"):
            workflow.receipt_for(context)

    def test_document_change_cannot_reuse_approval(self):
        first = self.context()
        self.approve(first)
        self.document.write_text("A changed final subtitle.\n", encoding="utf-8")
        second = self.context()
        self.assertNotEqual(first["documentSha256"], second["documentSha256"])
        with self.assertRaises(workflow.ReviewError):
            workflow.receipt_for(second)

    def test_changed_persona_requires_commit_and_new_semantic_review(self):
        first = self.context()
        path, record = self.approve(first)
        self.persona.write_text("Changed complete persona\n", encoding="utf-8", newline="\n")
        with self.assertRaisesRegex(workflow.ReviewError, "Commit the complete persona"):
            self.context()
        self.git("add", "--", "characters/vivhite/persona.md")
        self.git("-c", "user.name=Workflow Test", "-c", "user.email=test@example.invalid", "commit", "-m", "update persona")
        with self.assertRaisesRegex(workflow.ReviewError, "persona changed"):
            workflow.receipt_for(self.context())
        self.assertEqual(path.read_text(encoding="utf-8"), json.dumps(record) + "\n")

    def test_review_only_commit_does_not_invalidate_identical_persona(self):
        first = self.context()
        self.approve(first)
        self.git("add", "--", "reviews")
        self.git("-c", "user.name=Workflow Test", "-c", "user.email=test@example.invalid", "commit", "-m", "review evidence")
        self.assertNotEqual(first["characters"][0]["characterRepoRevision"], self.context()["characters"][0]["characterRepoRevision"])
        workflow.receipt_for(self.context())

    def test_public_clone_path_and_registry_traversal_rejected(self):
        with self.assertRaisesRegex(workflow.ReviewError, "outside the public"):
            workflow.load_context(self.episode, self.public / "characters", public_root=self.public)
        self.save(self.private / "characters.json", {"schemaVersion": "vivhite-character-registry-1",
                  "visibility": "private", "characters": [{"id": "vivhite", "personaFile": "../outside.md"}]})
        with self.assertRaisesRegex(workflow.ReviewError, "inside its owning"):
            self.context()

    def test_sample_only_review_does_not_pass(self):
        context = self.context()
        path, record = self.approve(context)
        record["coverage"]["allScenes"] = False
        self.save(path, record)
        with self.assertRaisesRegex(workflow.ReviewError, "every scene"):
            workflow.receipt_for(context)

    def test_context_before_writing_and_review_requires_existing_document(self):
        self.document.unlink()
        context = workflow.load_context(self.episode, self.private, public_root=self.public, require_document=False)
        self.assertIsNone(context["documentSha256"])
        self.assertTrue(context["characters"][0]["personaSha256"])
        with self.assertRaisesRegex(workflow.ReviewError, "Write the complete document"):
            workflow.receipt_for(context)
        with self.assertRaisesRegex(workflow.ReviewError, "does not exist"):
            self.context()

    def test_replacing_external_presenter_invalidates_review(self):
        asset = self.base / "presenter.jpg"
        asset.write_bytes(b"first reviewed placeholder")
        first = workflow.load_context(self.episode, self.private, public_root=self.public, assets=[asset])
        self.approve(first)
        receipt = workflow.receipt_for(first)
        self.assertNotIn(str(asset), json.dumps(receipt))
        asset.write_bytes(b"changed picture or video with new visible content")
        second = workflow.load_context(self.episode, self.private, public_root=self.public, assets=[asset])
        self.assertEqual(first["documentSha256"], second["documentSha256"])
        with self.assertRaisesRegex(workflow.ReviewError, "asset changed"):
            workflow.receipt_for(second)


if __name__ == "__main__":
    unittest.main()
