"""Protect the single opening-shot revision against unrelated changes."""
import copy
import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).parents[3]/'series/vivhite/autumn-journey/episodes/01-autumn-journey/production/materialize-sources-v10.py'
spec=importlib.util.spec_from_file_location('v10_locked_materializer',SCRIPT)
worker=importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


class V10TimingTest(unittest.TestCase):
    def test_locks_all_timings_other_sources_and_titles(self):
        plan=worker.worker.read(worker.PLAN_FILE)
        baseline=worker.worker.read(worker.previous.PLAN_FILE)
        worker.validate_locked_timing(plan,baseline)
        for index in range(48):
            for key in ('seconds','startFrame','sourceSeconds'):
                with self.subTest(shot=plan['shots'][index]['id'],key=key):
                    changed=copy.deepcopy(plan)
                    changed['shots'][index][key]+=1
                    with self.assertRaises(ValueError):worker.validate_locked_timing(changed,baseline)
            if index:
                changed=copy.deepcopy(plan)
                changed['shots'][index]['prompt']+=' changed'
                with self.assertRaisesRegex(ValueError,'Only S01'):
                    worker.validate_locked_timing(changed,baseline)
        changed=copy.deepcopy(plan)
        changed['titleOverlays'][0]['text']+=' changed'
        with self.assertRaisesRegex(ValueError,'titles unchanged'):
            worker.validate_locked_timing(changed,baseline)


if __name__=='__main__':unittest.main()
