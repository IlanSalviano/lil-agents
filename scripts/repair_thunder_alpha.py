#!/usr/bin/env python3
"""Repair the alpha matte of the existing Thunder movie without changing its motion.

Decode the HEVC+alpha input with extract_animation_frames.swift, NOT ffmpeg's
software HEVC decoder (which drops auxiliary alpha). The clip-specific guides
below protect opaque fabric/steel; only the surrounding light uses emission alpha.
Guides use 540x960 coordinates measured on native full-resolution frames and must be reviewed
if the artwork changes. Requires NumPy, Pillow, and SciPy; no runtime dependency.
"""

import argparse
from PIL import Image, ImageDraw
import numpy as np
from scipy import ndimage as ndi
from pathlib import Path


def big_regions(mask, minimum):
    labels, _ = ndi.label(mask)
    sizes = np.bincount(labels.ravel())
    keep = sizes >= minimum
    keep[0] = False
    return keep[labels]


PANTS = {
    0: [
        (170, 600),
        (280, 590),
        (367, 596),
        (420, 617),
        (440, 665),
        (420, 706),
        (326, 710),
        (302, 677),
        (276, 663),
        (248, 684),
        (213, 739),
        (151, 741),
        (124, 703),
        (130, 665),
        (155, 629),
    ],
    1: [
        (173, 602),
        (280, 585),
        (351, 589),
        (422, 617),
        (441, 663),
        (426, 714),
        (328, 718),
        (300, 672),
        (278, 659),
        (250, 687),
        (224, 750),
        (178, 755),
        (128, 726),
        (134, 681),
        (159, 627),
    ],
    2: [
        (185, 576),
        (278, 585),
        (365, 586),
        (411, 626),
        (436, 671),
        (419, 718),
        (328, 723),
        (300, 680),
        (281, 659),
        (239, 677),
        (211, 726),
        (170, 738),
        (130, 710),
        (123, 676),
        (146, 636),
    ],
    3: [
        (208, 574),
        (280, 571),
        (340, 578),
        (401, 626),
        (431, 673),
        (413, 720),
        (326, 724),
        (298, 684),
        (279, 660),
        (238, 677),
        (213, 724),
        (168, 735),
        (128, 710),
        (121, 677),
        (147, 637),
    ],
    4: [
        (167, 573),
        (275, 580),
        (348, 576),
        (405, 617),
        (423, 664),
        (400, 717),
        (315, 720),
        (294, 680),
        (272, 657),
        (225, 672),
        (207, 713),
        (172, 733),
        (126, 714),
        (117, 674),
        (142, 609),
    ],
    5: [
        (177, 560),
        (256, 550),
        (330, 555),
        (357, 611),
        (408, 672),
        (388, 723),
        (321, 728),
        (298, 670),
        (278, 640),
        (242, 689),
        (222, 739),
        (176, 745),
        (128, 726),
        (142, 674),
        (165, 628),
    ],
    6: [
        (171, 550),
        (256, 540),
        (330, 553),
        (360, 610),
        (410, 674),
        (390, 723),
        (321, 728),
        (298, 668),
        (278, 636),
        (240, 688),
        (220, 739),
        (175, 745),
        (128, 725),
        (141, 672),
        (162, 622),
    ],
}
SHIRT = {
    0: [(310, 432), (375, 443), (351, 590), (267, 607), (286, 511)],
    1: [(290, 475), (336, 472), (333, 595), (257, 609), (270, 541)],
    2: [(218, 443), (320, 450), (329, 591), (241, 599), (206, 530)],
    3: [(205, 442), (319, 450), (329, 591), (236, 599), (198, 530)],
    4: [(233, 429), (306, 422), (301, 598), (211, 599), (214, 495)],
    5: [(225, 388), (301, 385), (306, 568), (203, 577), (212, 476)],
    6: [(224, 376), (298, 375), (304, 563), (203, 566), (214, 470)],
}
SWORD = {
    0: [(37, 674), (300, 581), (400, 535), (497, 473)],
    0.5: [(121, 694), (321, 548), (418, 442), (501, 356)],
    1: [(135, 687), (315, 531), (420, 430), (501, 319)],
    1.5: [(78, 587), (264, 444), (397, 361), (495, 292)],
    2: [(53, 533), (182, 388), (307, 267), (407, 182)],
    2.5: [(25, 465), (171, 327), (316, 236), (429, 193)],
    3: [(38, 499), (156, 335), (277, 235), (383, 157)],
    3.5: [(94, 570), (204, 542), (324, 492), (350, 455)],
    4: [(86, 532), (197, 593), (326, 645), (449, 658)],
    4.5: [(84, 539), (199, 598), (326, 650), (448, 658)],
    5: [(100, 480), (182, 578), (241, 670), (327, 758)],
    5.5: [(103, 449), (160, 596), (215, 720), (270, 780)],
    6: [(97, 464), (156, 590), (215, 720), (273, 791)],
}
COAT = {
    0: [
        (216, 405),
        (322, 422),
        (412, 481),
        (414, 562),
        (403, 620),
        (274, 635),
        (92, 620),
        (78, 477),
    ],
    1: [
        (180, 435),
        (337, 471),
        (388, 495),
        (421, 570),
        (460, 630),
        (281, 625),
        (28, 650),
        (43, 532),
    ],
    2: [
        (104, 378),
        (337, 421),
        (354, 500),
        (388, 563),
        (451, 671),
        (275, 627),
        (73, 678),
        (128, 512),
    ],
    3: [
        (103, 348),
        (327, 424),
        (354, 497),
        (390, 563),
        (459, 671),
        (275, 624),
        (70, 678),
        (123, 500),
    ],
    4: [
        (178, 410),
        (334, 399),
        (360, 461),
        (381, 560),
        (467, 650),
        (275, 617),
        (79, 672),
        (132, 512),
    ],
    5: [
        (176, 414),
        (320, 384),
        (345, 459),
        (371, 575),
        (426, 681),
        (277, 582),
        (115, 693),
        (128, 563),
    ],
    6: [
        (173, 400),
        (321, 371),
        (345, 459),
        (371, 575),
        (426, 681),
        (277, 578),
        (115, 689),
        (128, 563),
    ],
}
HEAD = {
    0: [(282, 275), (463, 477)],
    1: [(221, 286), (438, 490)],
    2: [(198, 275), (377, 469)],
    3: [(196, 294), (372, 458)],
    4: [(190, 266), (372, 452)],
    5: [(192, 220), (365, 408)],
    6: [(190, 211), (365, 390)],
}


def interpolate(points, time):
    keys = sorted(points)
    time = np.clip(time, keys[0], keys[-1])
    lower = max(t for t in keys if t <= time)
    upper = min(t for t in keys if t >= time)
    if lower == upper:
        return points[lower]
    f = (time - lower) / (upper - lower)
    return [
        (x + (u - x) * f, y + (v - y) * f)
        for (x, y), (u, v) in zip(points[lower], points[upper])
    ]


def opaque_subject_mask(a, time=0):
    rgb = a[:, :, :3].astype(np.float32)
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    r, g, b = [rgb[:, :, i] for i in range(3)]
    existing = a[:, :, 3] > 180
    warm = (r > 100) & (g > 75) & (b > r * 0.22) & (r >= g) & (g >= b) & existing
    roots = big_regions(ndi.binary_erosion(warm, iterations=3), 300)
    yy = np.arange(a.shape[0])[:, None]
    foot = (mx > 100) & ((mx - mn) < 45) & (yy > 670) & existing
    roots |= big_regions(ndi.binary_erosion(foot, iterations=2), 100)
    neutral = (mx > 12) & (mx < 100) & ((mx - mn) < 25) & (mn > mx * 0.6) & existing
    seeds = ndi.binary_erosion(neutral, iterations=2)
    labels, count = ndi.label(seeds)
    sizes = np.bincount(labels.ravel())
    distances = ndi.distance_transform_edt(~roots)
    closest = ndi.minimum(distances, labels, index=np.arange(count + 1))
    kept = (sizes >= 100) & (closest < 12)
    kept[0] = False
    body = ndi.binary_dilation(roots | kept[labels], iterations=5)
    # Bright lightning crosses opaque fabric too. Close those thin cuts before
    # filling the subject's interior; the weapon/FX remain separate below.
    closed_fabric = ndi.binary_fill_holes(ndi.binary_closing(body, iterations=8))
    # Only fill small ink details or enclosed dark fabric. Never fill a loop
    # merely because a sword, arm, or lightning stroke encloses the background.
    holes, n = ndi.label(~body)
    for label, box in enumerate(ndi.find_objects(holes), 1):
        if box is None:
            continue
        ys, xs = box
        if (
            ys.start == 0
            or xs.start == 0
            or ys.stop == a.shape[0]
            or xs.stop == a.shape[1]
        ):
            continue
        area = (holes[box] == label).sum()
        if area < 32:
            body[box] |= holes[box] == label
            continue
        expanded = (
            slice(max(0, ys.start - 1), min(a.shape[0], ys.stop + 1)),
            slice(max(0, xs.start - 1), min(a.shape[1], xs.stop + 1)),
        )
        m = holes[expanded] == label
        ring = ndi.binary_dilation(m) & ~m
        clothing = neutral[expanded][ring]
        if clothing.mean() > 0.8:
            body[expanded] |= m
    domain = Image.new("L", (a.shape[1], a.shape[0]))
    dd = ImageDraw.Draw(domain)
    dd.polygon(interpolate(COAT, time), fill=255)
    body |= closed_fabric & (np.asarray(domain) > 0)
    corners = interpolate(HEAD, time)
    dd.ellipse([*corners[0], *corners[1]], fill=255)
    body &= np.asarray(domain) > 0
    # Preserve facial ink and skin even when a flash interrupts color seeds.
    face = Image.new("L", (a.shape[1], a.shape[0]))
    (left, top), (right, bottom) = corners
    ImageDraw.Draw(face).ellipse(
        (left + 20, top + 90, right - 20, bottom - 10), fill=255
    )
    body |= np.asarray(face) > 0
    # White/gray socks and tan sandals are opaque, including their dark straps.
    # Color-connected foot silhouettes avoid the horizontal edge of a box matte.
    foot_region = Image.new("L", (a.shape[1], a.shape[0]))
    fd = ImageDraw.Draw(foot_region)
    fd.rectangle((70, 680, 235, 815), fill=255)
    fd.rectangle((295, 680, 460, 815), fill=255)
    shoe_pixels = (mx > 12) & ((mx - mn) < 55) & (mn > mx * 0.5) & existing
    shoe_pixels &= np.asarray(foot_region) > 0
    body |= ndi.binary_dilation(
        ndi.binary_fill_holes(big_regions(shoe_pixels, 100)), iterations=2
    )
    # Clip-specific guards protect genuinely black fabric and the solid weapon.
    # They are separate from the glow so an enclosed background gap stays clear.
    guard = Image.new("L", (a.shape[1], a.shape[0]))
    draw = ImageDraw.Draw(guard)
    for polygon in [PANTS, SHIRT]:
        draw.polygon(interpolate(polygon, time), fill=255)
    # Use the guide to locate the weapon, then retain its actual colored pixels.
    # A guide alone can capture an adjacent black background pocket as it moves.
    weapon = Image.new("L", (a.shape[1], a.shape[0]))
    ImageDraw.Draw(weapon).line(
        interpolate(SWORD, time), fill=255, width=16, joint="curve"
    )
    weapon_pixels = (np.asarray(weapon) > 0) & (mx > 12)
    body |= ndi.binary_dilation(weapon_pixels, iterations=1) & (np.asarray(weapon) > 0)
    draw.rectangle((70, 738, 235, 815), fill=255)
    draw.rectangle((295, 738, 460, 815), fill=255)
    body |= np.asarray(guard) > 0
    return body


def repair_frame(rgba, time):
    if rgba.ndim != 3 or rgba.shape[2] != 4:
        raise ValueError("Expected decoded RGBA pixels, not black-backed RGB")
    if rgba.shape[0] * 540 != rgba.shape[1] * 960:
        raise ValueError("Expected a 9:16 video canvas")
    canonical = np.asarray(
        Image.fromarray(rgba).resize((540, 960), Image.Resampling.LANCZOS)
    )
    matte = opaque_subject_mask(canonical, time)
    matte = (
        np.asarray(
            Image.fromarray(matte.astype(np.uint8) * 255).resize(
                (rgba.shape[1], rgba.shape[0]), Image.Resampling.NEAREST
            )
        )
        > 0
    )
    rgb = rgba[:, :, :3].astype(np.float32)
    brightness = rgb.max(axis=2) / 255
    factor = np.where(matte, 1, brightness)
    output = rgba.copy()
    output[:, :, 3] = np.round(rgba[:, :, 3] * factor).astype(np.uint8)
    # Unpremultiply the emission: this preserves its original appearance on
    # black while replacing black fill with the desktop on every other color.
    output[:, :, :3] = (
        np.round(
            np.divide(
                rgb,
                factor[:, :, None],
                out=np.zeros_like(rgb),
                where=factor[:, :, None] > 0,
            )
        )
        .clip(0, 255)
        .astype(np.uint8)
    )
    output[output[:, :, 3] == 0, :3] = 0
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=Path, required=True)
    parser.add_argument("--output-frames", type=Path, required=True)
    args = parser.parse_args()
    frames = sorted(args.frames.glob("*.png"))
    if len(frames) != 145:
        raise ValueError(
            f"Expected all 145 Thunder frames at 24 fps; got {len(frames)}"
        )
    args.output_frames.mkdir(parents=True, exist_ok=True)
    for index, frame in enumerate(frames):
        rgba = np.asarray(Image.open(frame).convert("RGBA"))
        output = repair_frame(rgba, index / 24)
        Image.fromarray(output).save(args.output_frames / f"f{index:05d}.png")
        if index % 12 == 0 or index == len(frames) - 1:
            print(f"Repaired {index + 1}/{len(frames)} frames", flush=True)


if __name__ == "__main__":
    main()
