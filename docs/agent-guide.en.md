# Agent guide: create, edit, and restore saves

[中文](agent-guide.md) · [English](agent-guide.en.md)

**Document version date: 2026/11/10. This guide may lag behind the actual project.** Before acting, carefully compare it with the current repository, selected commit, release notes, configuration examples, and actual file layout—especially supported platforms, required inputs, tool paths, command arguments, and save compatibility. When they differ, follow the verified project state and promptly tell the user which instructions are outdated and how you will adjust. Explicitly identify anything you cannot confirm. Do not treat this guide as a permanently valid command list. If you cannot check online, explain that your conclusions are limited to the local version.

Assume you already have this repository address and are reading it, regardless of vendor or Agent environment. Do not ask again for a known address. Carry out authorized work according to the user’s goal; explain specific missing materials or access and the next step. Check current source, usage documentation, and the selected release rather than presenting unpublished development records as supported features.

This guide does not pin project release versions. Select from current official releases and compatibility requirements, recording actual versions. Game input versions, dependency versions, and example paths are not project releases to download; verify them separately before acting.

## How the three projects work together

| Repository | Guide |
| --- | --- |
| BH2017-LOCRENASCI | [Android building and playing](https://github.com/ClearwSea/BH2017-LOCRENASCI/blob/main/docs/agent-guide.en.md) |
| BH-LOCRENASCI-ACT-EDIT | [Save creation, editing, and restoration](agent-guide.en.md) |
| BH-NX-Ferculum | [NS building, integration, and validation](https://github.com/ClearwSea/BH-NX-Ferculum/blob/main/docs/agent-guide.en.md) |

Follow the guide for the current goal; installing all three repositories is unnecessary. Use the editor when a save is needed, then return to the target platform’s game guide. Do not request usable materials again. Carry forward the user’s platform, versions, file paths, goal, and authorization rather than restarting the questions. Cross-project guides do not replace checks of actual version and interface compatibility.

## Before starting: communication and network checks

### Explain progress in language the user understands

Assess familiarity from the user's questions and feedback without labeling them as having “low technical ability.” If they are unfamiliar with building, signing, or file paths, **at every step** briefly explain what you are doing, why, what currently blocks progress, what they need to do next, and any precautions relevant to that step. If nothing is blocked or no user action is needed, say so. Do not invent problems or overwhelm them with a complete technical manual.

Ask necessary questions before reaching a step that depends on a user decision or missing material, rather than after it fails. Start with their device and available materials. Before downloading, explain file size and destination. Before installation, establish whether this is a new install or an update and whether the save is backed up. Before generating a save, explain starter and max-level experience templates. Ask only a few questions needed for the current and immediately following step. Reuse answers and authorization already given; inspect what you can yourself first. While waiting, continue work that does not depend on the answer.

For example: “I'll check download speed first because the build tools are large, so we don't discover a connection problem halfway through. You don't need to do anything yet. Next, please tell me how much free disk space you have, or let me check it directly.” If the network is blocked, explain the impact and alternatives rather than just displaying an error or telling the user to solve it themselves.

### Test the actual download environment; do not assume a reliable proxy

Assume the user's Agent **does not have a reliable network proxy**. Before downloading large files, use available tools for a quick check with time and traffic limits. Being able to read the repository does not prove that large release assets download reliably. An Agent's cloud connection also does not represent the user's computer connection.

1. In the environment that will actually download the files, test the repository/release page or GitHub API. Record response status and elapsed time. A connection timeout of about 10 seconds and a total request limit of about 20 seconds are reasonable starting points. Retry only a limited number of times.
2. Obtain a real asset URL from actual release metadata and follow redirects to test downloading. Prefer a small sample of about 1–4 MiB, with an approximately 20-second total timeout and a hard byte limit. Record bytes received, average speed, and interruptions. Stop at the limit even if the server ignores Range; do not turn a speed test into a full download. A HEAD request alone does not measure download speed.
3. Estimate download duration using the actual asset size. Repeated timeouts, interrupted transfers, or sustained speeds below roughly 200 KiB/s for a large package are examples of poor quality, not rigid pass/fail thresholds. Distinguish authentication errors, API rate limits, and expired or invalid links from network problems.
4. If you cannot make network requests, say that you could not test. Give the user short executable instructions or commands and explain what results to return. Do not fabricate a successful check.

If the connection is poor, **explicitly tell the user: “The current environment has a poor connection to GitHub,”** supported by measured timeouts, speed, or estimated waiting time. This can occur on some networks in mainland China, but location alone is not evidence. Also explain which downloads remain necessary and what preparation can continue.

Then proactively devise and try a workable way to obtain the release. Do not merely tell the user to “find a proxy.” Choose based on your tools and their environment: official direct asset links, a downloader with resume support, an existing user-approved proxy or alternate network, downloading through the browser and handing the file to the Agent, or downloading in another authorized environment and transferring it back. When user participation is necessary, explain the approach, why it can help, and the specific step they need to take.

This guide does not prescribe a permanently valid mirror or proxy address. If a third-party relay is necessary, verify availability and disclose the source first. Do not send it GitHub credentials, signing keys, or saves, and do not disable TLS certificate validation. Check downloaded files against official SHA-256 values when provided. If an official checksum is temporarily unavailable, mark verification as pending rather than claiming the file is trusted. Proxy installation, system setting changes, and paid services require the applicable user authorization; download problems do not authorize unrelated environment changes.

## 1. What this repository does

This is a desktop offline save editor for `account.json` used by the companion Android/NS offline versions. Create a save from a template, or open an existing save, preview changes, save, and restore it to the game. It does not supply the game client or handle official online accounts.

Read the [README](../README_ENG.md), [source instructions](README.md), and the target platform's [Android instructions](使用方式-Android.md) or [NS instructions](使用方式-NS.md). **Using the editor alone does not require 1.9/2.4 APKs or 7.x resources.** If the user does not have a game installation, follow the appropriate game guide; request those materials only when undertaking a game build.

Deliver the requested save, the original backup location, and platform-specific restore steps—not merely an editor download link.

## 2. Establish the task

Inspect existing information, then ask as needed: new save or existing save; Android or NS and which offline build; computer OS; requested values/progress; existing save location. Explain to beginners that the save is “the file that stores your characters and progress”; they do not need to understand JSON.

For an existing save, explicitly request `account.json` **exported from actual play**, not the initial save bundled with an installer. Accept a local path, upload, or accessible shared location, and specify a concrete folder on the confirmed computer. If export is unfamiliar, guide the user through section 6. Creating a template does not require an old save.

Before editing, stop the game and any server writing the save, copy the file to the computer, and keep an independent original backup. Copy MTP/FTP files locally before opening; do not edit a file in transit.

## 3. Obtain and start the editor

Apply the network checks above to [this project's releases](https://github.com/ClearwSea/BH-LOCRENASCI-ACT-EDIT/releases). Read the current stable release notes, download the appropriate Windows asset, verify against supplied official checksums, and extract completely. Run the actual editor EXE in that package rather than guessing a versioned filename. Release packages generally do not require a separate Python installation; follow the current release instructions.

With a suitable source environment, run from the repository root:

```powershell
python save_editor.py
```

Source execution uses Python's standard library and Tcl/Tk. At this guide's date, documentation recommends Windows Python 3.13 with Tcl/Tk. Check that `tkinter` imports. Python in a chat environment is not the user's desktop GUI environment. Explain missing Python/Tk before installing under authorization or using the released package instead.

## 4. Create a template save

Explain the choices plainly and let the user choose:

| Template | Intended use | Explain |
| --- | --- | --- |
| Starter (“新号”) | Starting from the beginning | Low level, initial character/equipment; not the experience account's progress |
| Max-level experience (“满级体验号”) | Trying characters, equipment, and stages | High levels and preset progress; equipment coverage follows template documentation and does not imply complete gameplay validation |

Select the template at the top, click “使用模板新建” (Create from template), review the preview, and save to a **new, nonexistent filename**. Prefer `account.json` for delivery; if it exists in that folder, choose another location rather than overwrite the only old save.

Use “首次登录” (First login) only for an eligible starter account. On Android, first verify support in the target build. At this guide's date it is available only at captain level 1, defaults off, and is canceled by level changes. **The full NS opening flow has not been verified: leave it off** unless current project documentation explicitly records subsequent validation.

Template nickname/signature fields are read-only in the editor; ordinary saves allow editing. In-game changes follow client behavior. Do not unlock fields or modify templates to bypass restrictions.

## 5. Edit an existing save

Click “打开存档” (Open save), select the local copy, and change only requested items. Click “预览修改” (Preview changes), explain the changes and effects plainly, then save or save as according to the user's established intent.

| Setting | Behavior at this guide's date; check current instructions |
| --- | --- |
| Captain level | Range 1–80; changing it clears current level EXP, does not upgrade characters/equipment, and grants no level-up rewards |
| Coins, crystals, stamina, friendship points | Respect tool validation limits; do not bypass them |
| Ordinary-save nickname/signature | Editable; template identity fields remain read-only |
| Complete story/extra stages | Fills supported normal-story/extra progress and stars, marking related tasks claimed without granting rewards; not all Hard, Nightmare, or other modes |
| Sakura Samsara | Starts at the selected cycle's beginning; skipping does not directly award rewards, replaying previous story may award story rewards again, and existing cycle-settlement claim records remain |
| Abyss floor 32/rank | Floor 32 becomes challengeable, not completed; requires valid current-period state. Refresh the current abyss in-game and finish battle before exiting/exporting |

Leaving progression options unchecked means no change, not clearing progress. Do not reset unrelated data. Changing abyss rank preserves current floor, items, and claimed rewards without awarding promotion rewards, but clears old-rank interactions and final-floor timing; temperature and opponents refresh on entry.

The tool detects external changes to the original file, backs up existing saves before saving, and prevents save-as/template targets from overwriting existing files. On conflict, check whether the game is still running or the wrong file was selected; do not remove validation to force a save. Identify the actual backup location and preserve both automatic and independent original backups.

## 6. Restore for the target platform

### Android

Prefer the game's startup-screen “导出当前存档” (Export current save) and “选择存档/重选存档” (Select/reselect save) functions. Export current progress, edit on the computer, then select the edited `account.json` and confirm replacement/old-save retention. See the [Android game guide](https://github.com/ClearwSea/BH2017-LOCRENASCI/blob/main/docs/agent-guide.en.md).

For older standalone servers or other branches, establish the actual save location using the [Android instructions](使用方式-Android.md). App-private directories are normally inaccessible through ordinary USB file transfer; do not tell beginners to browse `/data/user/0/`. A server running on the computer uses its own save, not a file copied to the phone. Use ADB or similar tools only with the relevant access and authorization.

### NS

Use HOME → X to **fully close the game**; returning to HOME is insufficient. Transfer using the user's existing working DBI, FTP, or direct SD-card access. The default path is:

```text
sd:/switch/bh3_2017/server-stage3/data/account.json
```

Check whether the current build changes that path, then restore the edited file as `account.json` to the original location. DBI accesses an SD-card file, not a system-save import; copy MTP files to the computer first. See the [NS game guide](https://github.com/ClearwSea/BH-NX-Ferculum/blob/main/docs/agent-guide.en.md). Do not transfer Android import procedures or first-login support conclusions directly to NS.

### Verify and recover

Restart the game, check requested values/progress, perform a normal save, and restart to check persistence. Saving the file successfully is not in-game acceptance. On failure, preserve the error and edited file, fully stop the game/server, and restore the original backup to the actual read location. Do not troubleshoot by uninstalling or deleting all data.

The companion offline version accepts arbitrary login credentials. This does not imply support for official online accounts or identical behavior in every third-party branch.

## 7. Development and packaging, when needed

Running source requires neither game clients nor the original private project. After changes, run from the repository root:

```powershell
python -B -m unittest test_save_editor
```

To produce an EXE, check the [source instructions](README.md) and `requirements-build.txt`, then prepare dependencies under authorization:

```powershell
python -m venv .build-env
.\.build-env\Scripts\python.exe -m pip install -r requirements-build.txt
.\build_exe.cmd
```

The output is `dist/BH3-V1.9-Save-Editor.exe`. Source includes `templates/` and `stage_catalog.json`; the original project's template-generation scripts and private inputs are absent, so do not assume all templates can be regenerated. Test the actual dependency-download network too; GitHub connectivity does not establish package-index connectivity.

## 8. Troubleshooting and handoff

If a file cannot open, check complete JSON and compatible offline-save format. For missing fields, check version/template rather than inventing fields. For save failures, check paths, permissions, external changes, and existing targets. If in-game values do not change, verify the actual active save location and whether the game overwrote the edited result.

Collect the exact error, editor version, target game platform/version, and minimal reproduction steps. Obtain consent and remove personal information when requesting a sample; do not upload real saves by default. Posting an issue requires explicit user instruction.

Explain what was generated/changed, output and original-backup locations, restore steps, and completed checks. Without gameplay verification, state “File saved; in-game validation pending.”
