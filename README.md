# GitMaze

> **A NetHack-style Roguelike where dungeon maps live in Git.**  
> Anyone can modify, fix, or expand the dungeon through Git Pull Requests and Issues!

---

## Highlights

- **Git-Native Dungeon**: Every level is an ASCII `.map` file with YAML frontmatter in `levels/`.
- **Community & Provenance**: The in-game HUD displays the level's Git author, commit SHA, and description.
- **Classic NetHack Mechanics**:
  - Turn-based movement and D&D combat (attack rolls vs AC, weapon dice, critical hits).
  - Shadowcasting **Field-of-View (FOV)** with dungeon memory (explored fog-of-war).
  - Hunger system (Satiated, Normal, Hungry, Weak, Fainting).
  - Inventory management with weapons, armors, potions, scrolls, food, and gold.
  - Multi-level dungeon exploration via stairs (`>` / `<`).
- **Automated Map CI & Validator**:
  - Includes `validate_maps.py` with BFS pathfinding to check for unreachable rooms, trapped stairs, or broken bounds.
  - GitHub Actions workflow (`.github/workflows/validate_maps.yml`) automatically tests all PRs.

---

## Quickstart

### Prerequisites
- Python 3.10+
- Dependencies: `pip install -r requirements.txt` (only `pyyaml` and `colorama`)

### Play with GUI Frontend (Graphical Window)
```bash
python run_gui.py
```
Or via `--gui`:
```bash
python run_game.py --gui
```

### Play in Terminal (Classic NetHack ASCII)
```bash
python run_game.py
```
Or specify a particular starting level:
```bash
python run_game.py --level level_02
```

### Controls (NetHack Style)

| Key | Action |
|:---|:---|
| **Arrow Keys** or **h, j, k, l** | Move / Attack (Left, Down, Up, Right) |
| **y, u, b, n** or **Numpad (1-9)** | Diagonal 8-way movement & combat |
| **`,`** or **`g`** | Pick up item on ground |
| **`i`** | Open Inventory |
| **`w`** / **`W`** | Wield weapon / wear armor |
| **`q`** | Quaff potion |
| **`r`** | Read magic scroll |
| **`e`** | Eat food |
| **`d`** | Drop item |
| **`>`** | Descend stairs |
| **`<`** | Ascend stairs |
| **`.`** or **`s`** | Wait 1 turn |
| **`M`** | Inspect Git map info (author, commit SHA) |
| **`?`** | Help screen |
| **`Q`** | Quit game |

---

## Modifying & Creating Maps via Git

See [CONTRIBUTING_MAPS.md](CONTRIBUTING_MAPS.md) for full instructions.

### 1. Validate all maps locally:
```bash
python validate_maps.py
```

### 2. Run the test suite:
```bash
python -m unittest discover tests
```

### 3. Open a Pull Request:
When your PR is submitted, GitHub Actions will automatically validate that your map is traversable and meets all quality requirements!
