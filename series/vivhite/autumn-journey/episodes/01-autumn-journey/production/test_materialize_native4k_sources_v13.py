"""Protect locked timing and prohibit substituting historical S20 instructions."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('import_v13_under_test',
    Path(__file__).with_name('materialize-native4k-sources-v13.py'))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class NativeImportV13Test(unittest.TestCase):
    def test_only_two_origins_change_and_all_timings_stay_fixed(self):
        plan = MODULE.build_plan()
        old = MODULE.worker.read(MODULE.previous.OLD_PLAN)
        self.assertEqual([(s['id'], s['seconds'], s['sourceSeconds'], s['startFrame']) for s in plan['shots']],
            [(s['id'], s['seconds'], s['sourceSeconds'], s['startFrame']) for s in old['shots']])
        changed = [s['id'] for s, original in zip(plan['shots'], old['shots']) if s != original]
        self.assertEqual(['S05', 'S20'], changed)
        self.assertEqual(6150, plan['totalFrames'])
        self.assertIn('v13-S20-full-sequence', MODULE.origins()['S20'][0])
        self.assertIn('v12-S05', MODULE.origins()['S05'][0])
        self.assertTrue(all('v11' in value[0] for key, value in MODULE.origins().items()
            if key not in ('S05', 'S20')))

    def test_old_s20_cannot_silently_replace_pending_rerun(self):
        plan = MODULE.build_plan()
        plan['shots'][19] = copy.deepcopy(MODULE.worker.read(MODULE.previous.OLD_PLAN)['shots'][19])
        with self.assertRaisesRegex(ValueError, 'new exact ten-second S20'):
            MODULE.validate_locked_layout(plan)

    def test_shortening_s46_is_rejected(self):
        plan = MODULE.build_plan()
        plan['shots'][45]['seconds'] = 4
        with self.assertRaises(ValueError):
            MODULE.validate_locked_layout(plan)

    def test_user_rejected_print_lighting_blocks_assembly(self):
        with patch.object(MODULE.worker, 'read', return_value={'status': 'open', 'finalAssemblyAllowed': False}):
            with self.assertRaisesRegex(ValueError, 'Print lighting review is unresolved'):
                MODULE.validate_lighting_hold()

    def test_changed_lighting_resolution_receipt_is_rejected(self):
        with patch.object(MODULE.worker, 'read', return_value={'status': 'resolved',
                'finalAssemblyAllowed': True, 'resolutionReceipt': 'production/test-only.json',
                'resolutionReceiptSha256': 'bound'}), patch.object(MODULE.worker, 'sha', return_value='changed'):
            with self.assertRaisesRegex(ValueError, 'resolution receipt changed'):
                MODULE.validate_lighting_hold()


if __name__ == '__main__':
    unittest.main()
