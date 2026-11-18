"""Watch local source-ready events without querying or changing the server.

Fresh controller startup/retry states have bounded grace. Missing journals also
have a deadline. This tool never approves media or starts/cancels render jobs.
GPL-3.0-only.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time


class LocalSourceWatch:
    ACTIVE = {'watching-active-worker', 'reconciled-existing-worker'}
    TRANSIENT = {'started-generation', 'started-technical-preview',
                 'waiting-for-client-retry-backoff'}

    def __init__(self, directory, identity):
        if not re.fullmatch(r'S\d{2}', identity):
            raise ValueError('Use an explicit shot ID')
        self.directory = Path(directory)
        self.identity = identity
        self.unreadable_since = None
        self.transient_since = None

    @staticmethod
    def read(path):
        value = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('Local journal must be an object')
        return value

    def tick(self, utc_now, monotonic_now):
        try:
            controller = self.read(self.directory/'controller.json')
            age = (utc_now - datetime.fromisoformat(controller['snapshotAt'])).total_seconds()
            if age > 180 or age < -30:
                return {'event': 'attention', 'reason': 'controller-heartbeat-age',
                        'heartbeatAgeSeconds': round(age), 'shotId': self.identity}
            report_file = self.directory/'clip-inspection'/f'{self.identity}.json'
            job_file = self.directory/'jobs'/f'{self.identity}.json'
            if report_file.exists() and job_file.exists():
                report, job = self.read(report_file), self.read(job_file)
                # A finished controller may already have disabled its watchdog.
                # Check the matching complete source before terminal status.
                digest = job.get('sourceSha256')
                if (job.get('status') == 'completed' and report.get('status') == 'decoded'
                        and isinstance(digest, str) and re.fullmatch(r'[0-9a-f]{64}', digest)
                        and report.get('identity', {}).get('sourceSha256') == digest
                        and report.get('decodedFrames') == report.get('usedFramesAnalysed')
                        and report.get('decodedFrames') in (120, 240, 336)):
                    return {'event': 'source-ready', 'shotId': self.identity,
                            'jobId': job['jobId'], 'sourceSha256': digest,
                            'frames': report['usedFramesAnalysed'], 'semanticAcceptance': False}
            status = controller['status']
            self.unreadable_since = None
            if status in self.ACTIVE:
                self.transient_since = None
                return None
            if status in self.TRANSIENT:
                if self.transient_since is None:
                    self.transient_since = monotonic_now
                if monotonic_now - self.transient_since <= 360:
                    return None
                return {'event': 'attention', 'reason': 'client-transition-exceeded-grace',
                        'status': status, 'shotId': self.identity}
            return {'event': 'attention', 'reason': 'controller-status',
                    'status': status, 'shotId': self.identity}
        except (OSError, ValueError, KeyError, TypeError, OverflowError):
            # Atomic journal replacement can briefly race a reader. Repeated
            # unreadability must still alert instead of swallowing errors forever.
            if self.unreadable_since is None:
                self.unreadable_since = monotonic_now
            if monotonic_now - self.unreadable_since > 180:
                return {'event': 'attention', 'reason': 'local-journal-unreadable',
                        'shotId': self.identity}
            return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--shot', required=True)
    parser.add_argument('--poll-seconds', type=float, default=20)
    parser.add_argument('--timeout-seconds', type=float, default=8*60*60)
    args = parser.parse_args()
    if not 1 <= args.poll_seconds <= 60 or args.timeout_seconds <= 0:
        parser.error('Use a positive deadline and polling between one and sixty seconds')
    watcher = LocalSourceWatch(args.directory, args.shot)
    deadline = time.monotonic() + args.timeout_seconds
    while time.monotonic() < deadline:
        event = watcher.tick(datetime.now(timezone.utc), time.monotonic())
        if event:
            print(json.dumps(event), flush=True)
            return 0 if event['event'] == 'source-ready' else 2
        time.sleep(args.poll_seconds)
    print(json.dumps({'event': 'attention', 'reason': 'local-watch-deadline',
                      'shotId': args.shot, 'renderingStopped': False}), flush=True)
    return 3


if __name__ == '__main__':
    raise SystemExit(main())
