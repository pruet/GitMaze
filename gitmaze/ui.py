"""Terminal UI renderer and input handler for GitMaze (NetHack-style)."""
import os
import sys
from typing import Dict, List, Optional, Tuple
from .engine import GameEngine
from .items import Weapon, Armor


# ANSI color codes
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "dark_gray": "\033[90m",
    "bright_red": "\033[91m",
    "bright_green": "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue": "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
    "bright_white": "\033[97m",
    "brown": "\033[33m",
}


def colorize(text: str, color_name: str, bold: bool = False) -> str:
    col = COLORS.get(color_name, COLORS["white"])
    bld = COLORS["bold"] if bold else ""
    return f"{bld}{col}{text}{COLORS['reset']}"


def get_key() -> str:
    """Read a single keypress cross-platform without waiting for Enter."""
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            # Special keys (arrows, function keys)
            ch2 = msvcrt.getwch()
            key_map = {
                "H": "UP",
                "P": "DOWN",
                "K": "LEFT",
                "M": "RIGHT",
                "y": "UP_LEFT",
                "u": "UP_RIGHT",
                "b": "DOWN_LEFT",
                "n": "DOWN_RIGHT",
            }
            return key_map.get(ch2, "")
        return ch
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                # Escape sequence
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A":
                        return "UP"
                    elif ch3 == "B":
                        return "DOWN"
                    elif ch3 == "D":
                        return "LEFT"
                    elif ch3 == "C":
                        return "RIGHT"
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


class TerminalUI:
    def __init__(self, engine: GameEngine):
        self.engine = engine
        self._init_terminal()

    def _init_terminal(self):
        # Enable ANSI colors on Windows cmd/powershell
        if os.name == "nt":
            os.system("color")

    def clear_screen(self):
        # Move cursor to home (0,0) and clear screen
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

    def render(self):
        eng = self.engine
        lvl = eng.current_level
        if not lvl:
            return

        lines: List[str] = []

        # 1. Message Log (NetHack top banner)
        recent_msgs = eng.messages[-3:] if eng.messages else ["Welcome to GitMaze!"]
        while len(recent_msgs) < 3:
            recent_msgs.insert(0, "")
        for m in recent_msgs:
            lines.append(colorize(m.ljust(80)[:80], "bright_white"))

        lines.append(colorize("-" * 80, "dark_gray"))

        # 2. Render Dungeon Map
        # Find camera viewport or render entire map
        visible = eng.visible_tiles
        explored = eng.explored_tiles.get(eng.current_level_id, set())

        # Build position lookup for monsters and items
        active_monsters = {(m.x, m.y): m for m in lvl.monsters if m.alive}
        items_map = lvl.items

        for y in range(lvl.height):
            row_str = []
            for x in range(lvl.width):
                pos = (x, y)
                if pos in visible:
                    # Player
                    if eng.player.x == x and eng.player.y == y:
                        row_str.append(colorize("@", "bright_white", bold=True))
                    # Monster
                    elif pos in active_monsters:
                        m = active_monsters[pos]
                        row_str.append(colorize(m.char, m.color, bold=True))
                    # Items
                    elif pos in items_map and items_map[pos]:
                        top_item = items_map[pos][-1]
                        row_str.append(colorize(top_item.char, top_item.color, bold=True))
                    # Dungeon tile
                    else:
                        tile = lvl.grid[y][x]
                        row_str.append(colorize(tile.char, tile.color))
                elif pos in explored:
                    # Explored but not currently in FOV (dim gray)
                    tile = lvl.grid[y][x]
                    char = tile.char if tile.char != " " else " "
                    row_str.append(colorize(char, "dark_gray"))
                else:
                    # Unexplored
                    row_str.append(" ")
            lines.append("".join(row_str))

        # 3. Status Line (NetHack bottom stats)
        lines.append(colorize("-" * 80, "dark_gray"))
        p = eng.player
        weapon_name = p.equipped_weapon.name if p.equipped_weapon else "bare hands"
        status_line1 = (
            f"Dlvl:{lvl.depth}  $: {p.gold:<4}  HP:{p.hp}({p.max_hp})  AC:{p.ac}  "
            f"Str:{p.str_score}  Dex:{p.dex_score}  Exp:{p.level}/{p.exp}  T:{eng.turn}  {p.hunger_status}"
        )
        status_line2 = (
            f"Level: {lvl.name} | Author: @{lvl.author} | SHA: {lvl.git_sha} | Wielding: {weapon_name}"
        )

        lines.append(colorize(status_line1, "bright_cyan", bold=True))
        lines.append(colorize(status_line2, "bright_yellow"))
        lines.append(colorize("Commands: [hjklyubn/arrows] Move/Atk  [,] Pick  [i] Inv  [e] Eat  [q] Quaff  [r] Read  [>] Down  [?] Help", "dark_gray"))

        # Output to terminal
        self.clear_screen()
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()

    def show_inventory_menu(self, prompt: str = "Select item to use/drop (or ESC/SPACE to cancel):") -> Optional[int]:
        self.clear_screen()
        p = self.engine.player
        print(colorize("=== INVENTORY ===", "bright_cyan", bold=True))
        if not p.inventory:
            print("Your inventory is empty.")
            print("\nPress any key to return...")
            get_key()
            return None

        for idx, item in enumerate(p.inventory):
            letter = chr(ord('a') + idx)
            equip_status = ""
            if item == p.equipped_weapon:
                equip_status = colorize(" (weapon in hand)", "bright_green")
            elif item == p.equipped_armor:
                equip_status = colorize(" (being worn)", "bright_green")

            print(f" {letter}) [{item.char}] {item.name}{equip_status}")

        print("\n" + colorize(prompt, "bright_yellow"))
        ch = get_key()
        if ch in ("\x1b", " ", "q", "\r", "\n"):
            return None

        idx = ord(ch.lower()) - ord('a')
        if 0 <= idx < len(p.inventory):
            return idx
        return None

    def show_help_menu(self):
        self.clear_screen()
        help_text = """
================================ GitMaze Help ================================
GitMaze is a NetHack-style roguelike where dungeon maps live directly inside
a Git repository. Anyone can create levels, suggest fixes, or submit new maps!

Movement & Combat:
  h, j, k, l / Arrow Keys : Move / Attack orthogonally (Left, Down, Up, Right)
  y, u, b, n              : Move / Attack diagonally
  Numpad 1-9              : 8-directional movement & combat
  Bump into monsters      : Attack with wielded weapon
  Bump into doors (+)     : Open door

Actions:
  ,  or g   : Pick up item from ground
  i         : Open inventory
  w         : Wield weapon / wear armor (or toggle equip)
  e         : Eat food (replenishes hunger)
  q         : Quaff potion
  r         : Read magic scroll
  d         : Drop item
  >         : Descend stairs to next dungeon level
  <         : Ascend stairs to previous dungeon level
  s  or .   : Wait / search 1 turn
  M         : Show Git provenance info (author, commit SHA, PR guide)
  ?         : Show this help menu
  Q         : Quit game

Dungeon Glyphs:
  @ : You (The Adventurer)    # : Wall           . : Floor
  + : Closed Door             / : Open Door      > : Stairs Down
  < : Stairs Up               $ : Gold           ! : Potion
  ? : Scroll                  ) : Weapon         [ : Armor
  % : Food                    d,k,g,o,z,D : Monsters

Press any key to return to game...
"""
        print(colorize(help_text, "bright_cyan"))
        get_key()

    def show_git_info_menu(self):
        self.clear_screen()
        lvl = self.engine.current_level
        info_text = f"""
=========================== Git Level Information ============================
Current Level ID  : {lvl.id}
Level Name        : {lvl.name}
Depth             : {lvl.depth}
Original Author   : @{lvl.author}
Git Commit SHA    : {lvl.git_sha}
Last Committer    : {lvl.git_last_author}
Commit Message    : {lvl.git_commit_msg}
File Path         : {lvl.file_path}

Description:
  {lvl.description or "No description provided."}

How to contribute or modify this map:
  1. Edit the file in your clone: {lvl.file_path or f"levels/{lvl.id}.map"}
  2. Run the validator: `python validate_maps.py`
  3. Commit and open a Pull Request!
  4. Your GitHub username and commit SHA will be displayed right here!

Press any key to return to game...
"""
        print(colorize(info_text, "bright_yellow"))
        get_key()
