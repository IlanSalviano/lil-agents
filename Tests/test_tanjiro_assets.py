"""Check actual native HEVC-alpha frames, not ffmpeg's color-only decode.

First run extract_animation_frames.swift --full-resolution for Tanjiro into
build/tanjiro/native-frames.
"""
import json
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['walk-tanjiro-01', 'special-tanjiro-water-01', 'special-tanjiro-hinokami-01']


class TanjiroAssetsTests(unittest.TestCase):
    def test_native_alpha_clothing_and_dock_contact(self):
        layouts = json.loads((ROOT / 'LilAgents/tanjiro-animation-layouts.json').read_text())
        for name in NAMES:
            frames = sorted((ROOT / 'build/tanjiro/native-frames' / name).glob('*.png'))
            self.assertTrue(frames, f'Native extraction required for {name}')
            layout = layouts[name]
            self.assertEqual(len(frames), len(layout['soleRows']))
            for i, frame in enumerate(frames):
                with self.subTest(clip=name, frame=i):
                    rgba = np.asarray(Image.open(frame).convert('RGBA'))
                    self.assertEqual(rgba.shape, (1280, 720, 4))
                    r, g, b, a = [rgba[:, :, c].astype(float) for c in range(4)]
                    self.assertLessEqual(int(a[:15].max()), 2)
                    self.assertLessEqual(int(a[-15:].max()), 2)
                    # Allow low-opacity codec ringing / fading sparks (observed alpha
                    # 3-8); solid sword/effect truncation is near 255 and must fail.
                    self.assertLessEqual(int(a[:, :2].max()), 16, 'Sword/effect clipped at left edge')
                    self.assertLessEqual(int(a[:, -2:].max()), 16, 'Sword/effect clipped at right edge')
                    self.assertGreater(float((a > 200).mean()), .06)
                    self.assertLess(float((a > 200).mean()), .55)
                    magenta = (np.minimum(r, b) - g > 70) & (a > 150)
                    self.assertLess(int(magenta.sum()), 25, 'Opaque chroma background/spill survived')
                    green = (g > r + 10) & (g > b + 5) & (a > 200)
                    self.assertGreater(int(green.sum()), 100, 'Green haori must survive chroma removal')
                    # Independent neutral/tan sandal measurement after native encoding.
                    neutral = ((a > 200) & (r >= g - 8) & (g >= b - 8) & (b > 30)
                               & (r - b < 90) & (r - g < 55))
                    neutral[:int(1280 * .68)] = False
                    rows = np.flatnonzero(neutral.sum(axis=1) >= 4)
                    self.assertTrue(len(rows))
                    sole = int(rows[-1]) + 1
                    error = abs(sole - layout['soleRows'][i]) * 200 * layout['canvasScale'] / 1280
                    self.assertLessEqual(error, 1, 'Sandals would float above/below Dock')

    def test_bundled_resources_and_standing_scale(self):
        layouts = json.loads((ROOT / 'LilAgents/tanjiro-animation-layouts.json').read_text())
        project = (ROOT / 'lil-agents.xcodeproj/project.pbxproj').read_text()
        for name in NAMES:
            self.assertGreater((ROOT / 'LilAgents' / (name + '.mov')).stat().st_size, 10000)
            self.assertIn(name + '.mov in Resources', project)
            first = np.asarray(Image.open(sorted((ROOT / 'build/tanjiro/native-frames' / name).glob('*.png'))[0]))
            top = np.flatnonzero((first[:, :, 3] > 200).sum(axis=1) >= 5)[0]
            layout = layouts[name]
            body_height = 200 * layout['canvasScale'] * (layout['soleRows'][0] - top) / 1280
            self.assertLess(abs(body_height - 200 * 652 / 960), 1)


if __name__ == '__main__':
    unittest.main()
