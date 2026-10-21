"""Validate the actual HEVC auxiliary alpha after native AVFoundation extraction.

Run extract_animation_frames.swift with --full-resolution into
build/inosuke/native-frames before running these checks.
"""
import json
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
NAMES = ['walk-inosuke-01', 'special-inosuke-cross-01', 'special-inosuke-rush-01']


class InosukeAssetsTests(unittest.TestCase):
    def test_native_frames_and_ground_contact(self):
        layouts = json.loads((ROOT / 'LilAgents/inosuke-animation-layouts.json').read_text())
        for name in NAMES:
            native = sorted((ROOT / 'build/inosuke/native-frames' / name).glob('*.png'))
            self.assertTrue(native, f'Native extraction required for {name}')
            layout = layouts[name]
            self.assertEqual(len(native), len(layout['soleRows']))
            for index, frame in enumerate(native):
                with self.subTest(clip=name, frame=index):
                    rgba = np.asarray(Image.open(frame).convert('RGBA'))
                    self.assertEqual(rgba.shape, (1280, 720, 4))
                    r, g, b, a = [rgba[:, :, i].astype(float) for i in range(4)]
                    self.assertLessEqual(int(a[:20].max()), 2)
                    self.assertLessEqual(int(a[-20:].max()), 2)
                    self.assertGreater(float((a > 200).mean()), .06)
                    self.assertLess(float((a > 200).mean()), .55)
                    green = (g > np.maximum(r, b) + 55) & (a > 150)
                    self.assertLess(int(green.sum()), 25, 'Chroma background/spill survived encoding')
                    skin = (a > 200) & (r > 95) & (g > 45) & (r > g * 1.12) & (r > b * 1.3)
                    skin[:int(1280 * .66)] = False
                    rows = np.flatnonzero(skin.sum(axis=1) >= 3)
                    self.assertTrue(len(rows))
                    sole = int(rows[-1]) + 1
                    # The native codec may move a threshold edge by a few source pixels;
                    # at the largest display size this must remain within one Dock pixel.
                    error = abs(sole - layout['soleRows'][index]) * 200 * layout['canvasScale'] / 1280
                    self.assertLessEqual(error, 1, 'Decoded toes would float above/below the Dock')

    def test_resources_and_matching_standing_scale(self):
        layouts = json.loads((ROOT / 'LilAgents/inosuke-animation-layouts.json').read_text())
        project = (ROOT / 'lil-agents.xcodeproj/project.pbxproj').read_text()
        for name in NAMES:
            self.assertGreater((ROOT / 'LilAgents' / (name + '.mov')).stat().st_size, 10000)
            self.assertIn(name + '.mov in Resources', project)
            first = np.asarray(Image.open(sorted((ROOT / 'build/inosuke/native-frames' / name).glob('*.png'))[0]))
            top = np.flatnonzero((first[:, :, 3] > 200).sum(axis=1) >= 5)[0]
            layout = layouts[name]
            height = 200 * layout['canvasScale'] * (layout['soleRows'][0] - top) / 1280
            self.assertLess(abs(height - 200 * 652 / 960), 1)


if __name__ == '__main__':
    unittest.main()
