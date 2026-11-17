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
    def test_director_contains_one_complete_timeline_matching_the_locked_plan(self):
        plan = worker.worker.read(worker.EP / 'production-plan-v8-bf16-768p.json')
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
        plan = worker.worker.read(worker.EP / 'production-plan-v8-bf16-768p.json')
        worker.validate_locked_timing(plan, baseline)
        for index in range(47):
            changed = copy.deepcopy(plan)
            changed['shots'][index]['seconds'] -= 1
            with self.subTest(shot=changed['shots'][index]['id']), self.assertRaisesRegex(ValueError, 'Only S48'):
                worker.validate_locked_timing(changed, baseline)
        for field, value in [('seconds', 15), ('startFrame', 5700), ('sourceSeconds', 15)]:
            changed = copy.deepcopy(plan)
            changed['shots'][-1][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                worker.validate_locked_timing(changed, baseline)


if __name__ == '__main__':
    unittest.main()
