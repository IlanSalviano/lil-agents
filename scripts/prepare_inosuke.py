#!/usr/bin/env python3
"""Prepare the three generated green-screen clips for AVPlayerLayer.

No generation/network calls: decode, key green, measure bare toes, encode HEVC
with auxiliary alpha, and write this character's independent layout resource.
Review the native decoded output before accepting the resulting measurements.
"""
import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

NAMES = ['walk-inosuke-01', 'special-inosuke-cross-01', 'special-inosuke-rush-01']
SOURCES = {'special-inosuke-cross-01': 'special-inosuke-cross-v2'}


def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def key_green(rgb):
    data = rgb.astype(np.float32)
    dominance = data[:, :, 1] - np.maximum(data[:, :, 0], data[:, :, 2])
    key = np.clip((dominance - 15) / 80, 0, 1)
    alpha = 1 - key * key * (3 - 2 * key)
    # Remove green spill only at the keyed edge, preserving blue eyes and skin.
    data[:, :, 1] = np.where(alpha < .99,
                            np.minimum(data[:, :, 1], np.maximum(data[:, :, 0], data[:, :, 2])),
                            data[:, :, 1])
    data[alpha < .01] = 0
    return np.dstack([data.astype(np.uint8), (alpha * 255).astype(np.uint8)])


def measure(rgba):
    r, g, b, a = [rgba[:, :, i].astype(float) for i in range(4)]
    skin = (a > 200) & (r > 95) & (g > 45) & (r > g * 1.12) & (r > b * 1.3)
    skin[:int(rgba.shape[0] * .66)] = False
    rows = np.flatnonzero(skin.sum(axis=1) >= 3)
    if not len(rows):
        raise ValueError('No bare toes detected; inspect the frame instead of guessing.')
    occupied = np.flatnonzero((a > 200).sum(axis=1) >= 5)
    return int(rows[-1]) + 1, int(occupied[0])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    for name in NAMES:
        source_name = SOURCES.get(name, name)
        if not (args.source / (source_name + '.mp4')).is_file():
            parser.error(f'Missing source clip: {source_name}.mp4')
    layouts = {}
    args.output.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        raw = args.work / name / 'raw'
        keyed = args.work / name / 'rgba'
        raw.mkdir(parents=True, exist_ok=True)
        keyed.mkdir(parents=True, exist_ok=True)
        source_name = SOURCES.get(name, name)
        timing = ['-t', '6'] if name == 'special-inosuke-cross-01' else []
        run(['ffmpeg', '-y', '-i', str(args.source / (source_name + '.mp4')), *timing,
             '-vf', 'scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2:0x00ff00,fps=24',
             '-an', str(raw / 'f%05d.png')])
        # Ignore stale frames from a previous, longer preparation of the same clip.
        frames = sorted(raw.glob('f*.png'))[:144] if timing else sorted(raw.glob('f*.png'))
        soles = []
        first_top = None
        previews = []
        sample_indices = np.linspace(0, len(frames) - 1, 8, dtype=int)
        for i, frame in enumerate(frames):
            rgba = key_green(np.asarray(Image.open(frame).convert('RGB')))
            sole, top = measure(rgba)
            soles.append(sole)
            first_top = top if first_top is None else first_top
            result = Image.fromarray(rgba)
            result.save(keyed / frame.name)
            if i in sample_indices:
                previews.append((i, result.copy()))
        layouts[name] = dict(canvasScale=round((652 / 960) * 1280 / (soles[0] - first_top), 5),
                             sampleRate=24, referenceHeight=1280, soleRows=soles)
        board = Image.new('RGB', (8 * 180, 360), '#e9e8e4')
        draw = ImageDraw.Draw(board)
        for j, (i, frame) in enumerate(previews):
            thumb = frame.resize((180, 320))
            board.paste(thumb, (j * 180, 25), thumb)
            draw.text((j * 180 + 8, 8), f'{i / 24:.2f}s', fill='#20232a')
        board.save(args.work / (name + '-contact.jpg'))
        prores = args.work / name / 'prores.mov'
        run(['ffmpeg', '-y', '-framerate', '24', '-i', str(keyed / 'f%05d.png'),
             '-frames:v', str(len(frames)), '-c:v', 'prores_ks', '-profile:v', '4444', '-pix_fmt', 'yuva444p10le', '-an', str(prores)])
        run(['avconvert', '--source', str(prores), '--preset', 'PresetHEVCHighestQualityWithAlpha',
             '--output', str(args.output / (name + '.mov')), '--replace'])
        print(name, 'frames=', len(frames), 'soles=', (min(soles), max(soles)),
              'scale=', layouts[name]['canvasScale'], flush=True)
    (args.output / 'inosuke-animation-layouts.json').write_text(json.dumps(layouts, indent=2) + '\n')


if __name__ == '__main__':
    main()
