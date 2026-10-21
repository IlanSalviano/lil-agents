#!/usr/bin/env python3
"""Measure sole rows from AVFoundation-decoded RGBA frames, without counting FX.

Extract frames with extract_animation_frames.swift first, then pass --frames-root.
The supplied movies share a 1080x1920 canvas; measurements use 540x960 previews.
Standing body heights are 652px (walk), 587px (thunder), and 259px (flame).
Fixed canvas scales match those heights and preserve crouches and lifted legs.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def sole_row(image: np.ndarray, flame: bool) -> int:
    mask = image[:, :, 3] > 180
    if flame:
        # The flame sword and dragon extend below the sandals. Only count the
        # tan/neutral sole pixels in the feet region, excluding orange/red fire.
        r, g, b = [image[:, :, i].astype(np.int16) for i in range(3)]
        mask &= ((r > 65) & (r < 180) & (g > 55) & (b > 35)
                 & (r >= g) & (g >= b) & (r - g < 40) & (g - b < 35))
        yy, xx = np.indices(mask.shape)
        mask &= (xx > 208) & (xx < 400) & (yy > 620)
    rows = np.flatnonzero(mask.sum(axis=1) >= 3)
    if not len(rows):
        raise ValueError("No sole found; inspect this frame instead of guessing")
    return int(rows[-1]) + 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    layouts = {}
    for name, scale, count in [
        ("walk-zenitsu-01", 1.0, 241),
        ("special-zenitsu-thunder-01", 1.11, 145),
        ("special-zenitsu-flame-01", 2.52, 145),
    ]:
        frames = sorted((args.frames_root / name).glob("*.png"))
        if len(frames) != count:
            raise ValueError(f"{name}: expected {count} frames at 24 fps, got {len(frames)}")
        rows = []
        for frame in frames:
            rgba = np.asarray(Image.open(frame).convert("RGBA"))
            if rgba.shape != (960, 540, 4):
                raise ValueError(f"{frame}: expected a 540x960 RGBA frame")
            rows.append(sole_row(rgba, "flame" in name))
        layouts[name] = dict(canvasScale=scale, sampleRate=24, referenceHeight=960, soleRows=rows)
        print(f"{name}: scale={scale}, soles={min(rows)}..{max(rows)}, frames={len(rows)}")
    args.output.write_text(json.dumps(layouts, indent=2) + "\n")


if __name__ == "__main__":
    main()
