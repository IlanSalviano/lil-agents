#!/usr/bin/env python3
"""Key pure black background to alpha via border flood-fill, encode HEVC+alpha."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-4000:] if r.stderr else "")
        raise SystemExit(f"command failed ({r.returncode}): {cmd[0]}")


def flood_alpha(rgb: np.ndarray, thresh: int = 22, soft: int = 10) -> np.ndarray:
    """Make border-connected near-black pixels transparent. Keeps dark clothing holes filled."""
    h, w, _ = rgb.shape
    mx = rgb.max(axis=2)
    is_dark = mx <= thresh

    # BFS from borders only
    from collections import deque

    visited = np.zeros((h, w), dtype=bool)
    q: deque[tuple[int, int]] = deque()

    def try_push(y: int, x: int) -> None:
        if 0 <= y < h and 0 <= x < w and not visited[y, x] and is_dark[y, x]:
            visited[y, x] = True
            q.append((y, x))

    for x in range(w):
        try_push(0, x)
        try_push(h - 1, x)
    for y in range(h):
        try_push(y, 0)
        try_push(y, w - 1)

    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            try_push(y + dy, x + dx)

    # visited = background to remove
    # soft edge: near bg dark-ish pixels get partial alpha
    bg = visited
    alpha = np.full((h, w), 255, dtype=np.uint8)
    alpha[bg] = 0

    if soft > 0:
        # distance-ish soft edge using dilation rings on bg
        # simple: pixels adjacent to bg with low luma get reduced alpha
        from numpy.lib.stride_tricks import sliding_window_view

        # neighbor is bg?
        padded = np.pad(bg, 1, constant_values=False)
        neigh = (
            padded[:-2, 1:-1]
            | padded[2:, 1:-1]
            | padded[1:-1, :-2]
            | padded[1:-1, 2:]
        )
        edge = neigh & ~bg
        # soft fade for near-black edge pixels
        edge_dark = edge & (mx <= thresh + soft * 2)
        # map luma 0..thresh+2soft -> alpha 0..255 within edge
        span = float(thresh + soft * 2)
        a_edge = np.clip((mx.astype(np.float32) / span) * 255.0, 0, 255).astype(np.uint8)
        alpha[edge_dark] = a_edge[edge_dark]

    return alpha


def process_frame(src: Path, dst: Path, thresh: int, soft: int) -> None:
    im = Image.open(src).convert("RGB")
    rgb = np.asarray(im)
    alpha = flood_alpha(rgb, thresh=thresh, soft=soft)
    out = np.dstack([rgb, alpha])
    # Premultiply-ish clean: zero rgb where fully transparent to avoid fringes
    out[..., 0] = np.where(alpha == 0, 0, out[..., 0])
    out[..., 1] = np.where(alpha == 0, 0, out[..., 1])
    out[..., 2] = np.where(alpha == 0, 0, out[..., 2])
    Image.fromarray(out, "RGBA").save(dst)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--thresh", type=int, default=20, help="max RGB treated as keyable black")
    ap.add_argument("--soft", type=int, default=8)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    args = ap.parse_args()

    work = Path(tempfile.mkdtemp(prefix="zen-alpha-"))
    try:
        raw_dir = work / "raw"
        rgba_dir = work / "rgba"
        raw_dir.mkdir()
        rgba_dir.mkdir()

        # Scale + pad to target, extract PNG frames
        run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(args.input),
                "-vf",
                f"scale={args.width}:{args.height}:force_original_aspect_ratio=decrease,"
                f"pad={args.width}:{args.height}:(ow-iw)/2:(oh-ih)/2:black",
                "-r",
                str(args.fps),
                "-an",
                str(raw_dir / "f%05d.png"),
            ]
        )
        frames = sorted(raw_dir.glob("f*.png"))
        if not frames:
            raise SystemExit("no frames extracted")
        print(f"processing {len(frames)} frames...", flush=True)
        for i, fr in enumerate(frames, 1):
            process_frame(fr, rgba_dir / fr.name, args.thresh, args.soft)
            if i % 30 == 0 or i == len(frames):
                print(f"  {i}/{len(frames)}", flush=True)

        # ProRes 4444 intermediate (preserves alpha), then avconvert to HEVC+alpha
        prores = work / "alpha.mov"
        run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(args.fps),
                "-i",
                str(rgba_dir / "f%05d.png"),
                "-c:v",
                "prores_ks",
                "-profile:v",
                "4444",
                "-pix_fmt",
                "yuva444p10le",
                "-an",
                str(prores),
            ]
        )

        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Prefer Apple avconvert HEVC+alpha (matches Bruce/Jazz pipeline)
        av = shutil.which("avconvert")
        if av:
            run(
                [
                    av,
                    "--source",
                    str(prores),
                    "--preset",
                    "PresetHEVCHighestQualityWithAlpha",
                    "--output",
                    str(args.output),
                    "--replace",
                    "--progress",
                ]
            )
        else:
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(prores),
                    "-c:v",
                    "hevc_videotoolbox",
                    "-alpha_quality",
                    "0.9",
                    "-tag:v",
                    "hvc1",
                    "-r",
                    str(args.fps),
                    "-an",
                    str(args.output),
                ]
            )

        # Verify alpha
        check = work / "check.png"
        run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                "1",
                "-i",
                str(args.output),
                "-frames:v",
                "1",
                "-pix_fmt",
                "rgba",
                str(check),
            ]
        )
        im = Image.open(check)
        tl = im.getpixel((10, 10))
        print(f"verify tl={tl} mode={im.mode}", flush=True)
        if len(tl) < 4 or tl[3] != 0:
            print("WARNING: corner not fully transparent", flush=True)
        print(f"wrote {args.output} ({args.output.stat().st_size} bytes)", flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
