"""Guard the user's explicit instruction to change only the closing duration."""
import copy
import importlib.util
from pathlib import Path
import re
import unittest

SCRIPT = (Path(__file__).parents[3] / 'series/vivhite/autumn-journey/episodes/'
          '01-autumn-journey/production/materialize-sources-v8.py')
SPEC = importlib.util.spec_from_file_location('v8_locked_source_materializer', SCRIPT)
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class LockedTimingTest(unittest.TestCase):
    def test_native_closing_choice_keeps_raw_origin_and_excludes_slowdown(self):
        plan = worker.worker.read(worker.PLAN_FILE)
        policy = worker.worker.read(worker.EP / 'production/workflow-policy.json')['closingGeneration']
        self.assertEqual(worker.ORIGINS['S48'], ('production-v8-motion-768p-S48-005',
                                                'production-plan-v8-S48-image-only-r5.json'))
        self.assertTrue(plan['shots'][-1]['nativeWingMotionAcceptedByUser'])
        self.assertFalse(plan['shots'][-1]['butterflySlowdownRequested'])
        self.assertFalse(policy['furtherClosingGenerationRequested'])
        self.assertFalse(policy['localTimingCandidates']['adopted'])
        self.assertEqual(policy['activeAttempt']['selectedSource'], 'sources/S48.mp4')

    def test_current_retry_uses_fourteen_source_seconds_and_preserves_failed_fifteen_second_history(self):
        plan = worker.worker.read(worker.PLAN_FILE)
        policy = worker.worker.read(worker.EP / 'production/workflow-policy.json')['closingGeneration']
        retry = worker.worker.read(worker.EP / policy['nextAttemptPlan'])
        self.assertEqual(policy['sourceSecondsFromNowOn'], 14)
        self.assertTrue(policy['fifteenSecondRuleSuperseded'])
        self.assertEqual(policy['supersededFifteenSecondPolicy']['lastAttempt']['sourceSeconds'], 15)
        self.assertEqual((plan['shots'][-1]['seconds'], plan['shots'][-1]['sourceSeconds']), (14, 14))
        self.assertEqual((retry['shots'][0]['seconds'], retry['shots'][0]['sourceSeconds']), (14, 14))
        self.assertEqual(retry['shots'][0]['prompt'], plan['shots'][-1]['prompt'])
        self.assertNotIn('fifteen', retry['shots'][0]['prompt'].lower())
        previous = worker.worker.read(worker.EP / 'production-plan-v8-bf16-768p-r2.json')
        self.assertEqual(plan['shots'][:-1], previous['shots'][:-1])

    def test_director_contains_one_complete_timeline_matching_the_locked_plan(self):
        plan = worker.worker.read(worker.PLAN_FILE)
        document = (worker.EP / 'director-v8.md').read_text(encoding='utf-8')
        rows = re.findall(r'^\| (S\d{2}) \| (\d{2}):(\d{2})-(\d{2}):(\d{2}) \| (\d+) \|',
                          document, re.MULTILINE)
        self.assertEqual(len(rows), 48)
        for row, shot in zip(rows, plan['shots']):
            identity, minute, second, end_minute, end_second, duration = row
            self.assertEqual(identity, shot['id'])
            self.assertEqual((int(minute)*60+int(second))*30, shot['startFrame'])
            self.assertEqual((int(end_minute)*60+int(end_second))*30,
                             shot['startFrame']+shot['seconds']*30)
            self.assertEqual(int(duration), shot['seconds'])

    def test_actual_first_47_timings_remain_unchanged_and_other_trims_are_rejected(self):
        baseline = worker.worker.read(worker.EP / 'production-plan-v7-bf16-768p.json')
        plan = worker.worker.read(worker.PLAN_FILE)
        worker.validate_locked_timing(plan, baseline)
        for index in range(47):
            changed = copy.deepcopy(plan)
            changed['shots'][index]['seconds'] -= 1
            with self.subTest(shot=changed['shots'][index]['id']), self.assertRaisesRegex(ValueError, 'Only S48'):
                worker.validate_locked_timing(changed, baseline)
        fallback = copy.deepcopy(plan)
        fallback['shots'][-1]['sourceSeconds'] = 15
        worker.validate_locked_timing(fallback, baseline)
        for field, value in [('seconds', 15), ('startFrame', 5700), ('sourceSeconds', 16)]:
            changed = copy.deepcopy(plan)
            changed['shots'][-1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                worker.validate_locked_timing(changed, baseline)


if __name__ == '__main__':
    unittest.main()
