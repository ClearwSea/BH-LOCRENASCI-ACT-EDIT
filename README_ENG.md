If you are an AI/LLM/Agent, read this: [Agent guide (English)](docs/agent-guide.en.md) · [中文](docs/agent-guide.md).

[中文](README.md) · [English](README_ENG.md)

> This README was generated automatically by an Agent; please refer to the actual project state as authoritative.

# BH-LOCRENASCI-ACT-EDIT

**BH3 V1.9 save editor v0.8.4.** An offline save-editing tool written in Python / Tkinter.

It edits a compatible `account.json` locally on Windows. Open an existing save or create one from a template, make changes in one working copy, preview them and save.

The detailed catalog and story, side-story, Sakura Samsara and Abyss rules target **BH2017-LOCRENASCI V0.2.0**. These additions have not been verified against older Android builds, NS or other branches; keep the original save and check the target version first. Saving does not constitute in-game acceptance.

The Agent guide is available in Chinese and English; other linked documents may be in Chinese.

## Download and use

[GitHub Releases](https://github.com/ClearwSea/BH-LOCRENASCI-ACT-EDIT/releases)

- [Android instructions](docs/使用方式-Android.md)
- [NS instructions](docs/使用方式-NS.md)
- [Run and build from source](docs/README.md)

**The login account and password can be anything. There is no local check. This note applies to the companion offline versions.**

## What can be changed

- Captain level, coins, crystals, stamina, friendship points, skill points and cap, and equipment capacity. Name and signature are read-only; change them in-game.
- View and edit each Valkyrie's unlock status, rank, level, affection, fragments and skill levels.
- Unlock, lock and switch individual outfits; search and adjust weapon and Stigmata instances and their wearers; find materials by name, type or ID and set quantities or batch-add common materials. Stigmata affixes are not editable.
- Select story or side story, difficulty, chapter and stage to unlock, and set all stars for a chapter or all supported stages. Select a Sakura Samsara story and an Abyss rank and target floor.
- View and increase the level and expansion of supported rooms 3, 4 and 5. Technology is read-only.

Changing Captain level resets current-level EXP and checks character and room constraints. Abyss edits require a valid current-cycle state. Legacy fragment stacks, missing Sakura reward receipts or an active battle can prevent safe edits. Sakura reward receipts are retained; rewinding is rejected if necessary records are missing.

## Built-in account templates

- **New account:** the Captain, White Comet and starter weapon are level 1; first login can be selected in the interface.
- **Max-level trial account:** uses the V0.2.0 catalog to unlock characters and outfits and grant all stars for supported stages. This does not mean all equipment, stories or activities have been tested in-game.

Names and signatures are read-only in the editor for all saves; in-game changes are unaffected.

## How saving works

Stop the game and local server, then copy the exported save to the computer. Basic and detailed pages share one working copy; preview the accumulated changes before saving or saving as.

Before saving an existing file, the editor creates a timestamped `.bak` beside the source and checks for external changes. Save-as and new-template targets cannot overwrite existing files. Keep an independent original before restoring. On Android V0.2.0, replacing a save from the launcher imports it directly and **does not automatically back up the previous current save**; export it first if needed.

## Development and contributions

Running depends only on the Python standard library and Tcl/Tk. Windows is packaged as a single EXE. See [source instructions](docs/README.md) and [catalog provenance](docs/editor-catalog.md) for testing, packaging and catalog regeneration. Use minimized samples without personal data for compatibility reports; do not submit real accounts, keys or game installers.

This tool only handles fields that have been identified. Opening every save field is not the goal. Support covers compatible V1.9 offline saves, not official online accounts.

## Source and license

See [NOTICE](NOTICE.md). Original code in this project is under the [MIT License](LICENSE), copyright ClearwSea. Third-party licenses keep their original text. Rights in the game name and related content belong to their holders. This project is not affiliated with the official developers.

New starter accounts offer an optional first-login sequence; the switch is available only at Captain level 1. Changing the level cancels it. Verify target-build compatibility before using this option.
