"""Bounded LK rebasing for larger carrier approach shots. GPL-3.0-only.

The raw material rim is re-seeded every24frames. No illustration pixels are
tracked or changed for tracking; cumulative drift still requires output review.
"""
import json
from pathlib import Path

import cv2
import numpy as np
import stabilize_carrier_plane as base

ORIGINAL_TRACKER = base.CarrierTracker


class SegmentedCarrierTracker:
    def __init__(self, first, polygons, excluded_polygons=(), max_shift=40, max_scale_change=.12):
        self.polygons = polygons
        self.excluded = excluded_polygons
        self.maximum_shift = max_shift
        self.maximum_scale_change = max_scale_change
        self.tracker = ORIGINAL_TRACKER(first, polygons, excluded_polygons, max_shift, max_scale_change)
        self.points = self.tracker.points
        self.anchor = np.eye(3)
        self.index = 0

    @staticmethod
    def warp(polygons, matrix):
        return [cv2.perspectiveTransform(np.float32([polygon]), matrix)[0].tolist() for polygon in polygons]

    def transform(self, frame):
        relative, metric = self.tracker.transform(frame)
        combined = relative@self.anchor
        self.index += 1
        if self.index % 24 == 0:
            self.tracker = ORIGINAL_TRACKER(frame, self.warp(self.polygons, combined),
                self.warp(self.excluded, combined), self.maximum_shift, self.maximum_scale_change)
            self.anchor = combined
        return combined, {**metric, 'anchorFrame': self.index//24*24,
            'cumulativeScale': float(np.sqrt(abs(np.linalg.det(combined[:2,:2]))))}


def composite(source, reference, destination, definition):
    if base.CarrierTracker is not ORIGINAL_TRACKER:
        raise ValueError('Unexpected tracker replacement')
    base.CarrierTracker = SegmentedCarrierTracker
    try:
        receipt = base.composite(source, reference, destination, definition)
    finally:
        base.CarrierTracker = ORIGINAL_TRACKER
    receipt.update(segmentedWorkerSha256=base.sha(__file__),
        method='Whole original physical pouch; raw carrier-only forward/backward LK with24frame rebasing. No facial/ink features. Independent complete output alignment review required.',
        trackingRebaseFrames=24)
    Path(destination).with_suffix('.carrier.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt
