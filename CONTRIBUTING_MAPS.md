# Contributing Maps to GitMaze

In **GitMaze**, the dungeon layout is entirely version-controlled in this Git repository! Anyone can:
- **Suggest a map change / design a new room** via a **Pull Request (PR)**.
- **Report an impossible room, trap, or bad layout** via a **GitHub Issue**.
- Have their GitHub username and commit SHA immortalized directly inside the game HUD!

---

## 1. Visual Map Editor (Recommended)

You don't need to manually type ASCII grids by hand! You can use the built-in **GitMaze Map Editor**:

```bash
# Launch a new map editor
python run_editor.py

# Or edit an existing level directly
python run_editor.py levels/level_01.map
```

### Features of the Editor:
- **Pencil & Room Tool**: Drag to draw hollow or filled rooms and corridors.
- **Palette**: One-click selection of walls (`#`), floors (`.`), doors (`+`/`/`), player start (`@`), stairs (`>` / `<`), ladders (`}` / `{`), monsters (`d, k, g, o, z, D`), and items (`$, !, ?, ), [, %`).
- **Resize Floor**: Quick presets (`80x21 NetHack`, `60x20 Standard`, `40x15 Compact`, `100x30 Large`) and interactive zoom (`🔍 +` / `🔍 -`).
- **Live Validator**: Built-in `✓ Validate Map` button checks connectivity and reachability in real-time.
- **▶ Test Play Map**: Instantly opens a test game window to playtest your newly drawn dungeon before submitting.
- **YAML Frontmatter Editor**: Modify title, depth, author handle, and description in the sidebar.

---

## 2. Map File Format

Maps are stored as plain text files in the `levels/` directory with a `.map` extension (e.g., `levels/level_01.map`).

Every map consists of:
1. **YAML Frontmatter** (delimited by `---`) with metadata.
2. **ASCII Grid** depicting walls, floors, doors, stairs, monsters, and items.

### Example Template

```text
---
id: level_04
name: "The Forgotten Library"
depth: 4
author: "your_github_username"
description: "A ruined library full of cursed scrolls and lurking kobolds."
next_level: level_05
prev_level: level_03
---
###############################################################################
#                                                                             #
#   #################                   ###################################   #
#   #<..............#                   #..............................>..#   #
#   #.......?.......#...................#.............k...................#   #
#   #.......!.......#                   #......$..................$.......#   #
#   ########+########                   #################+#################   #
#           .                                            .                    #
#           ..............................................                    #
#                                                                             #
###############################################################################
```

---

## 3. Legend of Dungeon Glyphs

| Glyph | Description | Walkable? | Notes |
|:-----:|:------------|:---------:|:------|
| `@` | **Player Start** | Yes | Required if no `<` (stairs up) is present |
| `#` / `-` / `\|` | **Wall** | No | Blocks vision and movement |
| `.` | **Floor / Corridor** | Yes | Walkable, allows light to pass |
| `+` | **Closed Door** | Yes (bump to open) | Blocks vision until opened |
| `/` | **Open Door** | Yes | Transparent |
| `>` | **Stairs Down** | Yes | Descends to `next_level` or configured target |
| `<` | **Stairs Up** | Yes | Ascends to `prev_level` or configured target |
| `}` | **Ladder Down** | Yes | NetHack-style ladder descending to branch/sub-level |
| `{` | **Ladder Up** | Yes | Ladder ascending to parent level |
| ` ` | **Empty Rock / Void**| No | Out of bounds |
| `$` | **Gold** | Yes | Automatically picked up |
| `!` | **Potion** | Yes | Healing, speed, etc. |
| `?` | **Scroll** | Yes | Teleportation, magic mapping |
| `)` or `/`| **Weapon** | Yes | Dagger, short sword, long sword |
| `[` | **Armor** | Yes | Leather armor, chain mail, plate |
| `%` | **Food** | Yes | Food ration, apple, bread |
| `d` | **Jackal** | Yes (attack) | Fast, light melee |
| `k` | **Kobold** | Yes (attack) | Moderate melee |
| `g` | **Goblin** | Yes (attack) | Drops weapons |
| `o` | **Orc** | Yes (attack) | Tough brute |
| `z` | **Zombie** | Yes (attack) | High HP |
| `D` | **Dragon** | Yes (attack) | Boss tier |

---

## 4. Multiple Ladders & Dungeon Branching

Floors can contain **multiple stairs and ladders** leading to separate dungeon branches or secret chambers.
To configure destinations, define an `exits` table in your YAML frontmatter:

```yaml
---
id: level_01
name: "The Catacombs Entrance"
depth: 1
author: "octocat"
next_level: level_02
prev_level: null
exits:
  - pos: [70, 3]
    target_level: level_02
    label: "A grand stone staircase leading deeper into the Catacombs"
  - pos: [60, 14]
    target_level: goblin_mines_01
    target_pos: [6, 3]
    label: "An iron ladder descending into the dark Goblin Mines"
---
```

- When standing on a stair (`>`) or ladder (`}`), the in-game log identifies it by its label.
- Pressing `>` or `<` transitions directly to that exit's `target_level`.
- If `target_pos` is provided, the player lands on that coordinate; otherwise the player lands on the matching reverse stair/ladder.

---

## 5. Map Rules & Quality Checklist

Before submitting a Pull Request, your map must pass the automated validator:
1. **Connectivity**: All stairs (`>`, `<`, `}`, `{`), player spawn (`@`), and items/monsters must be reachable (no orphan rooms sealed off without doors).
2. **Bounds**: Width between 10 and 120; Height between 5 and 60.
3. **Surrounding Walls**: Enclose rooms with walls (`#`) so the player cannot fall into the void.
4. **Metadata**:
   - `id`: Unique alphanumeric ID (e.g. `level_04`).
   - `depth`: Positive integer.
   - `author`: Your GitHub handle (e.g. `@octocat`).

---

## 6. How to Test Your Map Locally

1. Create or edit your map in `levels/your_level.map`.
2. Run the validator CLI:
   ```bash
   python validate_maps.py
   ```
3. Test play your map directly in the game:
   ```bash
   python run_game.py --level your_level
   ```
4. Run the automated test suite:
   ```bash
   python -m unittest discover tests
   ```

---

## 7. Submitting Your PR

1. Fork this repository and create a branch:
   ```bash
   git checkout -b map/add-level-04
   ```
2. Commit your map:
   ```bash
   git add levels/level_04.map
   git commit -m "Add Level 04: The Forgotten Library"
   ```
3. Push to your fork and submit a Pull Request.
4. GitHub Actions CI will automatically run `validate_maps.py` to confirm your map passes all reachability and syntax tests!
