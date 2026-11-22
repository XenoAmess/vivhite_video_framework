"""Draft checkpoints bind actual first-frame images, not UHD video inputs. GPL-3.0-only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))
import durable_video_controller as worker


@unittest.skipUnless(os.name == 'nt' and shutil.which('git'), 'Windows checkpoint fixture')
class DurableDraftCheckpointTest(unittest.TestCase):
    def test_draft_dimensions_image_binding_and_changed_reference_rejection(self):
        with tempfile.TemporaryDirectory(prefix='whale-draft-checkpoint-') as temporary:
            base = Path(temporary)
            root, directory, remote = base/'checkout', base/'run', base/'origin.git'
            root.mkdir()
            (directory/'logs').mkdir(parents=True)
            def git(*args):
                return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.STDOUT)
            git('init', '-b', 'main')
            git('config', 'user.name', 'Unit Fixture')
            git('config', 'user.email', 'fixture@example.invalid')
            git('config', 'core.autocrlf', 'false')
            git('init', '--bare', str(remote))
            git('remote', 'add', 'origin', str(remote))
            (root/'baseline.txt').write_text('unit fixture', encoding='utf-8')
            git('add', '--', 'baseline.txt')
            git('commit', '-m', 'unit baseline')
            git('push', '-u', 'origin', 'main')
            episode = root/'episode'
            evidence = episode/'assets/generated/draft/review'
            evidence.mkdir(parents=True)
            picture = episode/'assets/generated/first-frame.fixture'
            picture.write_bytes(b'unit reference; not production artwork')
            expected = worker.sha(picture)
            frame = evidence/'full-source.fixture'
            frame.write_bytes(b'unit evidence; no real approval')
            plan = episode/'plan.json'
            plan.write_text(json.dumps({'stage':'draft', 'width':1344, 'height':768,
                'shots':[{'id':'S01', 'references':['assets/generated/first-frame.fixture'],
                          'referenceSha256':[expected]}]}), encoding='utf-8')
            report = directory/'clip-inspection/S01.json'
            report.parent.mkdir()
            report.write_text(json.dumps({'status':'decoded', 'identity':{'sourceSha256':'unit-source'},
                'decodedFrames':120, 'temporalEvidence':{'path':str(frame), 'sha256':worker.sha(frame)},
                'faceEvidence':None, 'allUsedFrameEvidence':[]}), encoding='utf-8')
            jobs = [{'shotId':'S01', 'status':'completed', 'sourceSha256':'unit-source',
                     'rawSha256':'unit-raw', 'requestSha256':'unit-request', 'jobId':'unit-job'}]
            config = {'root':str(root), 'directory':str(directory), 'episode':str(episode/'episode.json'),
                      'plan':str(plan), 'planSha256':worker.sha(plan),
                      'evidenceRelativeToEpisode':'assets/generated/draft/review',
                      'sourceCatalogRelativeToEpisode':'production/draft-sources.json'}
            worker.checkpoint_sources(config, jobs)
            catalog = json.loads((episode/'production/draft-sources.json').read_text(encoding='utf-8'))
            self.assertEqual(catalog['schemaVersion'], 'vivhite-native-768p-source-catalog-1')
            row = catalog['sources'][0]
            self.assertEqual((row['width'], row['height']), (1344, 768))
            self.assertEqual(row['imageReferences'][0]['sha256'], expected)
            self.assertNotIn('inputSourceSha256', row)
            self.assertEqual(git('rev-parse', 'HEAD'), git('rev-parse', 'origin/main'))
            picture.write_bytes(b'changed reference')
            with self.assertRaisesRegex(ValueError, 'Draft reference changed'):
                worker.checkpoint_sources(config, jobs)


if __name__ == '__main__':
    unittest.main()
