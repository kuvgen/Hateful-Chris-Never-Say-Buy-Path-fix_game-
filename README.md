# Hateful Chris 2: Never Say Buy — unofficial fix patch

An unofficial fan patcher for **Hateful Chris 2: Never Say Buy** (Clickteam engine, `HCNSB.exe`).

> **This repository contains no game files.** You need your own copy of the game.
> The patcher reads your original `HCNSB.exe` and writes a new patched file next to it —
> the original is never modified.

## What it fixes

| Flag | Fix |
|---|---|
| `inventory` | The game continues to run while the inventory screen is open: enemies, NPCs, visual effects, and level objects are rendered on top of it. Now, however, when the inventory is opened on modern systems, it displays correctly, and all those other objects are hidden; they reappear once the inventory is closed. |
| `hud` | (with `inventory`) also hides the top HUD panel while the inventory is open. |
| `fix-story` | **"Uber"- quest:** the Liposuction tool is never given in the original, so the quest cannot be finished. It is now given when you take the quest. **Trixie abduction:** the story only continues if you have completed exactly 4–5 quests when entering Klub Kix; with 6+ it never triggers. Now 4–8. |
| `windowed` | Starts in an 800×600 window with a title bar instead of fullscreen. **Alt+Enter** toggles fullscreen. |
| `-knife-bonus N` | Adds N to the starting knife's damage (it deals 1 in the original). |

Debug/advanced flags: `--no-pause` (hide objects only, don't pause), `--hide-name NAME` (also hide an object by name, repeatable), `--dry-run` (report only, don't write).

## Requirements
- Windows, your own copy of the game.
- [Python 3.8+](https://www.python.org/downloads/) (tick “Add Python to PATH” when installing).

## Usage
1. Download this repository (**Code → Download ZIP**) and unpack it.
2. Open a command prompt in the `tools` folder and run (use your own paths):
   ```
   python hc_patch.py "D:\Games\Hateful Chris\HCNSB.exe" "D:\Games\Hateful Chris\HCNSB_patched.exe" --inventory --hud --fix-story --windowed --knife-bonus 5
   ```
3. Check the output. Expected lines:
   - `Liposuction added in 2 events` / `abduction condition fixed in 1` (printed in Russian: `Liposuction добавлена в 2 событий … исправлено в 1`);
   - `Окно: флаги заголовка 0xAC9A -> 0xB498, размер 800x600`.
4. Start the game with `HCNSB_patched.exe`. It must stay in the game folder (next to `inventory.ccn` and `Cncs232.dll`).

Always patch the **original** `HCNSB.exe`, not an already patched one. Any combination of flags works.

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

## For researchers: extraction tools
`tools/` also contains the scripts used to reverse-engineer the game (container format, image/sound banks, event logic dump, level data):
```
python hc_run_all.py "D:\Games\Hateful Chris\HCNSB.exe" work
```
They write everything to the `work` folder on your machine. **Do not upload the extracted files** — they are the game's copyrighted content.
Findings about the game (quests, weapons, enemies, loot, shops, save format, level map) are documented in [`docs/`](docs).
Script comments and docs are mostly in Russian.

## Godot remake (work in progress)
[`godot/`](godot) contains a Godot 4.4+ prototype of the Downtown level that loads the data exported from your own copy of the game. See [`godot/README.md`](godot/README.md).

## Credits
- Reverse engineering, testing and project lead: [kuvgen](https://github.com/kuvgen)
- Tools, patcher and documentation were developed with the help of
  [Claude](https://claude.ai) (Anthropic), an AI assistant.
- Hateful Chris 2: Never Say Buy belongs to its original authors.

## Legal
This is an unofficial, non-commercial fan project and is not affiliated with the authors or publishers of Hateful Chris 2.
It contains only original code and documentation written for this project (MIT license, see `LICENSE`).
All game content, names and trademarks belong to their respective owners.
