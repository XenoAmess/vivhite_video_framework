"""Protect the two-shot revision against other timing or source changes."""
import copy
import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).parents[3]/'series/vivhite/autumn-journey/episodes/01-autumn-journey/production/materialize-sources-v9.py'
spec=importlib.util.spec_from_file_location('v9_locked_materializer',SCRIPT)
worker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class V9TimingTest(unittest.TestCase):
    def test_rejects_any_duration_or_reused_source_change(self):
        plan=worker.previous.worker.read(worker.PLAN_FILE)
        baseline=worker.previous.worker.read(worker.previous.PLAN_FILE)
        worker.validate_locked_timing(plan,baseline)
        for index in range(48):
            with self.subTest(shot=plan['shots'][index]['id']):
                changed=copy.deepcopy(plan)
                changed['shots'][index]['seconds']+=1
                with self.assertRaises(ValueError):worker.validate_locked_timing(changed,baseline)
        for index in range(48):
            if plan['shots'][index]['id'] in ('S44','S47'):continue
            with self.subTest(source=plan['shots'][index]['id']):
                changed=copy.deepcopy(plan)
                changed['shots'][index]['prompt']+=' changed'
                with self.assertRaisesRegex(ValueError,'Only S44 and S47'):
                    worker.validate_locked_timing(changed,baseline)


if __name__=='__main__':unittest.main()
