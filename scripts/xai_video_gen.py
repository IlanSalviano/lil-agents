#!/usr/bin/env python3
"""Generate videos via xAI Imagine API (raw HTTP). Works when Grok Build tool is ZDR-blocked."""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def load_token() -> str:
    auth = json.loads(Path.home().joinpath(".grok/auth.json").read_text())
    entry = next(iter(auth.values()))
    token = entry.get("key") or entry.get("access_token")
    if not token:
        raise SystemExit("No API key found in ~/.grok/auth.json")
    return token


def data_url_for(path: Path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


def api_request(method: str, url: str, token: str, body: dict | None = None, timeout: int = 120):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            hdrs = {k.lower(): v for k, v in resp.headers.items()}
            return resp.status, hdrs, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}
        raise SystemExit(f"HTTP {e.code} {url}: {parsed}") from e


def generate_video(
    token: str,
    prompt: str,
    image: Path | None,
    out: Path,
    duration: int = 6,
    resolution: str = "720p",
    aspect_ratio: str | None = "9:16",
    model: str = "grok-imagine-video",
    poll_s: float = 4.0,
    timeout_s: float = 600.0,
) -> Path:
    body: dict = {
        "model": model,
        "prompt": prompt,
        "duration": duration,
        "resolution": resolution,
    }
    if aspect_ratio:
        body["aspect_ratio"] = aspect_ratio
    if image is not None:
        body["image"] = {"url": data_url_for(image)}

    print(f"Starting generation → {out.name}", flush=True)
    print(f"  image={image} duration={duration}s res={resolution}", flush=True)
    status, hdrs, start = api_request(
        "POST", "https://api.x.ai/v1/videos/generations", token, body
    )
    print(f"  start status={status} zdr={hdrs.get('x-zero-data-retention')} request_id={start.get('request_id')}", flush=True)
    rid = start.get("request_id")
    if not rid:
        raise SystemExit(f"No request_id: {start}")

    t0 = time.time()
    while True:
        if time.time() - t0 > timeout_s:
            raise SystemExit(f"Timed out after {timeout_s}s (request_id={rid})")
        time.sleep(poll_s)
        _, ph, poll = api_request("GET", f"https://api.x.ai/v1/videos/{rid}", token)
        st = poll.get("status")
        prog = poll.get("progress")
        print(f"  poll status={st} progress={prog}", flush=True)
        if st == "done":
            video = poll.get("video") or {}
            url = video.get("url")
            if not url:
                raise SystemExit(f"Done but no url: {poll}")
            if not video.get("respect_moderation", True):
                raise SystemExit("Video failed moderation")
            out.parent.mkdir(parents=True, exist_ok=True)
            req = urllib.request.Request(url, headers={"User-Agent": "lilagents-video-gen/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                out.write_bytes(resp.read())
            print(f"  saved {out} ({out.stat().st_size} bytes) duration={video.get('duration')}", flush=True)
            return out
        if st in ("failed", "expired"):
            raise SystemExit(f"Generation {st}: {poll}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image", type=Path, help="Source still for image-to-video")
    p.add_argument("--prompt", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--duration", type=int, default=6)
    p.add_argument("--resolution", default="720p", choices=["480p", "720p", "1080p"])
    p.add_argument("--aspect-ratio", default="9:16")
    p.add_argument("--model", default="grok-imagine-video")
    args = p.parse_args()
    token = load_token()
    generate_video(
        token=token,
        prompt=args.prompt,
        image=args.image,
        out=args.out,
        duration=args.duration,
        resolution=args.resolution,
        aspect_ratio=args.aspect_ratio,
        model=args.model,
    )


if __name__ == "__main__":
    main()
