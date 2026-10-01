#!/usr/bin/env python3
"""Special: transparent bg, strip gray speed-line plate, pad for margin — NO circular crop."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def run(cmd: list) -> None:
    print("+", " ".join(str(c) for c in cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write((r.stderr or "")[-5000:])
        raise SystemExit(r.returncode)


def flood_bg(rgb: np.ndarray, thresh: int = 22) -> np.ndarray:
    h, w, _ = rgb.shape
    mx = rgb.max(axis=2)
    is_dark = mx <= thresh
    visited = np.zeros((h, w), dtype=bool)
    q: deque = deque()

    def try_push(y, x):
        if 0 <= y < h and 0 <= x < w and not visited[y, x] and is_dark[y, x]:
            visited[y, x] = True
            q.append((y, x))

    for x in range(w):
        try_push(0, x); try_push(h - 1, x)
    for y in range(h):
        try_push(y, 0); try_push(y, w - 1)
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            try_push(y + dy, x + dx)
    return visited


def body_keep_mask(rgb: np.ndarray) -> np.ndarray:
    """Keep character + yellow/red lightning, fire FX, and black flame-dragon body."""
    r = rgb[:, :, 0].astype(np.int16)
    g = rgb[:, :, 1].astype(np.int16)
    b = rgb[:, :, 2].astype(np.int16)
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = mx - mn

    orange = (r > 140) & (g > 50) & (g < 170) & (b < 100) & (r > g)
    warm = (r > 170) & (g > 120) & (b > 70) & (b < 190) & (r >= g) & (sat > 25)
    # Yellow thunder + crimson fire arcs + red-orange dragon flame
    lightning = (
        ((r > 150) & (g > 130) & (b < 160) & (sat > 30))
        | ((r > 200) & (g > 180) & (b < 120))
        | ((r > 120) & (g < 100) & (b < 90) & (r > g + 25) & (sat > 30))
        | ((r > 180) & (g > 40) & (g < 170) & (b < 90) & (r > g) & (sat > 35))
    )
    # Dark clothing + black dragon body (slight red bias vs pure bg)
    dark = (mx < 90) & (mx > 8)
    dark_red = (r > 25) & (r >= g) & (r >= b) & (mx < 160) & ((sat > 12) | (r > g + 5) | (r > b + 5))
    bright = mx > 195  # socks / silver steel — only kept near body via dilate
    ember = (mx > 18) & (r + 10 > g) & (r + 10 > b) & (r > 30) & (b < r)

    seed = orange | warm | lightning | dark | dark_red | ember
    seed_img = Image.fromarray((seed.astype(np.uint8) * 255))
    # Heavy dilate so sword arcs, lightning, and dragon body fill in
    for _ in range(22):
        seed_img = seed_img.filter(ImageFilter.MaxFilter(5))
    dilated = np.array(seed_img) > 127

    keep = dilated & (seed | bright | lightning | orange | warm | dark | dark_red | ember)
    keep |= dilated & (sat > 30) & (r + g > b + 30)
    keep |= dilated & (r > g + 15) & (r > b + 15) & (mx > 20)
    # Interior dark pixels inside the dilated silhouette (black dragon fill)
    keep |= dilated & (mx > 6) & (mx < 100)
    return keep

def soft_rect_edge(alpha: np.ndarray, margin: int) -> np.ndarray:
    """Very mild fade only at the outer canvas pixels (not a circular crop of the character)."""
    if margin <= 0:
        return alpha
    h, w = alpha.shape
    yy = np.arange(h, dtype=np.float32)[:, None]
    xx = np.arange(w, dtype=np.float32)[None, :]
    dist = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    t = np.clip(dist / float(margin), 0.0, 1.0)
    fade = t * t * (3.0 - 2.0 * t)
    return (alpha.astype(np.float32) * fade).astype(np.uint8)


def process_frame(src: Path, dst: Path, out_w: int, out_h: int, content_scale: float, bg_thresh: int, edge: int) -> None:
    im = Image.open(src).convert("RGB")
    sw, sh = im.size
    cw = max(1, int(round(out_w * content_scale)))
    ch = max(1, int(round(out_h * content_scale)))
    scale = min(cw / sw, ch / sh)
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    im = im.resize((nw, nh), Image.Resampling.LANCZOS)
    rgb = np.asarray(im)

    bg = flood_bg(rgb, thresh=bg_thresh)
    keep = body_keep_mask(rgb)
    # Keep wins over flood-fill so black dragon body / dark clothing is not eaten
    # when connected to the pure-black background.
    alpha = np.where(keep, 255, 0).astype(np.uint8)
    # Still drop clear border-connected pure black that is not in keep
    alpha = np.where(bg & ~keep, 0, alpha)
    alpha = np.array(Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(radius=1.0)))

    # Soft-fade the CONTENT patch itself so hard crop lines from the source video
    # (FX that hit the raw frame edge) dissolve instead of showing as a sharp cut.
    content_edge = max(edge, int(round(min(nw, nh) * 0.12)))
    alpha = soft_rect_edge(alpha, content_edge)

    free_y = out_h - nh
    pad_bottom = int(round(free_y * 0.18))
    pad_top = free_y - pad_bottom
    pad_left = (out_w - nw) // 2

    canvas = np.zeros((out_h, out_w, 4), dtype=np.uint8)
    canvas[pad_top:pad_top + nh, pad_left:pad_left + nw, 0:3] = rgb
    canvas[pad_top:pad_top + nh, pad_left:pad_left + nw, 3] = alpha
    a = canvas[:, :, 3]
    for c in range(3):
        canvas[:, :, c] = np.where(a == 0, 0, canvas[:, :, c])

    # Outer canvas fade for extra safety near window border
    canvas[:, :, 3] = soft_rect_edge(canvas[:, :, 3], edge)
    a2 = canvas[:, :, 3]
    for c in range(3):
        canvas[:, :, c] = np.where(a2 == 0, 0, canvas[:, :, c])

    # Hard safe band: force fully transparent outer strip so nothing can touch
    # the player window edge even if source FX were edge-clipped.
    safe = max(edge, int(round(min(out_w, out_h) * 0.08)))
    canvas[:safe, :, 3] = 0
    canvas[-safe:, :, 3] = 0
    canvas[:, :safe, 3] = 0
    canvas[:, -safe:, 3] = 0
    for c in range(3):
        canvas[:, :, c] = np.where(canvas[:, :, 3] == 0, 0, canvas[:, :, c])

    Image.fromarray(canvas, "RGBA").save(dst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--content-scale", type=float, default=0.52)
    ap.add_argument("--edge-fade", type=int, default=48)
    ap.add_argument("--bg-thresh", type=int, default=20)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    args = ap.parse_args()

    work = Path(tempfile.mkdtemp(prefix="zen-sp3-"))
    try:
        raw, rgba = work / "raw", work / "rgba"
        raw.mkdir(); rgba.mkdir()
        run([
            "ffmpeg", "-y", "-i", str(args.input),
            "-vf", f"scale={args.width}:{args.height}:force_original_aspect_ratio=decrease,"
                   f"pad={args.width}:{args.height}:(ow-iw)/2:(oh-ih)/2:black",
            "-r", str(args.fps), "-an", str(raw / "f%05d.png"),
        ])
        frames = sorted(raw.glob("f*.png"))
        print(f"processing {len(frames)} scale={args.content_scale} (no circular crop)", flush=True)
        for i, fr in enumerate(frames, 1):
            process_frame(fr, rgba / fr.name, args.width, args.height, args.content_scale, args.bg_thresh, args.edge_fade)
            if i % 30 == 0 or i == len(frames):
                print(f"  {i}/{len(frames)}", flush=True)

        prores = work / "alpha.mov"
        run([
            "ffmpeg", "-y", "-framerate", str(args.fps), "-i", str(rgba / "f%05d.png"),
            "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-an", str(prores),
        ])
        args.output.parent.mkdir(parents=True, exist_ok=True)
        run([
            "avconvert", "--source", str(prores),
            "--preset", "PresetHEVCHighestQualityWithAlpha",
            "--output", str(args.output), "--replace", "--progress",
        ])
        check = work / "c.png"
        run(["ffmpeg", "-y", "-ss", "2.5", "-i", str(args.output), "-frames:v", "1", "-pix_fmt", "rgba", str(check)])
        a = np.array(Image.open(check))
        mask = a[:, :, 3] > 10
        ys, xs = np.where(mask)
        print(f"margins L={xs.min()} R={a.shape[1]-1-xs.max()} T={ys.min()} B={a.shape[0]-1-ys.max()} fill={mask.mean():.3f}")
        print(f"edge alpha T/B/L/R={a[0,:,3].max()}/{a[-1,:,3].max()}/{a[:,0,3].max()}/{a[:,-1,3].max()}")
        print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
