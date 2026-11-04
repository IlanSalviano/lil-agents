#!/usr/bin/env python3
"""Prepare Tanjiro's magenta-screen videos for native transparent playback.

Offline only. Generates independent per-frame sandal calibration and HEVC-alpha
resources. Review every native decoded frame before accepting the new movies.
Requires ffmpeg, macOS avconvert, NumPy and Pillow.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

NAMES = ['walk-tanjiro-01', 'special-tanjiro-water-01', 'special-tanjiro-hinokami-01']
SOURCES = {name: name + '-v2' for name in NAMES}


def run(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])


def key_magenta(rgb):
    data = rgb.astype(np.float32)
    # Both red AND blue must dominate green: preserve the green haori, burgundy
    # hair, blue water and orange flames. Remove enclosed background pockets too.
    dominance = np.minimum(data[:, :, 0], data[:, :, 2]) - data[:, :, 1]
    key = np.clip((dominance - 15) / 100, 0, 1)
    alpha = 1 - key * key * (3 - 2 * key)
    spill = np.maximum(dominance, 0) * (1 - alpha)
    data[:, :, 0] -= spill
    data[:, :, 2] -= spill
    data = np.clip(data, 0, 255)
    data[alpha < .01] = 0
    return np.dstack([data.astype(np.uint8), (alpha * 255).astype(np.uint8)])


def measure(rgba):
    r, g, b, a = [rgba[:, :, i].astype(float) for i in range(4)]
    # Sandal soles are warm neutral/tan. Exclude blue water and saturated flames.
    sole = ((a > 200) & (r >= g - 8) & (g >= b - 8) & (b > 30)
            & (r - b < 90) & (r - g < 55))
    sole[:int(rgba.shape[0] * .68)] = False
    rows = np.flatnonzero(sole.sum(axis=1) >= 4)
    occupied = np.flatnonzero((a > 200).sum(axis=1) >= 5)
    if not len(rows) or not len(occupied):
        raise ValueError('No sandals detected; inspect the source instead of guessing.')
    return int(rows[-1]) + 1, int(occupied[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--clips', nargs='+', choices=NAMES, default=NAMES,
                        help='Prepare only these clips, preserving other existing layout entries')
    args = parser.parse_args()
    for name in args.clips:
        source_name = SOURCES.get(name, name)
        if not (args.source / (source_name + '.mp4')).is_file():
            parser.error(f'Missing source clip: {source_name}.mp4')
    layout_path = args.output / 'tanjiro-animation-layouts.json'
    layouts = json.loads(layout_path.read_text()) if layout_path.exists() else {}
    args.output.mkdir(parents=True, exist_ok=True)
    for name in args.clips:
        raw = args.work / name / 'raw'
        keyed = args.work / name / 'rgba'
        if raw.exists() or keyed.exists():
            parser.error(f'Use a fresh --work directory to avoid stale frames: {args.work}')
        raw.mkdir(parents=True)
        keyed.mkdir(parents=True)
        source_name = SOURCES.get(name, name)
        run(['ffmpeg', '-y', '-i', str(args.source / (source_name + '.mp4')),
             '-vf', 'scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:0xff00ff,fps=24',
             '-an', str(raw / 'f%05d.png')])
        frames = sorted(raw.glob('f*.png'))
        if not frames:
            raise ValueError(f'No decoded frames for {name}')
        soles, previews = [], []
        first_top = None
        sample_indices = set(np.linspace(0, len(frames) - 1, 12, dtype=int))
        for i, frame in enumerate(frames):
            rgba = key_magenta(np.asarray(Image.open(frame).convert('RGB')))
            sole, top = measure(rgba)
            soles.append(sole)
            if first_top is None:
                first_top = top
            result = Image.fromarray(rgba)
            result.save(keyed / frame.name)
            if i in sample_indices:
                previews.append((i, result.copy()))
        layouts[name] = dict(canvasScale=round((652 / 960) * 1280 / (soles[0] - first_top), 5),
                             sampleRate=24, referenceHeight=1280, soleRows=soles)
        board = Image.new('RGB', (6 * 180, 2 * 350), '#e9e8e4')
        draw = ImageDraw.Draw(board)
        for j, (i, frame) in enumerate(previews):
            x, y = j % 6 * 180, j // 6 * 350
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
    (args.output / 'tanjiro-animation-layouts.json').write_text(json.dumps(layouts, indent=2) + '\n')


if __name__ == '__main__':
    main()
