# Amit companion

Created 2026-11-03. Fictional chibi interpretation inspired by Amit Zavery's public
product and engineering presence. Reference generated with the built-in image tool;
the exact image prompt and source provenance are in `amit-generation.json`.

- Walk, upward fist pump ("Lets Flow!"), and forward point ("Let's make work flow!").
- Three 10-second native HEVC-alpha clips, 240 frames each. Both gestures stay planted.
- Generic macOS English Eddy voice, controlled by Sounds; no cloned voice.
- Fist speech starts at 2.2s, pointing speech at 2s, against the video playhead.
- All 720 native decoded frames passed alpha, crop, scale and shoe baseline tests.
- Runtime review passed: eight companions, delayed phrases with sound off, planted
  gestures, environment pause/recovery, three sizes, mirroring and walking.
- Swift tests and Xcode Debug build passed. Signed local app verified with codesign.

Review artifacts: `build/amit/amit-specials-preview.mp4`,
`build/amit/verification.json`, and `build/amit/lil agents.app`.
Video prompts: `scripts/amit-prompts.json`. Source jobs are resumable in
`build/amit/source/`. Preparation and native calibration are offline scripts.
