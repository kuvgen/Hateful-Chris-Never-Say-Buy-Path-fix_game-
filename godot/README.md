# Godot remake prototype (work in progress)

A Godot 4.4+ prototype of the Downtown level, rebuilt from the original game's data.
**No game assets are included** - you generate them from your own copy of the game.

## Setup
1. Export the game data (from the `tools` folder):
   ```
   python hc_run_all.py "D:\Games\Hateful Chris\HCNSB.exe" work
   ```
2. Copy from `work\hc_godot` into `godot\hc\`:
   - the folders `sprites` and `sounds`;
   - from `data`: `anims.json`, `images.json`, `levels.json`, `sounds.json`, `flags.json`
     (keep the `slice.json` that is already here).
3. Open `godot/project.godot` in Godot and press F5.

Controls: arrows - move, Up - jump / enter a door, Z - knife, R - restart.

## What is where
- `levels/004_Downtown.tscn` - the level scene: backgrounds, decor, floor line (`Markers/Floor`),
  Chris start, enemy spawn points, door zones. Everything can be moved in the editor.
- `hc/data/slice.json` - tuning: knife, enemy aggression, speeds, spawns, loot.
- `scripts/hcdata.gd` - conversion constants (Clickteam speed -> pixels).
- `tools/make_scenes.py` - builds scenes for other levels: `python tools/make_scenes.py 11 12` or `all`
  (existing scenes are not overwritten; use `--force`).

NPCs are neutral like in the original: they get angry only after you hit them.
