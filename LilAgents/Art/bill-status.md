# Bill companion

Completed and installed on 2026-11-03 at `/Applications/lil agents.app`.
Caricature inspired by Bill McDermott's public keynote presence, with a confident,
optimistic, motivating personality. Inspiration: [ServiceNow profile](https://www.servicenow.com/company/executive-team/bill-mcdermott.html).

- Reference: `bill-reference.png`, created with the built-in image generator.
- Full image prompt, provider records and video request IDs: `bill-generation.json`.
- Full animation prompts: `../../scripts/bill-prompts.json`.
- Upward celebratory fist pump: **Let's go!**, text and voice at 1.8s.
- Forward point: **Put AI to Work!**, text and voice at 2.0s.
- Both specials remain planted on the Dock. The walk moves from 0–5.6s.
- Generic macOS English Eddy voice when installed; male en-US/default fallback.
  No voice cloning. The app's Sounds option controls speech; hiding or interrupting
  stops it. Cues follow the video playhead and fire once per action.

## Assets and preparation

All three 10-second Grok/xAI source clips were generated successfully after the
user renewed authentication. The fist-pump source included an unintended second
raise: the final clip keeps the first 5.75 seconds, including recovery, and holds
its neutral pose through 10 seconds. Each bundled clip contains 240 frames at
24fps with native HEVC transparency.

```sh
python3 scripts/prepare_bill.py --source build/bill/source --work build/bill/rebuild --output LilAgents
swiftc -parse-as-library scripts/extract_animation_frames.swift -o build/bill/extract-frames
build/bill/extract-frames LilAgents build/bill/native-frames --full-resolution walk-bill-01 special-bill-letsgo-01 special-bill-ai-01
python3 scripts/calibrate_bill.py --frames build/bill/native-frames --layout LilAgents/bill-animation-layouts.json
python3 -m unittest discover -s Tests -p 'test_bill_assets.py' -v
```

Native decoded shoe edges own the final calibration. One walking frame changed
by 13 source pixels after encoding (approximately 2 displayed pixels), corrected
in the final native calibration. The three movies and layout are bundled in Xcode.

## Validation

- Xcode Debug build and ad-hoc signature verification passed.
- All 720 native frames passed transparency, clipping, opaque body coverage,
  magenta spill, shoe contact and standing-scale checks.
- Dock visibility, animation layout and personality/history tests passed.
- `scripts/verify_bill_runtime.swift` passed with the real Bill assets: all seven
  companions, exact delayed phrases with sounds off, planted gestures, pause on
  environment hiding, recovery, three sizes, mirroring and walking.
- Both phrases were synthesized successfully as nonempty PCM with Eddy, and used
  in the audible preview; final preview peak is -4.3 dBFS. Physical speaker output
  was not independently confirmed.
- Installed asset hashes match the validated source files; updated app launched.
- `git diff --check` passed.

Evidence and preview: `build/bill/verification.json`, `build/bill/assets-tests.log`,
`build/bill/runtime-tests.log`, `build/bill/build.log`, and
`build/bill/bill-specials-preview.mp4`.
Previous installed app preserved at `build/bill/previous-installed.app`.

The earlier `build/bill/LogicReview.app` uses renamed existing animations as
playback fixtures only. Final verification used `build/bill/Review.app` with the
actual Bill resources. The computer-use screenshot selected Nezuko's unnamed
window, so installed Bill appearance was verified through native asset decoding
and the isolated runtime, not an installed-app screenshot.
