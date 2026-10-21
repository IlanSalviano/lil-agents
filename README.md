# lil agents

![lil agents](hero-thumbnail.png)

Tiny AI companions that live on your macOS dock.

**Bruce**, **Jazz**, **Zenitsu**, and **Inosuke** walk back and forth above your dock. Click one to open an AI terminal. They walk, they think, they vibe.

Supports **Claude Code**, **OpenAI Codex**, **GitHub Copilot**, and **Google Gemini** CLIs — switch between them from the menubar.

**[Download for macOS](https://lilagents.xyz)** · [Website](https://lilagents.xyz)

## features

- Animated characters rendered from transparent HEVC video
- Click a character to chat with AI in a themed popover terminal
- Switch between Claude, Codex, Copilot, and Gemini from the menubar
- Four visual themes: Peach, Midnight, Cloud, Moss
- Slash commands: `/clear`, `/copy`, `/help` in the chat input
- Copy last response button in the title bar
- Thinking bubbles with playful phrases while your agent works
- Sound effects on completion
- First-run onboarding with a friendly welcome
- Auto-updates via Sparkle

## requirements

- macOS Sonoma (14.0+) — including Sequoia (15.x)
- **Universal binary** — runs natively on both Apple Silicon and Intel Macs
- At least one supported CLI installed:
  - [Claude Code](https://claude.ai/download) — `curl -fsSL https://claude.ai/install.sh | sh`
  - [OpenAI Codex](https://github.com/openai/codex) — `npm install -g @openai/codex`
  - [GitHub Copilot](https://github.com/github/copilot-cli) — `brew install copilot-cli`
  - [Google Gemini CLI](https://github.com/google-gemini/gemini-cli) — `npm install -g @google/gemini-cli`

## building

Open `lil-agents.xcodeproj` in Xcode and hit run.

Inosuke is a chibi boar-masked companion with two serrated swords, an energetic
walk, **Presas cruzadas** (a planted double slash), and **Investida da fera** (a
continuous charge). Right-click him to choose a special, or let him choose one
automatically. His Portuguese bubbles and chat style are competitive, playful,
and loyal. Character flavor does not change the selected provider's permissions.

The source artwork was created with OpenAI Images. The video assets use the
official xAI generation route from DarkYT's `GrokVideoClient`, with a separate
tracked request for each clip. Source prompts and provenance live in
`LilAgents/Art/inosuke-generation.json`. The generated sprite atlas is retained as
optional source artwork; the app plays the video clips. The first cross-slash take
was rejected for extra limbs; the bundled version uses the corrected second take.

Inosuke has independent `inosuke-animation-layouts.json` calibration. His bare
toes, rather than sword/effect bounds, determine the Dock baseline. To prepare
already-downloaded source videos (no provider calls or credits):

```sh
python3 scripts/prepare_inosuke.py --source build/inosuke/source --work build/inosuke/alpha --output LilAgents
swiftc -parse-as-library scripts/extract_animation_frames.swift -o build/inosuke/extract-frames
build/inosuke/extract-frames LilAgents build/inosuke/native-frames --full-resolution walk-inosuke-01 special-inosuke-cross-01 special-inosuke-rush-01
```

Zenitsu's walk, thunder, and flame clips use `zenitsu-animation-layouts.json` to
match body scale and place the sandals on the Dock independently of transparent
padding and effects. Movement follows the video playhead, including playback stalls.
If these movies are replaced, regenerate and visually review their sole measurements:

```sh
mkdir -p build/animation-review
swiftc -parse-as-library scripts/extract_animation_frames.swift -o build/animation-review/extract-frames
build/animation-review/extract-frames LilAgents build/animation-review/all-frames
python3 scripts/calibrate_animation_layouts.py --frames-root build/animation-review/all-frames --output LilAgents/zenitsu-animation-layouts.json
swiftc LilAgents/DockVisibility.swift LilAgents/CharacterAnimationLayout.swift LilAgents/CharacterPersonality.swift Tests/DockVisibilityTests.swift Tests/CharacterAnimationLayoutTests.swift Tests/CharacterPersonalityTests.swift Tests/main.swift -o build/animation-review/layout-tests
build/animation-review/layout-tests
```

The calibration requires Python with NumPy and Pillow. Check the feet rather than
the effect boundaries: the flame sword and dragon can extend below the sandals.

The Thunder clip also has a separate body/weapon matte and translucent lightning.
Black pockets enclosed by the arm, sword, or lightning cannot be removed by a
border flood-fill. To repair this clip from native RGBA frames, use Python with
NumPy, Pillow, and SciPy:

```sh
mkdir -p build/alpha-review/original-movies
cp LilAgents/special-zenitsu-thunder-01.mov build/alpha-review/original-movies/
build/animation-review/extract-frames build/alpha-review/original-movies build/alpha-review/original-frames --full-resolution special-zenitsu-thunder-01
python3 scripts/repair_thunder_alpha.py --frames build/alpha-review/original-frames/special-zenitsu-thunder-01 --output-frames build/alpha-review/repaired-frames
ffmpeg -y -framerate 24 -i build/alpha-review/repaired-frames/f%05d.png -c:v prores_ks -profile:v 4444 -pix_fmt yuva444p10le -an build/alpha-review/repaired-prores.mov
avconvert --source build/alpha-review/repaired-prores.mov --preset PresetHEVCHighestQualityWithAlpha --output build/alpha-review/special-zenitsu-thunder-01.mov --replace
build/animation-review/extract-frames build/alpha-review build/alpha-review/encoded-frames --full-resolution special-zenitsu-thunder-01
python3 -m unittest discover -s Tests -p 'test_thunder_alpha.py' -v
```

Review the entire exported action on light and dark backgrounds before replacing
the bundled movie. Decode the exported HEVC with the native extractor to check
its auxiliary alpha; ffmpeg's software HEVC decoder returns only the color track.
The repair guides are specific to this artwork and need review if its motion changes.

## privacy

lil agents runs entirely on your Mac and sends no personal data anywhere.

- **Your data stays local.** The app plays bundled animations and calculates your dock size to position the characters. No project data, file paths, or personal information is collected or transmitted.
- **AI providers.** Conversations are handled entirely by the CLI process you choose (Claude, Codex, Copilot, or Gemini) running locally. lil agents does not intercept, store, or transmit your chat content. Any data sent to the provider is governed by their respective terms and privacy policies.
- **No accounts.** No login, no user database, no analytics in the app.
- **Updates.** lil agents uses Sparkle to check for updates, which sends your app version and macOS version. Nothing else.

## license

MIT License. See [LICENSE](LICENSE) for details.
