"""Validate Nezuko using every frame decoded by native AVFoundation, not ffmpeg.

Extract the three movies into build/nezuko/native-frames first. This verifies
actual encoded transparency, complete silhouettes, growth and retained airtime.
"""
import json
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['walk-nezuko-01', 'special-nezuko-run-01', 'special-nezuko-awaken-01']


def bounds(rgba):
    opaque = rgba[:, :, 3] > 200
    rows = np.flatnonzero(opaque.sum(axis=1) >= 5)
    return int(rows[0]), int(rows[-1]) + 1


class NezukoAssetsTests(unittest.TestCase):
    def test_native_alpha_and_complete_character(self):
        layouts = json.loads((ROOT / 'LilAgents/nezuko-animation-layouts.json').read_text())
        for name in NAMES:
            frames = sorted((ROOT / 'build/nezuko/native-frames' / name).glob('*.png'))
            self.assertTrue(frames, f'Native extraction required: {name}')
            self.assertEqual(len(frames), len(layouts[name]['soleRows']))
            for i, frame in enumerate(frames):
                with self.subTest(clip=name, frame=i):
                    rgba = np.asarray(Image.open(frame).convert('RGBA'))
                    self.assertEqual(rgba.shape, (1280, 720, 4))
                    r, g, b, a = [rgba[:, :, c].astype(float) for c in range(4)]
                    for edge in [a[:2], a[-2:], a[:, :2], a[:, -2:]]:
                        self.assertLessEqual(int(edge.max()), 16, 'Character is clipped or background survived')
                    self.assertGreater(float((a > 200).mean()), .015)
                    self.assertLess(float((a > 200).mean()), .6)
                    blue_spill = (b > np.maximum(r, g) + 65) & (a > 150)
                    self.assertLess(int(blue_spill.sum()), 25, 'Opaque blue screen/spill remains')
                    bamboo = (g > r + 5) & (g > b + 10) & (a > 200)
                    pink = (r > g + 15) & (b > g - 35) & (a > 200)
                    self.assertGreater(int(bamboo.sum()), 25, 'Bamboo was lost during keying')
                    self.assertGreater(int(pink.sum()), 100, 'Pink kimono/eyes were lost during keying')

    def test_growth_airtime_and_dock_scale(self):
        layouts = json.loads((ROOT / 'LilAgents/nezuko-animation-layouts.json').read_text())
        record = json.loads((ROOT / 'LilAgents/Art/nezuko-generation.json').read_text())
        jump_start, jump_end = record['jumpInterval']
        for name in NAMES:
            layout = layouts[name]
            frames = sorted((ROOT / 'build/nezuko/native-frames' / name).glob('*.png'))
            self.assertTrue(frames)
            standing = frames[-1] if '-run-' in name else frames[0]
            top, sole = bounds(np.asarray(Image.open(standing).convert('RGBA')))
            height = (sole - top) * 200 * layout['canvasScale'] / 1280
            self.assertLess(abs(height - 88), 1.5, 'Tiny standing scale differs across clips')
            if '-awaken-' not in name:
                continue
            heights, airtime = [], []
            for i, frame in enumerate(frames):
                top, sole = bounds(np.asarray(Image.open(frame).convert('RGBA')))
                heights.append(sole - top)
                if jump_start < i / 24 < jump_end:
                    airtime.append(layout['soleRows'][i] - sole)
                else:
                    error = abs(layout['soleRows'][i] - sole) * 200 * layout['canvasScale'] / 1280
                    self.assertLess(error, 1.5, 'Grounded sandals float above or below the Dock')
            self.assertGreater(max(heights), heights[0] * 1.5, 'Transformation must visibly grow')
            self.assertGreater(max(airtime), 40, 'Foot anchoring must preserve the actual jump')
            self.assertLess(abs(heights[-1] - heights[0]), heights[0] * .15,
                            'Special must recover to the tiny form')

    def test_bundle_resources(self):
        project = (ROOT / 'lil-agents.xcodeproj/project.pbxproj').read_text()
        for name in NAMES:
            self.assertGreater((ROOT / 'LilAgents' / (name + '.mov')).stat().st_size, 10000)
            self.assertIn(name + '.mov in Resources', project)
        self.assertIn('nezuko-animation-layouts.json in Resources', project)


if __name__ == '__main__':
    unittest.main()
