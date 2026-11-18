"""Windows sharing collisions must not corrupt or strand video task journals.

GPL-3.0-only.
"""
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).parents[1]))
import local_video_pipeline as worker


def denied():
    error = PermissionError('simulated Windows sharing collision')
    error.winerror = 5
    return error


class AtomicVideoStateTest(unittest.TestCase):
    def test_retries_replacement_without_overwriting_another_journal(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)/'S04.json'
            worker.save(target,{'status':'in_progress','jobId':'existing'})
            legacy = target.with_name(target.name+'.partial')
            legacy.write_text('retained previous failure',encoding='utf-8')
            original = Path.replace
            calls = []
            def replace(source,destination):
                calls.append(source)
                if len(calls) == 1:
                    raise denied()
                return original(source,destination)
            with patch.object(Path,'replace',replace), patch.object(worker.time,'sleep'):
                worker.save(target,{'status':'completed','jobId':'existing'})
            self.assertEqual(len(calls),2)
            self.assertEqual(worker.read(target)['jobId'],'existing')
            self.assertEqual(worker.read(target)['status'],'completed')
            self.assertEqual(legacy.read_text(encoding='utf-8'),'retained previous failure')
            self.assertFalse(calls[-1].exists())

    def test_permanent_denial_is_bounded_and_preserves_old_and_new_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)/'S04.json'
            worker.save(target,{'status':'in_progress'})
            with patch.object(Path,'replace',side_effect=denied()) as replace, \
                    patch.object(worker.time,'sleep') as sleep:
                with self.assertRaises(PermissionError):
                    worker.save(target,{'status':'completed'})
            self.assertEqual(replace.call_count,10)
            self.assertEqual(sleep.call_count,9)
            self.assertEqual(worker.read(target)['status'],'in_progress')
            journals = list(Path(temporary).glob('*.partial'))
            self.assertEqual(len(journals),1)
            self.assertEqual(worker.read(journals[0])['status'],'completed')

    @unittest.skipUnless(os.name == 'nt','Actual Windows file sharing semantics')
    def test_real_open_reader_releases_and_atomic_replace_recovers(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)/'S04.json'
            worker.save(target,{'status':'in_progress','jobId':'same'})
            reader = target.open('rb')
            def release():
                time.sleep(0.2)
                reader.close()
            thread = threading.Thread(target=release)
            collisions = []
            original = Path.replace
            def replace(source,destination):
                try:
                    return original(source,destination)
                except OSError as error:
                    collisions.append(getattr(error,'winerror',None))
                    raise
            thread.start()
            try:
                with patch.object(Path,'replace',replace):
                    worker.save(target,{'status':'completed','jobId':'same'})
            finally:
                thread.join()
                reader.close()
            self.assertEqual(worker.read(target),{'status':'completed','jobId':'same'})
            self.assertEqual(list(Path(temporary).glob('*.partial')),[])
            self.assertTrue(set(collisions).intersection((5,32,33)),collisions)


if __name__ == '__main__':
    unittest.main()
