"""Regression checks against the actual movie frames that exposed the matte bug.

Run after AVFoundation extraction and repair_thunder_alpha.py. These compare
background gaps, dark fabric, steel, and soles rather than a corner-only check.
"""

from pathlib import Path
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "build/alpha-review/original-frames/special-zenitsu-thunder-01"
REPAIRED = ROOT / "build/alpha-review/repaired-frames"
ENCODED = ROOT / "build/alpha-review/encoded-frames/special-zenitsu-thunder-01"


class ThunderAlphaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ORIGINAL.exists() or not REPAIRED.exists():
            raise unittest.SkipTest("Extract and repair the original movie first")

    def frames(self, index):
        original = sorted(ORIGINAL.glob("*.png"))[index]
        before = np.asarray(Image.open(original).convert("RGBA"))
        after = np.asarray(Image.open(REPAIRED / f"f{index:05d}.png").convert("RGBA"))
        return before, after

    def test_enclosed_gaps_are_transparent(self):
        before, after = self.frames(72)
        for x, y, maximum in [(175, 295, 8), (110, 470, 24)]:
            with self.subTest(point=(x, y)):
                self.assertGreater(int(before[y * 2, x * 2, 3]), 240)
                self.assertLessEqual(int(after[y * 2, x * 2, 3]), maximum)

    def test_dark_fabric_weapon_and_soles_remain_opaque(self):
        probes = [
            (72, 355, 671),
            (72, 132, 808),
            (72, 200, 292),
            (120, 260, 465),
            (120, 200, 698),
            (120, 260, 333),
            (120, 290, 340),
            (12, 155, 725),
        ]
        for index, x, y in probes:
            before, after = self.frames(index)
            with self.subTest(frame=index, point=(x, y)):
                self.assertGreater(int(before[y * 2, x * 2, 3]), 240)
                np.testing.assert_array_equal(before[y * 2, x * 2], after[y * 2, x * 2])

    def test_glow_preserves_appearance_on_black(self):
        before, after = self.frames(72)
        old_light = before[:, :, :3].astype(np.float32) * before[:, :, 3:4] / 255
        new_light = after[:, :, :3].astype(np.float32) * after[:, :, 3:4] / 255
        self.assertLessEqual(float(np.max(np.abs(old_light - new_light))), 1.1)

    def test_all_frames_keep_the_canvas_and_foot_baseline(self):
        originals = sorted(ORIGINAL.glob("*.png"))
        repaired = sorted(REPAIRED.glob("*.png"))
        self.assertEqual(len(originals), 145)
        self.assertEqual(len(repaired), 145)
        for index in range(145):
            before, after = self.frames(index)
            self.assertEqual(after.shape, (1920, 1080, 4))
            # The sole measurements already used by the app span rows 1616..1624.
            # Keep those existing opaque pixels unchanged throughout the action.
            opaque = before[1616:1625, :, 3] > 180
            np.testing.assert_array_equal(
                before[1616:1625][opaque], after[1616:1625][opaque]
            )
            self.assertEqual(int(after[0, :, 3].max()), 0)
            self.assertEqual(int(after[:, 0, 3].max()), 0)

    def test_native_hevc_export_keeps_the_repaired_alpha(self):
        if not ENCODED.exists():
            self.skipTest("Decode the exported HEVC with AVFoundation first")
        encoded = sorted(ENCODED.glob("*.png"))
        self.assertEqual(len(encoded), 145)
        for index, path in enumerate(encoded):
            _, repaired = self.frames(index)
            actual = np.asarray(Image.open(path).convert("RGBA"))
            self.assertEqual(actual.shape, repaired.shape)
            error = np.abs(actual[:, :, 3].astype(int) - repaired[:, :, 3])
            self.assertLess(float(error.mean()), 0.8, f"alpha track, frame {index}")
            self.assertEqual(int(actual[0, :, 3].max()), 0)
            self.assertEqual(int(actual[:, 0, 3].max()), 0)
            # Quantization must not make the existing foot anchor translucent.
            opaque_soles = repaired[1616:1625, :, 3] > 240
            self.assertTrue(np.all(actual[1616:1625, :, 3][opaque_soles] > 230))


if __name__ == "__main__":
    unittest.main()
