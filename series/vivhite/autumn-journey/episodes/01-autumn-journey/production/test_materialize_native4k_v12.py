"""Lock the native4K repair import to unchanged positions and approved origins."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

FILE = Path(__file__).with_name('materialize-native4k-sources-v12.py')
SPEC = importlib.util.spec_from_file_location('native4k_v12_import_test', FILE)
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class Native4kImportTest(unittest.TestCase):
    def test_candidate_keeps_all_timing_and47_original_shots_without_editing_plans(self):
        before = [worker.worker.sha(path) for path in (worker.OLD_PLAN, worker.REPAIR_PLAN)]
        candidate = worker.build_plan()
        baseline = worker.worker.read(worker.OLD_PLAN)
        worker.validate_locked_layout(candidate)
        self.assertEqual(candidate['totalFrames'], 6150)
        for shot, old in zip(candidate['shots'], baseline['shots']):
            self.assertEqual((shot['seconds'], shot['startFrame'], shot['sourceSeconds']),
                             (old['seconds'], old['startFrame'], old['sourceSeconds']))
            if shot['id'] != 'S05':
                self.assertEqual(shot, old)
        self.assertEqual(before, [worker.worker.sha(path) for path in (worker.OLD_PLAN, worker.REPAIR_PLAN)])
        self.assertEqual(candidate['shots'][4]['inputSourceSha256'], worker.INPUT_SHA)

    def test_missing_saddle_input_or_altered_other_shot_cannot_be_imported(self):
        candidate = worker.build_plan()
        old = worker.worker.read(worker.OLD_PLAN)
        for identity in ('S05', 'S46', 'S48'):
            modified = copy.deepcopy(candidate)
            shot = next(item for item in modified['shots'] if item['id'] == identity)
            if identity == 'S05':
                modified['shots'][4] = old['shots'][4]
            elif identity == 'S46':
                shot['seconds'] = 4
            else:
                shot['prompt'] += ' Make the butterfly slower.'
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                worker.validate_locked_layout(modified)

    def test_title_format_and_person_constraints_cannot_change(self):
        candidate = worker.build_plan()
        for key, value in [('titleOverlays', []), ('sourceSize', '2560x1440'),
                           ('noAddedPeople', False), ('assemblyOnly', False)]:
            modified = copy.deepcopy(candidate)
            modified[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                worker.validate_locked_layout(modified)

    def test_all48_origins_are_explicit_and_s05_has_no_old_fallback(self):
        origins = worker.origins()
        self.assertEqual(len(origins), 48)
        self.assertEqual(origins['S05'][0], 'production-v12-S05-native-4k-001')
        self.assertTrue(all(value[0] == 'production-v11-native-4k-001'
                            for key, value in origins.items() if key != 'S05'))

    def test_missing_actual_sources_create_no_partial_assembly(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            plan_file = base / 'unapproved-test-candidate.json'
            plan_file.write_text(json.dumps(worker.build_plan()), encoding='utf-8')
            target = base / 'must-not-be-created'
            with self.assertRaises(FileNotFoundError):
                worker.materialize(base, target, plan_file)
            self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
