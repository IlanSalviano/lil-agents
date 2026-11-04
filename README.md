# lil agents

![lil agents](hero-thumbnail.png)

Tiny AI companions that live on your macOS dock.

**Bruce**, **Jazz**, **Zenitsu**, **Inosuke**, **Tanjiro**, **Nezuko**, **Bill**, and **Amit** walk back and forth above your dock. Click one to open an AI terminal. They walk, they think, they vibe.

Supports **Claude Code**, **OpenAI Codex**, **GitHub Copilot**, and **Google Gemini** CLIs — switch between them from the menubar.

**[Download for macOS](https://github.com/IlanSalviano/lilagents-releases/releases/latest)** · [Original project](https://github.com/ryanstephen/lil-agents)

## features

- Animated characters rendered from transparent HEVC video
- Click a character to chat with AI in a themed popover terminal
- Switch between Claude, Codex, Copilot, and Gemini from the menubar
- Four visual themes: Peach, Midnight, Cloud, Moss
- Slash commands: `/clear`, `/copy`, `/help` in the chat input
- Copy last response button in the title bar
- Thinking bubbles with playful phrases while your agent works
- Per-character macOS voices (Standard, Enhanced and Premium), with preview and saved preferences
- Sound effects on completion
- First-run onboarding with a friendly welcome
- Auto-updates via Sparkle

## character voices

Right-click any character and open **Voice**, or use **Voices → character** in the
menu bar. Voices are grouped by language and labeled **Standard**, **Enhanced** or
**Premium**. Select a voice to save it immediately for that character, then choose
**Test Voice** to hear a sample. **Stop Preview** stops the sample; starting another
sample replaces the previous one. Explicit previews work even with **Sounds** off.

**Automatic** uses the highest available quality for the character's default
language. Download additional voices through macOS Accessibility settings (the
menu includes Apple's download guide); reopen the menu to refresh the list.
If a saved voice is no longer installed, the menu shows a warning and speech uses
Automatic until that voice is available again or you select another one.

Voice choices apply to synthesized speech, currently Bill and Amit's special
phrases, and previews for every character. They do not replace recorded audio in
animation clips or add spoken chat responses. Automatic special speech still
respects **Sounds**, hiding and interruption.

Voice preference and installed-catalog checks:

```sh
mkdir -p build/voice-review
swiftc -parse-as-library LilAgents/CharacterVoice.swift Tests/CharacterVoiceTests.swift -o build/voice-review/voice-tests
build/voice-review/voice-tests
```

`scripts/verify_voice_runtime.swift` checks all character context menus, preview
start/stop with Sounds off, and native audio rendering for installed quality tiers
in an isolated review app. Premium playback can only be checked when installed.

## requirements

- macOS Sonoma (14.0+) — including Sequoia (15.x)
- **Universal binary** — runs natively on both Apple Silicon and Intel Macs
- At least one supported CLI installed:
  - [Claude Code](https://claude.ai/download) — `curl -fsSL https://claude.ai/install.sh | sh`
  - [OpenAI Codex](https://github.com/openai/codex) — `npm install -g @openai/codex`
  - [GitHub Copilot](https://github.com/github/copilot-cli) — `brew install copilot-cli`
  - [Google Gemini CLI](https://github.com/google-gemini/gemini-cli) — `npm install -g @google/gemini-cli`

## releases e atualizações

Esta edição usa um canal próprio de Sparkle e DMGs universais notarizados.
Veja [RELEASING.md](RELEASING.md) para publicar versões e testar **1.3.0 sem Amit →
1.3.1 com Amit**. O empacotador legado não habilita este canal.

## building

Open `lil-agents.xcodeproj` in Xcode and hit run.

Amit is a chibi companion inspired by Amit Zavery's public product and engineering
presence, with salt-and-pepper hair and a charcoal quarter-zip sweater. His fictional
persona is approachable, technical, pragmatic and optimistic. Right-click him for
**Lets Flow! — soco no ar**, a celebratory upward fist pump, or
**Let's make work flow! — apontar**, an energetic forward point. Both gestures stay
planted on the Dock and use their selected macOS voice when **Sounds**
is on. Playback controls the timing of text and speech; hiding/interruption stops
speech. He walks, chooses specials automatically, and launches alongside the other
companions. He does not represent Amit Zavery or ServiceNow officially.

Reference artwork and the exact built-in image prompt are in `LilAgents/Art/amit-*`;
video prompts are in `scripts/amit-prompts.json`. Generate/resume source clips with
`scripts/generate_amit.py` and the existing GrokVideoClient. Prepare offline:

```sh
python3 scripts/prepare_amit.py --source build/amit/source --work build/amit/alpha --output LilAgents
swiftc -parse-as-library scripts/extract_animation_frames.swift -o build/amit/extract-frames
build/amit/extract-frames LilAgents build/amit/native-frames --full-resolution walk-amit-01 special-amit-flow-01 special-amit-point-01
python3 scripts/calibrate_amit.py --frames build/amit/native-frames --layout LilAgents/amit-animation-layouts.json
python3 -m unittest discover -s Tests -p 'test_amit_assets.py' -v
```

`scripts/verify_amit_runtime.swift` exercises native playback, planted gestures,
delayed text with sound disabled, environment pause/recovery, walking and all sizes.

Bill is a chibi caricature inspired by Bill McDermott's public keynote presence:
silver hair, sunglasses, a navy suit, and a confident, motivating personality.
Right-click him for **Let's go! — soco no ar**, a celebratory upward fist pump,
or **Put AI to Work! — apontar**, a forward pointing gesture. Both stay planted
on the Dock and speak their English phrases with their selected macOS voice when
**Sounds** is on. Text and voice cues follow video playback; hiding or interrupting
stops speech. He also walks and chooses specials automatically. His chat persona
is fictional, not an official representation of Bill McDermott or ServiceNow.

Artwork and provenance are in `LilAgents/Art/bill-*`; complete video prompts are
in `scripts/bill-prompts.json`. Preparation and verification use the same native
HEVC-alpha pipeline as the other companions:

```sh
python3 scripts/prepare_bill.py --source build/bill/source --work build/bill/rebuild --output LilAgents
swiftc -parse-as-library scripts/extract_animation_frames.swift -o build/bill/extract-frames
build/bill/extract-frames LilAgents build/bill/native-frames --full-resolution walk-bill-01 special-bill-letsgo-01 special-bill-ai-01
python3 scripts/calibrate_bill.py --frames build/bill/native-frames --layout LilAgents/bill-animation-layouts.json
python3 -m unittest discover -s Tests -p 'test_bill_assets.py' -v
```

`scripts/verify_bill_runtime.swift` checks actual native playback, planted gestures,
delayed text cues with sound disabled, environment pause, recovery and all sizes.

Nezuko is a tiny, shy, curious and protective companion. **Correr até o Zenitsu**
runs toward the visible Zenitsu with both arms stretched forward and oversized
haori sleeves hanging beyond her hands. She follows his position and stops nearby;
if he is hidden, the run stays idle or cancels in place. **Despertar: salto da Nezuko**
grows into her taller horned combat form, performs a flying kick, lands and returns
to the tiny form. Right-click her to select either action. She also walks and chooses
actions automatically, and appears at launch alongside Zenitsu, Inosuke and Tanjiro.
Her Portuguese personality affects presentation only, never tool permissions.

Nezuko's OpenAI Images references and generation record are in `LilAgents/Art/`;
the complete prompts are in `scripts/nezuko-prompts.json`. The blue-screen videos
use the existing Grok client and resumable jobs in `build/nezuko/source/`.
`nezuko-animation-layouts.json` keeps her standing body at 65% of the other anime
companions' height. The jump uses an interpolated ground plane during airtime so
foot anchoring preserves the jump. The awakening uses the clean first 111 frames
of take 3, reverses the landing/shrink, and holds the initial tiny pose; the provider's
later ghost silhouette and incomplete recovery are excluded. Preparation is offline:

```sh
python3 scripts/prepare_nezuko.py --source build/nezuko/source --work build/nezuko/rebuild --output LilAgents --jump 3.6666666667 5.5
swiftc -parse-as-library scripts/extract_animation_frames.swift -o build/nezuko/extract-frames
build/nezuko/extract-frames LilAgents build/nezuko/native-frames --full-resolution walk-nezuko-01 special-nezuko-run-01 special-nezuko-awaken-01
python3 -m unittest discover -s Tests -p 'test_nezuko_assets.py' -v
```

`scripts/verify_nezuko_runtime.swift` exercises actual native playback, approach
from both directions, moving/hidden Zenitsu, differing sizes, narrow Docks,
environment pause/resume, mirroring and recovery in an isolated review app.

Tanjiro is a chibi companion with a green-and-black checkered haori, a calm walk,
**Respiração da Água** (a water sword crescent), and **Hinokami Kagura** (a fire
sword arc). Right-click him to choose an attack, or let him choose automatically.
His Portuguese bubbles and conversation style are gentle, empathetic and determined.
He appears at launch alongside Zenitsu and Inosuke; the menubar controls visibility,
size and AI provider for each companion. Personality affects style, never permissions.

Tanjiro's OpenAI Images reference and generation record live in `LilAgents/Art/`;
the exact prompts are in `scripts/tanjiro-prompts.json`. Source videos are generated
through the same Grok/xAI client used for Inosuke. Each clip has a resumable request
record in `build/tanjiro/source/`. Magenta is used for the source background so the
green haori survives keying. The app plays transparent HEVC, with independent
per-frame sandal calibration in `tanjiro-animation-layouts.json`.
The bundled clips use the second takes and the wider battle reference; first takes
were rejected for cropped sword tips or effects. Canvas scaling keeps Tanjiro's
standing height consistent across walking and both attacks.

To prepare downloaded source videos offline, use a fresh work directory:

```sh
python3 scripts/prepare_tanjiro.py --source build/tanjiro/source --work build/tanjiro/alpha --output LilAgents
swiftc -parse-as-library scripts/extract_animation_frames.swift -o build/tanjiro/extract-frames
build/tanjiro/extract-frames LilAgents build/tanjiro/native-frames --full-resolution walk-tanjiro-01 special-tanjiro-water-01 special-tanjiro-hinokami-01
python3 -m unittest discover -s Tests -p 'test_tanjiro_assets.py' -v
```

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
