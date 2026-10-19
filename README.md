# Hateful Chris 2: Never Say Buy — unofficial fix patch

An unofficial fan patcher for **Hateful Chris 2: Never Say Buy** (Clickteam engine, `HCNSB.exe`).

> **This repository contains no game files.** You need your own copy of the game.
> The patcher reads your original `HCNSB.exe` and writes a new patched file next to it —
> the original is never modified.

**Status:** beta. `--inventory`, `--hud` and `--windowed` are tested in-game.
`--fix-story` is verified on the event data but not yet played through — feedback is welcome (see *Testing checklist*).

## What it fixes

Flags are passed with two dashes, e.g. `--inventory` (see the full command in **Build & run**).

| Flag | Fix |
|---|---|
| `inventory` | In the original the game keeps running while the inventory screen is open, and enemies, NPCs, visual effects and level objects are drawn on top of it. Now the game is **paused** while the inventory is open and all those objects are hidden; they reappear when the inventory is closed. |
| `hud` | (with `inventory`) also hides the top HUD panel while the inventory is open. |
| `fix-story` | **Uber quest:** the Liposuction tool is never given in the original, so the quest cannot be finished. It is now given when you take the quest. **Trixie abduction:** the story only continues if you have completed exactly 4–5 quests when entering Klub Kix; with 6+ it never triggers. Now 4–8. |
| `windowed` | Starts in an 800×600 window with a title bar instead of fullscreen. **Alt+Enter** toggles fullscreen. |
| `knife-bonus N` | Adds N to the starting knife's damage (it deals 1 in the original). |

Debug/advanced flags: `--no-pause` (hide objects only, don't pause), `--hide-name NAME` (also hide an object by name, repeatable), `--dry-run` (report only, don't write).

## Requirements
- Windows, your own copy of the game.
- [Python 3.8+](https://www.python.org/downloads/) (tick “Add Python to PATH” when installing).

## Build & run

All commands are for the Windows command prompt (`cmd`). Set your two folders once per session —
every command below uses them, so you only change the paths here:

```bat
set GAME=D:\Games\Hateful Chris
set REPO=C:\hateful-chris-patch
```
- `GAME` — the game folder (with `HCNSB.exe`, `inventory.ccn`, `Cncs232.dll`);
- `REPO` — where you unpacked this repository (**Code → Download ZIP**).

### 1. Patch the game
```bat
cd /d "%REPO%\tools"
python hc_patch.py "%GAME%\HCNSB.exe" "%GAME%\HCNSB_patched.exe" --inventory --hud --fix-story --windowed --knife-bonus 5
```
Drop any flags you don't want; `python hc_patch.py -h` shows the full help.
Always patch the **original** `HCNSB.exe`, not an already patched one.

Check the output. Expected lines (printed in Russian):
- `Liposuction добавлена в 2 событий … исправлено в 1` — Liposuction added in 2 events, abduction condition fixed in 1;
- `Окно: флаги заголовка 0xAC9A -> 0xB498, размер 800x600` — window mode enabled.

Then start `%GAME%\HCNSB_patched.exe`. It must stay in the game folder (next to `inventory.ccn` and `Cncs232.dll`).

### 2. (Optional) Build a standalone `hc_patch.exe` — players won't need Python
```bat
cd /d "%REPO%\tools"
pip install pyinstaller
pyinstaller --onefile hc_patch.py
```
The result is `%REPO%\tools\dist\hc_patch.exe`; it is used exactly like the script:
```bat
"%REPO%\tools\dist\hc_patch.exe" "%GAME%\HCNSB.exe" "%GAME%\HCNSB_patched.exe" --inventory --hud --fix-story --windowed
```
Attach it to a GitHub Release — never commit it (it is ignored by `.gitignore`).

### 3. (Optional) Extract the game data — for research and the Godot prototype
```bat
cd /d "%REPO%\tools"
python hc_run_all.py "%GAME%\HCNSB.exe" "%REPO%\work"
```
Everything goes to `%REPO%\work`: logic dumps in `work\logic`, data and notes in `work\data`, Godot-ready assets in `work\hc_godot`.
The folder is ignored by git — **never upload it**, it is the game's copyrighted content.
Findings about the game (quests, weapons, enemies, loot, shops, save format, level map) are documented in [`docs/`](docs).
Script comments and docs are mostly in Russian.

### 4. (Optional) Run the Godot prototype (work in progress)
[`godot/`](godot) is a Godot 4.4+ prototype of the Downtown level built from the data of your own copy of the game.
Copy the exported assets into the project:
```bat
robocopy "%REPO%\work\hc_godot\sprites" "%REPO%\godot\hc\sprites" /E
robocopy "%REPO%\work\hc_godot\sounds"  "%REPO%\godot\hc\sounds"  /E
for %F in (anims images levels sounds flags) do copy /Y "%REPO%\work\hc_godot\data\%F.json" "%REPO%\godot\hc\data\"
```
(In a `.bat` file write `%%F` instead of `%F`.)

Open `%REPO%\godot\project.godot` in Godot and press F5. To build scenes for more levels:
```bat
cd /d "%REPO%\godot"
python tools\make_scenes.py all
```
Existing scenes are kept (add `--force` to rebuild). Details: [`godot/README.md`](godot/README.md).

## Save files
The game keeps its state in `C:\Windows\syshcin1.ini` (or `C:\Users\<you>\AppData\Local\VirtualStore\Windows\` when not run as administrator).
Save slots are `savhc1.ini`, `savhc2.ini`, `savhc3.ini` in the same folder. Loading a slot copies it over `syshcin1.ini`.
Back these up before testing.

## Testing checklist
1. **Inventory:** open with Space in several levels (Downtown, Suburbs, Trailer Park, Klub Kix) — nothing moves or is drawn over the inventory, Space closes it, controls work afterwards.
2. **Uber quest:** take the quest at the UberBurger door in the mall → Liposuction appears in the inventory and in `[weapons] lipo=1`; it survives save/load; 50 hits on bums in Bum Villa finish the quest.
3. **Abduction:** with `[status] quests` = 3 → no abduction; 4–8 → abduction scene on entering Klub Kix; 20 (after the good ending) → no abduction.
4. **Window:** 800×600 window, can be moved, Alt+Enter toggles fullscreen, minimize/restore keeps controls.

Please report issues with the check number, a screenshot and the relevant lines of `syshcin1.ini`.

## Credits
- Reverse engineering, testing and project lead: [kuvgen](https://github.com/kuvgen)
- Tools, patcher and documentation were developed with the help of
  [Claude](https://claude.ai) (Anthropic), an AI assistant.
- Hateful Chris 2: Never Say Buy belongs to its original authors.

## Legal
This is an unofficial, non-commercial fan project and is not affiliated with the authors or publishers of Hateful Chris 2.
It contains only original code and documentation written for this project (MIT license, see `LICENSE`).
All game content, names and trademarks belong to their respective owners.
