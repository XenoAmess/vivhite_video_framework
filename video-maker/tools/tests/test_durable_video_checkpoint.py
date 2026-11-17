"""Check background Git scope and recovery in isolated local fixture repositories.

No network, project media or production approvals. GPL-3.0-only.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).parents[1]))
import durable_video_controller as worker


@unittest.skipUnless(os.name == 'nt' and shutil.which('git'),'Windows background checkpoint fixture')
class DurableCheckpointTest(unittest.TestCase):
    def test_staged_unrelated_work_is_preserved_and_post_commit_crash_is_idempotent(self):
        with tempfile.TemporaryDirectory(prefix='vivhite-checkpoint-test-') as temporary:
            base = Path(temporary)
            root, directory, remote = base/'checkout',base/'run',base/'origin.git'
            root.mkdir();directory.mkdir()
            (directory/'logs').mkdir()
            def git(*arguments):
                return subprocess.check_output(['git',*arguments],cwd=root,stderr=subprocess.STDOUT).decode('utf-8')
            git('init','-b','main');git('config','user.name','Unit Fixture');git('config','user.email','fixture@example.invalid')
            git('config','core.autocrlf','false');git('init','--bare',str(remote));git('remote','add','origin',str(remote))
            (root/'user.txt').write_text('before',encoding='utf-8')
            git('add','--','user.txt');git('commit','-m','unit baseline');git('push','-u','origin','main')
            initial = git('rev-parse','HEAD').strip()
            episode = root/'episode'
            evidence = episode/'assets/generated/production-v11-native-4k-001/review/video-4k'
            evidence.mkdir(parents=True)
            fixture = evidence/'S01-unit-evidence.fixture'
            fixture.write_bytes(b'Unit evidence bytes; no production or semantic review')
            plan = episode/'plan.json'
            plan.write_text(json.dumps({'shots':[{'id':'S01','inputSourceSha256':'unit-input'}]}),encoding='utf-8')
            report_file = directory/'clip-inspection/S01.json'
            report_file.parent.mkdir()
            report_file.write_text(json.dumps({'status':'decoded','identity':{'sourceSha256':'unit-source'},
                'decodedFrames':120,'temporalEvidence':{'path':str(fixture),'sha256':worker.sha(fixture)},
                'faceEvidence':None,'allUsedFrameEvidence':[]}),encoding='utf-8')
            jobs = [{'shotId':'S01','status':'completed','sourceSha256':'unit-source','rawSha256':'unit-raw',
                     'requestSha256':'unit-request','jobId':'unit-job'}]
            config = {'root':str(root),'directory':str(directory),'episode':str(episode/'episode.json'),
                      'plan':str(plan),'planSha256':worker.sha(plan)}
            (root/'user.txt').write_text('unrelated pending edit',encoding='utf-8')
            git('add','--','user.txt')
            worker.checkpoint_sources(config,jobs)
            self.assertEqual(git('rev-parse','HEAD').strip(),initial)
            self.assertEqual(git('diff','--cached','--name-only').strip(),'user.txt')
            git('restore','--staged','--','user.txt')
            worker.checkpoint_sources(config,jobs)
            actual = git('rev-parse','HEAD').strip()
            self.assertNotEqual(actual,initial)
            self.assertNotIn('user.txt',git('show','--format=','--name-only','HEAD'))
            self.assertEqual((root/'user.txt').read_text(encoding='utf-8'),'unrelated pending edit')
            self.assertEqual(git('rev-parse','origin/main').strip(),actual)
            # Simulate a crash after the commit but before its local ledger was saved.
            (directory/'git-checkpoint.json').unlink()
            worker.checkpoint_sources(config,jobs)
            self.assertEqual(git('rev-parse','HEAD').strip(),actual)
            ledger = json.loads((directory/'git-checkpoint.json').read_text(encoding='utf-8'))
            self.assertTrue(ledger['pushed'])


if __name__ == '__main__':
    unittest.main()
