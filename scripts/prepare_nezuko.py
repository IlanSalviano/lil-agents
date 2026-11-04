#!/usr/bin/env python3
"""Key reviewed blue-screen Nezuko clips and encode native HEVC auxiliary alpha.

Offline only. Each movie has independent scale and sandal measurements. During
the jump, interpolate the ground plane, NOT the airborne soles, so Dock anchoring
does not cancel the jump. Use a fresh work directory for each preparation.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from prepare_tanjiro import run

NAMES = ['walk-nezuko-01', 'special-nezuko-run-01', 'special-nezuko-awaken-01']
SOURCES = {'special-nezuko-awaken-01': 'special-nezuko-awaken-01-v3'}
BODY_FRACTION = .44  # 88px at Large, versus the other companions' ~136px.


def key_blue(rgb):
    data = rgb.astype(np.float32)
    dominance = data[:, :, 2] - np.maximum(data[:, :, 0], data[:, :, 1])
    key = np.clip((dominance - 12) / 100, 0, 1)
    alpha = 1 - key * key * (3 - 2 * key)
    data[:, :, 2] = np.where(alpha < .99,
                             np.minimum(data[:, :, 2], np.maximum(data[:, :, 0], data[:, :, 1])),
                             data[:, :, 2])
    data[alpha < .01] = 0
    return np.dstack([data.astype(np.uint8), (alpha * 255).astype(np.uint8)])


def measure(rgba):
    r, g, b, a = [rgba[:, :, i].astype(float) for i in range(4)]
    # Warm neutral sandal soles, excluding pink flame and trailing dark hair.
    sandal = ((a > 200) & (r > 65) & (g > 45) & (r >= g - 8)
              & (g >= b - 5) & (r - g < 95) & (g - b < 85))
    sandal[:int(rgba.shape[0] * .45)] = False
    rows = np.flatnonzero(sandal.sum(axis=1) >= 5)
    occupied = np.flatnonzero((a > 200).sum(axis=1) >= 5)
    if not len(rows) or not len(occupied):
        raise ValueError('No sandals/body found; inspect source instead of guessing.')
    return int(rows[-1]) + 1, int(occupied[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--clips', nargs='+', choices=NAMES, default=NAMES)
    parser.add_argument('--jump', nargs=2, type=float,
                        help='Reviewed takeoff and landing times; required for the awakening')
    args = parser.parse_args()
    if 'special-nezuko-awaken-01' in args.clips and args.jump is None:
        parser.error('Review the source and pass --jump TAKEOFF LANDING for the awakening.')
    if args.jump is not None and not 0 < args.jump[0] < args.jump[1] < 10:
        parser.error('--jump must be an increasing interval within the 10-second clip.')
    layout_path = args.output / 'nezuko-animation-layouts.json'
    layouts = json.loads(layout_path.read_text()) if layout_path.exists() else {}
    args.output.mkdir(parents=True, exist_ok=True)
    for name in args.clips:
        source = args.source / (SOURCES.get(name, name) + '.mp4')
        if not source.is_file():
            parser.error(f'Missing source: {source}')
        raw, keyed = args.work / name / 'raw', args.work / name / 'rgba'
        if raw.exists() or keyed.exists():
            parser.error('Use a fresh work directory to avoid stale frames.')
        raw.mkdir(parents=True)
        keyed.mkdir(parents=True)
        run(['ffmpeg', '-y', '-i', str(source), '-vf', 'scale=720:1280,fps=24',
             '-an', str(raw / 'f%05d.png')])
        frames = sorted(raw.glob('f*.png'))
        if not frames:
            raise ValueError(f'No frames in {source}')
        if name == 'special-nezuko-awaken-01':
            if len(frames) != 241:
                raise ValueError('The reviewed awakening edit requires the 241-frame third take.')
            # Use the clean growth and flying kick, then retrace its landing and
            # shrink. The provider's later recovery contained a duplicate ghost
            # silhouette and retained the horn. This cut ends on the exact tiny
            # starting frame, with no ghost, crossfade or costume discontinuity.
            sequence = list(range(111)) + list(range(109, -1, -1)) + [0] * 20
            frames = [frames[i] for i in sequence]
        soles, tops, previews = [], [], []
        indices = set(np.linspace(0, len(frames) - 1, 20, dtype=int))
        for i, frame in enumerate(frames):
            rgba = key_blue(np.asarray(Image.open(frame).convert('RGB')))
            sole, top = measure(rgba)
            soles.append(sole)
            tops.append(top)
            result = Image.fromarray(rgba)
            result.save(keyed / f'f{i + 1:05d}.png')
            if i in indices:
                previews.append((i, result.copy()))
        anchors = list(soles)
        if name == 'special-nezuko-awaken-01':
            first, last = (round(t * 24) for t in args.jump)
            anchors[first:last + 1] = np.linspace(soles[first], soles[last], last - first + 1).tolist()
        # The run starts in a crouched stride; calibrate its upright recovery.
        scale_index = -1 if name == 'special-nezuko-run-01' else 0
        layouts[name] = dict(canvasScale=round(BODY_FRACTION * 1280 / (soles[scale_index] - tops[scale_index]), 6),
                             sampleRate=24, referenceHeight=1280, soleRows=anchors)
        board = Image.new('RGB', (10 * 180, 2 * 350), '#e9e8e4')
        draw = ImageDraw.Draw(board)
        for j, (i, frame) in enumerate(previews):
            x, y = j % 10 * 180, j // 10 * 350
            thumb = frame.resize((180, 320))
            board.paste(thumb, (x, y + 25), thumb)
            draw.text((x + 8, y + 8), f'{i / 24:.2f}s', fill='#20232a')
        board.save(args.work / (name + '-contact.jpg'))
        prores = args.work / name / 'prores.mov'
        run(['ffmpeg', '-y', '-framerate', '24', '-i', str(keyed / 'f%05d.png'),
             '-frames:v', str(len(frames)), '-c:v', 'prores_ks', '-profile:v', '4444',
             '-pix_fmt', 'yuva444p10le', '-an', str(prores)])
        run(['avconvert', '--source', str(prores), '--preset', 'PresetHEVCHighestQualityWithAlpha',
             '--output', str(args.output / (name + '.mov')), '--replace'])
        print(name, 'frames=', len(frames), 'soles=', (min(soles), max(soles)),
              'scale=', layouts[name]['canvasScale'], flush=True)
        layout_path.write_text(json.dumps(layouts, indent=2) + '\n')


if __name__ == '__main__':
    main()
