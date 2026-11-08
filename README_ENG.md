[中文](README.md) · [English](README_ENG.md)

> This README was generated automatically by an Agent; please refer to the actual project state as authoritative.

# BH-LOCRENASCI-ACT-EDIT

**BH3 V1.9 save editor.** An offline save-editing tool written in Python / Tkinter.

It edits a compatible `account.json` on Windows for this project's Android and NS offline versions. Reading the file, previewing changes, and saving or saving as a new file all stay on the local machine.

Linked documents in this repository are still in Chinese.

## Download and use

[GitHub Releases](https://github.com/ClearwSea/BH-LOCRENASCI-ACT-EDIT/releases)

- [v0.8.1 Windows build](release/v0.8.1/README.md)
- [Android instructions](docs/使用方式-Android.md)
- [NS instructions](docs/使用方式-NS.md)
- [Run and build from source](docs/README.md)

**The login account and password can be anything. There is no local check. This note applies to the companion offline versions.**

## What can be changed

- Captain level (1–80), coins, crystals, stamina, and friend points.
- Nickname and signature on an ordinary save.
- Sakura Samsara: cycle 1 through cycle 4 PART1, continuing from the start of the selected cycle.
- Full completion with full stars for the story and side stories. Related missions are marked claimed, and rewards are not reissued.
- Abyss progress to floor 32, and a choice among seven ranks.

Changing the level resets the current level's experience to zero. Character and equipment levels do not change with it. Abyss edits require a valid current-cycle Abyss state.

## Built-in account templates

- **New account:** the Captain, the starter White Comet, and the starter weapon are all level 1.
- **Max-level trial account:** the Captain and 26 Valkyries at level 80, story and side stories at full stars, Sakura Samsara at cycle 4 PART1, with a verified equipment catalog, skins, and full affection. Defaults are stamina 160, 100,000 coins, and 1,000 crystals.

Nicknames and signatures of both templates are read-only inside the editor. Opening the template save again keeps that limit. Changes made inside the game are not limited. The templates are not complete game data. Equipment coverage is described in the usage notes.

## How saving works

Existing files are backed up automatically before saving, and the tool checks whether the original file was modified externally. A new template only creates a new file. Export the file back to the matching version's save directory under the name `account.json`.

## Development and contributions

Running depends only on the Python standard library and Tcl/Tk. The current version includes 35 automated tests. Compatibility issues are welcome when explained with a minimized sample that has personal data removed. Do not submit real accounts, keys, or game installers.

This tool only handles fields that have been identified. Opening every save field is not the goal. Support covers compatible V1.9 offline saves, not official online accounts.

## Source and license

See [NOTICE](NOTICE.md). Original code in this project is under the [MIT License](LICENSE), copyright ClearwSea. Third-party licenses keep their original text. Rights in the game name and related content belong to their holders. This project is not affiliated with the official developers.

New starter accounts offer an optional first-login opening sequence (off by default; requires Android V0.1.3 or later). The switch is available for new starter accounts at captain level 1. Changing to another level unchecks it; saving disables first login for any captain level other than 1.
