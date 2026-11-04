#!/usr/bin/env python3
"""Generate/resume Tanjiro source clips using the established Grok client.

Calls the provider (unlike prepare_tanjiro.py). Existing downloaded clips and
tracked request IDs are reused; failed requests are never silently resubmitted.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('clip', choices=['walk-tanjiro-01', 'special-tanjiro-water-01',
                                       'special-tanjiro-hinokami-01'])
    parser.add_argument('--client-dir', type=Path, required=True,
                        help='Directory containing grok_video_client.py; its parent contains video_qa.py')
    parser.add_argument('--take', type=int, default=1, help='New take number; preserves earlier jobs and source clips')
    args = parser.parse_args()
    sys.path.insert(0, str(args.client_dir))
    sys.path.insert(0, str(args.client_dir.parent))
    from grok_video_client import GrokVideoClient
    prompts = json.loads((ROOT / 'scripts/tanjiro-prompts.json').read_text())
    source = ROOT / 'build/tanjiro/source'
    source.mkdir(parents=True, exist_ok=True)
    if args.take < 1:
        parser.error('--take must be positive')
    name = args.clip if args.take == 1 else f'{args.clip}-v{args.take}'
    if name not in prompts:
        parser.error(f'No prompt for take: {name}')
    spec = prompts[name]
    target = source / (name + '.mp4')
    if target.is_file() and target.stat().st_size > 0:
        print('Reusing downloaded clip:', target)
        return
    GrokVideoClient(timeout_seconds=1200)._generate_via_xai_api(
        image=ROOT / 'LilAgents/Art' / spec.get('reference', 'tanjiro-reference.png'), raw_path=target,
        prompt=spec['prompt'], log=lambda message: print(
            'Iniciando um único job na API oficial xAI...' if message.startswith('Rota ZDR')
            else message, flush=True))


if __name__ == '__main__':
    main()
