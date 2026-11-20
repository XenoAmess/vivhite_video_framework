"""Reject a non-full-sequence ending or wrong input before preparing a rerun."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


WORKER = Path(__file__).with_name('prepare-S20-full-sequence-v13.py')
SPEC = importlib.util.spec_from_file_location('prepare_s20_full_sequence', WORKER)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PreparationBoundaryTest(unittest.TestCase):
    def fixture(self, temporary, *, windows=1):
        base = Path(temporary)
        episode = base / 'episode'
        original = base / 'original'
        output = base / 'new-run'
        (episode / 'production').mkdir(parents=True)
        (original / 'sources').mkdir(parents=True)
        (original / 'input-sources').mkdir()
        # Use the real immutable source plan, not a second hand-written schema.
        source_plan = MODULE.EP / 'production-plan-v11-native-4k.json'
        (episode / source_plan.name).write_bytes(source_plan.read_bytes())
        ending = original / 'sources/S48.mp4'
        ending.write_bytes(b'unit-test-ending')
        (original / 'input-sources/S20.mp4').write_bytes(b'wrong-input')
        audit = {
            'decision': {'decision': 'accepted'},
            'wholeSceneFramesActuallyViewed': 336,
            'nativeButterflyFramesActuallyViewed': 336,
            'serverResult': {'temporal_strategy': 'full_sequence', 'windows': windows,
                             'independent_window_fallback': False},
            'sourceSha256': MODULE.sha(ending),
        }
        (episode / 'production/S48-full-sequence-source-review-v11-4k.json').write_text(
            json.dumps(audit), encoding='utf-8')
        return episode, original, output

    def test_multiple_windows_rejected_even_when_ending_marked_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            episode, original, output = self.fixture(temporary, windows=4)
            with patch.object(MODULE, 'EP', episode):
                with self.assertRaisesRegex(ValueError, 'full-sequence ending'):
                    MODULE.prepare(original, output)
            self.assertFalse(output.exists())
            self.assertFalse((episode / 'production-plan-v13-S20-full-sequence-native-4k-r1.json').exists())

    def test_wrong_input_is_rejected_before_any_new_run_or_plan(self):
        with tempfile.TemporaryDirectory() as temporary:
            episode, original, output = self.fixture(temporary)
            with patch.object(MODULE, 'EP', episode):
                with self.assertRaisesRegex(ValueError, 'original complete adopted768P'):
                    MODULE.prepare(original, output)
            self.assertFalse(output.exists())
            self.assertFalse((episode / 'production-plan-v13-S20-full-sequence-native-4k-r1.json').exists())


if __name__ == '__main__':
    unittest.main()
