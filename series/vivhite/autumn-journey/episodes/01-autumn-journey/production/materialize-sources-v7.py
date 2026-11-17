"""Reuse reviewed v6 sources and the new full ten-second closing, without rendering.

The final v7 plan and actual composition still require independent semantic review.
GPL-3.0-only.
"""
import argparse
import importlib.util
from pathlib import Path

EP = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('v6_source_materializer',
    Path(__file__).with_name('materialize-sources-v6.py'))
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--directory', required=True, type=Path)
    args = parser.parse_args()
    origins = {**worker.ORIGINS,
        'S48': ('production-v7-bf16-768p-S48-001', 'production-plan-v7-S48-image-only-r1.json')}
    worker.materialize(args.base, args.directory, EP / 'production-plan-v7-bf16-768p.json', origins)
