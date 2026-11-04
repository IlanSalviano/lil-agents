"""Check actual native HEVC-alpha frames, not ffmpeg's color-only decode.

First run extract_animation_frames.swift --full-resolution for Amit into
build/amit/native-frames.
"""
import json
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['walk-amit-01', 'special-amit-flow-01', 'special-amit-point-01']


class AmitAssetsTests(unittest.TestCase):
    def test_native_alpha_clothing_and_dock_contact(self):
        layouts = json.loads((ROOT / 'LilAgents/amit-animation-layouts.json').read_text())
        for name in NAMES:
            frames = sorted((ROOT / 'build/amit/native-frames' / name).glob('*.png'))
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
                    # Allow low-opacity codec ringing; solid body or gesture clipping
                    # at the canvas edges must fail.
                    self.assertLessEqual(int(a[:, :2].max()), 16, 'Gesture clipped at left edge')
                    self.assertLessEqual(int(a[:, -2:].max()), 16, 'Gesture clipped at right edge')
                    self.assertGreater(float((a > 200).mean()), .06)
                    self.assertLess(float((a > 200).mean()), .55)
                    magenta = (np.minimum(r, b) - g > 70) & (a > 150)
                    self.assertLess(int(magenta.sum()), 25, 'Opaque chroma background/spill survived')
                    # No effect or prop extends below Amit's sneakers.
                    rows = np.flatnonzero((a > 200).sum(axis=1) >= 5)
                    self.assertTrue(len(rows))
                    sole = int(rows[-1]) + 1
                    error = abs(sole - layout['soleRows'][i]) * 200 * layout['canvasScale'] / 1280
                    self.assertLessEqual(error, 1, 'Shoes would float above/below Dock')

    def test_bundled_resources_and_standing_scale(self):
        layouts = json.loads((ROOT / 'LilAgents/amit-animation-layouts.json').read_text())
        project = (ROOT / 'lil-agents.xcodeproj/project.pbxproj').read_text()
        for name in NAMES:
            self.assertGreater((ROOT / 'LilAgents' / (name + '.mov')).stat().st_size, 10000)
            self.assertIn(name + '.mov in Resources', project)
            first = np.asarray(Image.open(sorted((ROOT / 'build/amit/native-frames' / name).glob('*.png'))[0]))
            top = np.flatnonzero((first[:, :, 3] > 200).sum(axis=1) >= 5)[0]
            layout = layouts[name]
            body_height = 200 * layout['canvasScale'] * (layout['soleRows'][0] - top) / 1280
            self.assertLess(abs(body_height - 200 * 652 / 960), 1)


if __name__ == '__main__':
    unittest.main()
