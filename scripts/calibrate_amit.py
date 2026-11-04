#!/usr/bin/env python3
"""Finalize Amit's shoe calibration from native decoded HEVC-alpha frames.

Run extract_animation_frames.swift first. Encoding can soften a few shoe-edge
pixels, so the native frames, rather than the pre-encode matte, own the baseline.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from prepare_amit import NAMES, measure


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames', type=Path, required=True)
    parser.add_argument('--layout', type=Path, required=True)
    args = parser.parse_args()
    layouts = json.loads(args.layout.read_text())
    for name in NAMES:
        frames = sorted((args.frames / name).glob('*.png'))
        if len(frames) != 240:
            parser.error(f'{name}: expected 240 native frames, found {len(frames)}')
        soles = []
        for frame in frames:
            with Image.open(frame) as image:
                rgba = np.asarray(image.convert('RGBA'))
            if rgba.shape != (1280, 720, 4):
                parser.error(f'{frame}: expected full-resolution RGBA frames')
            sole, top = measure(rgba)
            if not soles:
                layouts[name]['canvasScale'] = round((652 / 960) * 1280 / (sole - top), 5)
            soles.append(sole)
        layouts[name]['soleRows'] = soles
    args.layout.write_text(json.dumps(layouts, indent=2) + '\n')
    print('Calibrated all three Amit clips from native HEVC-alpha frames')


if __name__ == '__main__':
    main()
