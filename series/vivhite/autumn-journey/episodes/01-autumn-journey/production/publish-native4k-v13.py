"""Publish exact reviewed assets, resume safely, and verify complete downloads.

GPL-3.0-only. Run separately from the conversation; no model or renderer call.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import subprocess
import time


def fingerprint(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8', newline='\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--target-commit', required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    root = args.repository.resolve()
    package_file = run / 'release-package.json'
    package = json.loads(package_file.read_text('utf-8'))
    metadata = run / 'release-metadata'
    metadata.mkdir(exist_ok=True)
    repo = package['repo']
    tag = package['tag']
    target = args.target_commit
    if len(target) != 40 or any(c not in '0123456789abcdef' for c in target):
        raise ValueError('Exact Git commit required')
    gate_path = (root / package['gate']).resolve()
    assert gate_path.is_relative_to(root)
    assert fingerprint(gate_path) == package['gateSha256']
    gate = json.loads(gate_path.read_text('utf-8'))
    assert gate['releaseAllowed'] is True
    for key, hash_key in [('finalReview', 'finalReviewSha256'),
                          ('deliveryPlan', 'deliveryPlanSha256'),
                          ('characterReceipt', 'characterReceiptSha256')]:
        path = gate_path.parent.parent / gate[key]
        assert fingerprint(path) == gate[hash_key]
    files = package['files']
    assert len(files) == 6
    for item in files:
        path = run / 'release' / item['name']
        assert path.is_file() and path.stat().st_size == item['bytes']
        assert fingerprint(path) == item['sha256']
    assert files[0]['sha256'] == gate['filmSha256']

    def command(arguments, timeout=1800):
        result = subprocess.run(arguments, cwd=root, capture_output=True,
                                text=True, encoding='utf-8', timeout=timeout)
        if result.returncode:
            raise RuntimeError(result.stderr[-5000:])
        return result.stdout

    def api(endpoint):
        return json.loads(command(['gh', 'api', endpoint], timeout=90))

    old_tags = ['autumn-journey-v12-768p-20261119',
                'autumn-journey-v11-4k-first24-review-20261119']
    def old_snapshot():
        snapshots = []
        for old_tag in old_tags:
            data = api(f'repos/{repo}/releases/tags/{old_tag}')
            snapshots.append({'tag': old_tag, 'id': data['id'],
                              'assets': [{'id': a['id'], 'name': a['name'],
                                          'size': a['size'], 'digest': a['digest']}
                                         for a in data['assets']]})
        return snapshots
    before_file = metadata / 'preserved-release-assets-before.json'
    if not before_file.exists():
        write_json(before_file, old_snapshot())
    before = json.loads(before_file.read_text('utf-8'))
    request = {'tag_name': tag, 'target_commitish': target,
               'name': package['name'], 'body': (run / 'release-notes.md').read_text('utf-8'),
               'draft': True, 'prerelease': True, 'make_latest': 'false'}
    request_file = metadata / 'create-release-request.json'
    if request_file.exists():
        assert json.loads(request_file.read_text('utf-8')) == request
    else:
        write_json(request_file, request)
    lookup = subprocess.run(['gh', 'api', f'repos/{repo}/releases/tags/{tag}'],
                            cwd=root, capture_output=True, text=True,
                            encoding='utf-8', timeout=90)
    if lookup.returncode == 0:
        release = json.loads(lookup.stdout)
    elif '404' in lookup.stderr:
        try:
            release = json.loads(command(['gh', 'api', f'repos/{repo}/releases',
                                          '--input', str(request_file)], timeout=90))
        except (RuntimeError, subprocess.TimeoutExpired):
            # A create request may succeed remotely before the response is lost.
            release = api(f'repos/{repo}/releases/tags/{tag}')
    else:
        raise RuntimeError('Release lookup failed; creation not attempted')
    assert release['tag_name'] == tag and release['target_commitish'] == target
    assert release['name'] == request['name'] and release['body'] == request['body']
    assert release['prerelease'] is True
    release_id = release['id']
    write_json(metadata / 'release-identity.json', release)
    print('Release identity verified', release_id, flush=True)

    def state(stage, **values):
        write_json(run / 'durable-release-state.json', {
            'updatedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'stage': stage, 'releaseId': release_id, 'tag': tag,
            'targetCommit': target, **values})

    expected_names = {f['name'] for f in files}
    for index, item in enumerate(files, 1):
        for attempt in range(1, 4):
            details = api(f'repos/{repo}/releases/{release_id}')
            existing = {a['name']: a for a in details['assets']}
            assert set(existing).issubset(expected_names), 'Unexpected release asset; preserve for investigation'
            if item['name'] in existing:
                asset = existing[item['name']]
                assert asset['size'] == item['bytes'] and asset['digest'] == 'sha256:' + item['sha256'], 'Existing asset differs; do not overwrite'
                break
            assert details['draft'], 'Missing asset in already published release'
            state('uploading', asset=item['name'], assetIndex=index, totalAssets=len(files), attempt=attempt)
            try:
                output = command(['gh', 'release', 'upload', tag, '--repo', repo,
                                  str(run / 'release' / item['name'])])
                (metadata / f'upload-{index}-attempt-{attempt}.log').write_text(output, encoding='utf-8')
            except (RuntimeError, subprocess.TimeoutExpired) as error:
                (metadata / f'upload-{index}-attempt-{attempt}-error.log').write_text(str(error), encoding='utf-8')
                if attempt == 3:
                    # Recheck even after a timed-out final attempt; never replace bytes.
                    details = api(f'repos/{repo}/releases/{release_id}')
                    asset = next((a for a in details['assets'] if a['name'] == item['name']), None)
                    assert asset and asset['size'] == item['bytes'] and asset['digest'] == 'sha256:' + item['sha256']
                else:
                    time.sleep(10)
        details = api(f'repos/{repo}/releases/{release_id}')
        asset = next(a for a in details['assets'] if a['name'] == item['name'])
        assert asset['size'] == item['bytes'] and asset['digest'] == 'sha256:' + item['sha256']
        print('Server digest verified', index, '/', len(files), item['name'], flush=True)
    details = api(f'repos/{repo}/releases/{release_id}')
    assert {a['name'] for a in details['assets']} == expected_names
    publish_file = metadata / 'publish-request.json'
    write_json(publish_file, {'draft': False, 'prerelease': True, 'make_latest': 'false'})
    if details['draft']:
        command(['gh', 'api', '--method', 'PATCH', f'repos/{repo}/releases/{release_id}',
                 '--input', str(publish_file)], timeout=90)
    published = api(f'repos/{repo}/releases/{release_id}')
    assert published['draft'] is False and published['prerelease'] is True
    assert published['body'] == request['body']
    write_json(metadata / 'published-release.json', published)
    print('Published', published['html_url'], flush=True)
    state('published-full-download-verification-pending', url=published['html_url'])
    downloads = run / 'release-download-verification'
    downloads.mkdir(exist_ok=True)
    assets = {a['name']: a for a in published['assets']}
    verified = []
    for index, item in enumerate(files, 1):
        destination = downloads / item['name']
        if destination.exists():
            assert destination.stat().st_size == item['bytes'] and fingerprint(destination) == item['sha256']
        else:
            for attempt in range(1, 4):
                attempt_directory = downloads / f'attempt-{index}-{attempt}'
                if attempt_directory.exists():
                    downloaded = attempt_directory / item['name']
                    if downloaded.exists() and downloaded.stat().st_size == item['bytes'] and fingerprint(downloaded) == item['sha256']:
                        downloaded.rename(destination)
                        break
                    continue  # Retain earlier partial files; never overwrite them.
                attempt_directory.mkdir()
                state('verifying-complete-remote-download', asset=item['name'], assetIndex=index, totalAssets=len(files), attempt=attempt)
                try:
                    command(['gh', 'release', 'download', tag, '--repo', repo,
                             '--pattern', item['name'], '--dir', str(attempt_directory)])
                    downloaded = attempt_directory / item['name']
                    assert downloaded.stat().st_size == item['bytes'] and fingerprint(downloaded) == item['sha256']
                    downloaded.rename(destination)
                    break
                except (RuntimeError, subprocess.TimeoutExpired, AssertionError) as error:
                    (metadata / f'download-{index}-attempt-{attempt}-error.log').write_text(str(error), encoding='utf-8')
                    if attempt == 3:
                        raise
                    time.sleep(10)
            assert destination.exists(), 'All bounded download attempts exhausted; partial evidence retained'
        assert fingerprint(destination) == item['sha256']
        asset = assets[item['name']]
        verified.append({**item, 'assetId': asset['id'], 'url': asset['browser_download_url'],
                         'serverDigestVerified': True, 'fullActualRemoteDownloadShaVerified': True})
        print('Full download verified', index, '/', len(files), item['name'], flush=True)
    after = old_snapshot()
    write_json(metadata / 'preserved-release-assets-after.json', after)
    assert before == after, 'Historical release assets changed; investigate before claiming preservation'
    result = {'schemaVersion': 'vivhite-release-upload-and-download-verification-1',
              'verifiedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'tag': tag, 'releaseId': release_id, 'url': published['html_url'],
              'targetCommit': target, 'draft': False, 'prerelease': True,
              'bodyUtf8Verified': True, 'assets': verified,
              'oldReleasesPreserved': True, 'allFullRemoteDownloadsVerified': True,
              'filmSha256': gate['filmSha256'], 'releaseGateSha256': package['gateSha256'],
              'publisherSha256': fingerprint(Path(__file__))}
    write_json(metadata / 'verification.json', result)
    state('complete-all-full-downloads-verified', url=published['html_url'], verifiedAssets=len(verified))
    print('Verified all assets and preserved historical releases.', flush=True)


if __name__ == '__main__':
    main()
