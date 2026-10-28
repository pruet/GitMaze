"""Tkinter-based GUI Frontend for GitMaze."""
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Optional, Tuple

from .engine import GameEngine
from .items import Weapon, Armor, Potion, Scroll, Food, Gold
from .entities import Monster


# Color Palette for GUI
THEME = {
    "bg": "#121417",
    "canvas_bg": "#0a0c0e",
    "panel_bg": "#1a1d24",
    "panel_border": "#2a2e39",
    "text_main": "#e1e4ea",
    "text_dim": "#6e7681",
    "accent_blue": "#58a6ff",
    "accent_green": "#3fb950",
    "accent_yellow": "#d29922",
    "accent_red": "#f85149",
    "accent_purple": "#bc8cff",
    "accent_cyan": "#39c5cf",
    "tile_wall": "#2d5f8b",
    "tile_floor": "#30363d",
    "tile_door": "#d29922",
    "tile_stairs": "#58a6ff",
}

GLYPH_COLORS = {
    "@": "#ffffff",        # Player
    "#": "#4182c4",        # Wall
    "-": "#4182c4",        # Wall
    "|": "#4182c4",        # Wall
    ".": "#3b4252",        # Floor
    "+": "#e5c07b",        # Closed Door
    "/": "#e5c07b",        # Open Door
    ">": "#61afef",        # Stairs Down
    "<": "#61afef",        # Stairs Up
    "$": "#e5c07b",        # Gold
    "!": "#c678dd",        # Potion
    "?": "#56b6c2",        # Scroll
    ")": "#abb2bf",        # Weapon
    "[": "#98c379",        # Armor
    "%": "#98c379",        # Food
    "d": "#d19a66",        # Jackal
    "k": "#98c379",        # Kobold
    "g": "#98c379",        # Goblin
    "o": "#e5c07b",        # Orc
    "z": "#56b6c2",        # Zombie
    "D": "#e06c75",        # Dragon
}


class GitMazeGUI:
    def __init__(self, root: tk.Tk, levels_dir: str = "levels", start_level: str = "level_01"):
        self.root = root
        self.root.title("GitMaze - The Git-Driven Roguelike")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)
        self.root.configure(bg=THEME["bg"])

        self.levels_dir = levels_dir
        self.engine = GameEngine(levels_dir=levels_dir, start_level_id=start_level)

        self.cell_size = 20  # Pixel size for each tile
        self.font_family = "Consolas" if os.name == "nt" else "Monospace"

        self._setup_styles()
        self._build_layout()
        self._bind_events()

        self.refresh_all()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=THEME["panel_bg"], foreground=THEME["text_main"])
        style.configure("TFrame", background=THEME["panel_bg"])
        style.configure("TLabel", background=THEME["panel_bg"], foreground=THEME["text_main"], font=(self.font_family, 10))
        style.configure("Header.TLabel", font=(self.font_family, 12, "bold"), foreground=THEME["accent_blue"])
        style.configure("Stats.TLabel", font=(self.font_family, 10, "bold"))
        style.configure("Badge.TLabel", font=(self.font_family, 9), foreground=THEME["accent_yellow"])
        
        style.configure(
            "Game.TButton",
            background="#21262d",
            foreground=THEME["text_main"],
            borderwidth=1,
            relief="flat",
            font=(self.font_family, 9),
            padding=(6, 4),
        )
        style.map("Game.TButton", background=[("active", "#30363d")])

    def _build_layout(self):
        # Top toolbar
        toolbar = ttk.Frame(self.root, padding=6)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        title_lbl = ttk.Label(toolbar, text=" ⚔ GitMaze ", font=(self.font_family, 14, "bold"), foreground=THEME["accent_blue"])
        title_lbl.pack(side=tk.LEFT, padx=5)

        self.git_badge = ttk.Label(toolbar, text="", style="Badge.TLabel")
        self.git_badge.pack(side=tk.LEFT, padx=10)

        # Action Buttons on Top
        btn_help = ttk.Button(toolbar, text="Help (?)", style="Game.TButton", command=self.show_help)
        btn_help.pack(side=tk.RIGHT, padx=3)

        btn_git = ttk.Button(toolbar, text="Git Info (M)", style="Game.TButton", command=self.show_git_info)
        btn_git.pack(side=tk.RIGHT, padx=3)

        btn_restart = ttk.Button(toolbar, text="Restart", style="Game.TButton", command=self.restart_game)
        btn_restart.pack(side=tk.RIGHT, padx=3)

        # Zoom controls
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.RIGHT, fill=tk.Y, padx=6)
        btn_zoom_in = ttk.Button(toolbar, text="🔍 +", width=3, style="Game.TButton", command=self.zoom_in)
        btn_zoom_in.pack(side=tk.RIGHT, padx=1)
        btn_zoom_out = ttk.Button(toolbar, text="🔍 -", width=3, style="Game.TButton", command=self.zoom_out)
        btn_zoom_out.pack(side=tk.RIGHT, padx=1)

        # Main horizontal split: Dungeon Canvas (Left) + Sidebar (Right)
        main_frame = tk.Frame(self.root, bg=THEME["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # Dungeon & Log Container (Left)
        left_container = tk.Frame(main_frame, bg=THEME["bg"])
        left_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Canvas Frame with scrollbars
        canvas_frame = tk.Frame(left_container, bg=THEME["canvas_bg"], relief=tk.SOLID, bd=1)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg=THEME["canvas_bg"],
            highlightthickness=0,
            cursor="crosshair",
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Narrative / Combat Log (Bottom of Left Frame)
        log_frame = tk.Frame(left_container, bg=THEME["panel_bg"], height=110, relief=tk.SOLID, bd=1)
        log_frame.pack(fill=tk.X, pady=(6, 0))
        log_frame.pack_propagate(False)

        self.log_text = tk.Text(
            log_frame,
            bg=THEME["panel_bg"],
            fg=THEME["text_main"],
            font=(self.font_family, 10),
            wrap=tk.WORD,
            bd=0,
            padx=8,
            pady=4,
            state=tk.DISABLED,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Sidebar (Right)
        sidebar = ttk.Frame(main_frame, width=320, padding=8)
        sidebar.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        sidebar.pack_propagate(False)

        # 1. Hero Stats
        ttk.Label(sidebar, text="HERO STATUS", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))

        self.stats_label = ttk.Label(sidebar, text="", style="Stats.TLabel")
        self.stats_label.pack(anchor=tk.W)

        # HP Bar
        hp_frame = ttk.Frame(sidebar)
        hp_frame.pack(fill=tk.X, pady=4)
        ttk.Label(hp_frame, text="HP:", width=4).pack(side=tk.LEFT)
        self.hp_bar = ttk.Progressbar(hp_frame, orient=tk.HORIZONTAL, mode="determinate")
        self.hp_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.hp_text = ttk.Label(hp_frame, text="25/25", width=7)
        self.hp_text.pack(side=tk.RIGHT)

        # Hunger status
        self.hunger_label = ttk.Label(sidebar, text="Hunger: Satiated")
        self.hunger_label.pack(anchor=tk.W, pady=(0, 6))

        # Divider
        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        # 2. Equipment Section
        ttk.Label(sidebar, text="EQUIPMENT", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))
        self.equip_label = ttk.Label(sidebar, text="Weapon: Bare Hands\nArmor: None")
        self.equip_label.pack(anchor=tk.W, pady=(0, 6))

        # Divider
        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        # 3. Inventory Section
        ttk.Label(sidebar, text="INVENTORY", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))

        inv_container = tk.Frame(sidebar, bg=THEME["panel_bg"])
        inv_container.pack(fill=tk.BOTH, expand=True, pady=4)

        self.inv_listbox = tk.Listbox(
            inv_container,
            bg="#161b22",
            fg=THEME["text_main"],
            selectbackground=THEME["accent_blue"],
            selectforeground="#ffffff",
            font=(self.font_family, 10),
            bd=0,
            highlightthickness=1,
            highlightcolor=THEME["panel_border"],
            highlightbackground=THEME["panel_border"],
        )
        self.inv_listbox.pack(fill=tk.BOTH, expand=True)

        inv_btn_frame = ttk.Frame(sidebar)
        inv_btn_frame.pack(fill=tk.X, pady=4)

        btn_use = ttk.Button(inv_btn_frame, text="Use / Equip", style="Game.TButton", command=self.use_selected_item)
        btn_use.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        btn_drop = ttk.Button(inv_btn_frame, text="Drop", style="Game.TButton", command=self.drop_selected_item)
        btn_drop.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(2, 0))

        # 4. Action Quick-Bar
        ttk.Separator(sidebar, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        ttk.Label(sidebar, text="ACTIONS", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))

        act_frame = ttk.Frame(sidebar)
        act_frame.pack(fill=tk.X)

        btn_pickup = ttk.Button(act_frame, text="Pick Up (,)", style="Game.TButton", command=self.action_pickup)
        btn_pickup.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        btn_wait = ttk.Button(act_frame, text="Wait (s)", style="Game.TButton", command=self.action_wait)
        btn_wait.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        stair_frame = ttk.Frame(sidebar)
        stair_frame.pack(fill=tk.X, pady=3)

        btn_down = ttk.Button(stair_frame, text="Down Stairs (>)", style="Game.TButton", command=self.action_down)
        btn_down.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        btn_up = ttk.Button(stair_frame, text="Up Stairs (<)", style="Game.TButton", command=self.action_up)
        btn_up.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

    def zoom_in(self):
        if self.cell_size < 40:
            self.cell_size += 2
            self.render_dungeon()

    def zoom_out(self):
        if self.cell_size > 10:
            self.cell_size -= 2
            self.render_dungeon()

    def _bind_events(self):
        # Keyboard bindings
        self.root.bind("<KeyPress>", self.handle_keypress)
        # Mouse click on canvas for movement / targeting
        self.canvas.bind("<Button-1>", self.handle_canvas_click)
        # Mouse wheel zoom with Ctrl
        self.canvas.bind("<MouseWheel>", lambda e: self.zoom_in() if e.delta > 0 else self.zoom_out())
        self.canvas.bind("<Button-4>", lambda e: self.zoom_in())
        self.canvas.bind("<Button-5>", lambda e: self.zoom_out())
        # Resize event
        self.canvas.bind("<Configure>", lambda e: self.render_dungeon())

    def handle_keypress(self, event):
        key = event.keysym.lower()
        char = event.char

        # Direction mappings
        directions = {
            "up": (0, -1),
            "k": (0, -1),
            "down": (0, 1),
            "j": (0, 1),
            "left": (-1, 0),
            "h": (-1, 0),
            "right": (1, 0),
            "l": (1, 0),
            "y": (-1, -1),
            "u": (1, -1),
            "b": (-1, 1),
            "n": (1, 1),
            # Keypad
            "kp_8": (0, -1),
            "kp_2": (0, 1),
            "kp_4": (-1, 0),
            "kp_6": (1, 0),
            "kp_7": (-1, -1),
            "kp_9": (1, -1),
            "kp_1": (-1, 1),
            "kp_3": (1, 1),
        }

        if key in directions:
            dx, dy = directions[key]
            self.engine.handle_move_or_attack(dx, dy)
        elif char in (",", "g"):
            self.engine.pickup_item()
        elif char in (".", "s", "5"):
            self.engine.wait_turn()
        elif char == ">":
            self.engine.descend_stairs()
        elif char == "<":
            self.engine.ascend_stairs()
        elif char in ("i", "w", "e", "q", "r"):
            self.use_selected_item()
        elif char == "d":
            self.drop_selected_item()
        elif char == "?":
            self.show_help()
        elif char in ("m", "M"):
            self.show_git_info()

        self.refresh_all()

    def handle_canvas_click(self, event):
        """Move towards or attack the clicked tile if adjacent."""
        lvl = self.engine.current_level
        if not lvl:
            return

        cx = event.x // self.cell_size
        cy = event.y // self.cell_size

        px = self.engine.player.x
        py = self.engine.player.y

        dx = cx - px
        dy = cy - py

        # Only allow 1-tile adjacent move/attack via direct click
        if -1 <= dx <= 1 and -1 <= dy <= 1 and not (dx == 0 and dy == 0):
            self.engine.handle_move_or_attack(dx, dy)
            self.refresh_all()

    def action_pickup(self):
        self.engine.pickup_item()
        self.refresh_all()

    def action_wait(self):
        self.engine.wait_turn()
        self.refresh_all()

    def action_down(self):
        self.engine.descend_stairs()
        self.refresh_all()

    def action_up(self):
        self.engine.ascend_stairs()
        self.refresh_all()

    def use_selected_item(self):
        sel = self.inv_listbox.curselection()
        if sel:
            idx = sel[0]
            self.engine.use_item(idx)
            self.refresh_all()

    def drop_selected_item(self):
        sel = self.inv_listbox.curselection()
        if sel:
            idx = sel[0]
            self.engine.drop_item(idx)
            self.refresh_all()

    def restart_game(self):
        if messagebox.askyesno("Restart Game", "Are you sure you want to start a new game?"):
            self.engine = GameEngine(levels_dir=self.levels_dir, start_level_id="level_01")
            self.refresh_all()

    def show_help(self):
        help_msg = (
            "GitMaze Controls:\n\n"
            "Movement & Combat:\n"
            "  - Arrow Keys or Vi Keys (h, j, k, l): Move / Attack\n"
            "  - Diagonal: y, u, b, n\n"
            "  - Mouse: Click on any adjacent tile to move or attack\n\n"
            "Actions:\n"
            "  - , or g : Pick up item\n"
            "  - s or . : Wait / Search\n"
            "  - > : Descend stairs\n"
            "  - < : Ascend stairs\n"
            "  - Select Item + Click Use/Drop in Inventory\n"
            "  - M : View Git map author and commit details"
        )
        messagebox.showinfo("GitMaze - Help", help_msg)

    def show_git_info(self):
        lvl = self.engine.current_level
        info_msg = (
            f"Level ID: {lvl.id}\n"
            f"Level Name: {lvl.name}\n"
            f"Depth: {lvl.depth}\n"
            f"Author: @{lvl.author}\n"
            f"Git SHA: {lvl.git_sha}\n"
            f"Last Committer: {lvl.git_last_author}\n"
            f"Commit Message: {lvl.git_commit_msg}\n\n"
            f"Description:\n{lvl.description or 'None'}\n\n"
            "Anyone can edit maps and submit Pull Requests to GitHub!"
        )
        messagebox.showinfo("Git Level Information", info_msg)

    def refresh_all(self):
        self.render_dungeon()
        self.update_sidebar()
        self.update_log()
        self.check_game_over()

    def render_dungeon(self):
        self.canvas.delete("all")
        eng = self.engine
        lvl = eng.current_level
        if not lvl:
            return

        visible = eng.visible_tiles
        explored = eng.explored_tiles.get(eng.current_level_id, set())

        active_monsters = {(m.x, m.y): m for m in lvl.monsters if m.alive}
        items_map = lvl.items

        cs = self.cell_size
        f_size = max(10, cs - 6)
        font = (self.font_family, f_size, "bold")

        for y in range(lvl.height):
            for x in range(lvl.width):
                pos = (x, y)
                px = x * cs
                py = y * cs

                if pos in visible:
                    # Visible tile: render background box + glyph
                    tile = lvl.grid[y][x]
                    
                    # Floor vs Wall background
                    if tile.char in ("#", "-", "|"):
                        self.canvas.create_rectangle(px, py, px + cs, py + cs, fill="#1c2536", outline="")
                    elif tile.char == ".":
                        self.canvas.create_rectangle(px, py, px + cs, py + cs, fill="#131924", outline="")
                    
                    # Entities / Glyphs
                    if eng.player.x == x and eng.player.y == y:
                        # Draw player highlight circle
                        self.canvas.create_oval(px + 2, py + 2, px + cs - 2, py + cs - 2, fill="#238636", outline="")
                        self.canvas.create_text(px + cs // 2, py + cs // 2, text="@", fill="#ffffff", font=font)
                    elif pos in active_monsters:
                        m = active_monsters[pos]
                        col = GLYPH_COLORS.get(m.char, "#f85149")
                        self.canvas.create_text(px + cs // 2, py + cs // 2, text=m.char, fill=col, font=font)
                    elif pos in items_map and items_map[pos]:
                        top_item = items_map[pos][-1]
                        col = GLYPH_COLORS.get(top_item.char, "#e5c07b")
                        self.canvas.create_text(px + cs // 2, py + cs // 2, text=top_item.char, fill=col, font=font)
                    else:
                        col = GLYPH_COLORS.get(tile.char, "#8b949e")
                        if tile.char != " ":
                            self.canvas.create_text(px + cs // 2, py + cs // 2, text=tile.char, fill=col, font=font)

                elif pos in explored:
                    # Explored (dim / fog of war)
                    tile = lvl.grid[y][x]
                    if tile.char != " ":
                        self.canvas.create_text(px + cs // 2, py + cs // 2, text=tile.char, fill="#3b4252", font=font)
                else:
                    # Unexplored remains black canvas background
                    pass

    def update_sidebar(self):
        eng = self.engine
        p = eng.player
        lvl = eng.current_level
        if not lvl:
            return

        # Git badge
        self.git_badge.config(
            text=f"Level: {lvl.name} (Dlvl {lvl.depth}) | Author: @{lvl.author} | SHA: {lvl.git_sha[:7]}"
        )

        # Stats
        stats_text = (
            f"Gold: {p.gold}  |  Turn: {eng.turn}\n"
            f"Armor Class: {p.ac}  |  Level: {p.level} (Exp: {p.exp})\n"
            f"Str: {p.str_score}  |  Dex: {p.dex_score}"
        )
        self.stats_label.config(text=stats_text)

        # HP Bar
        hp_pct = max(0, min(100, (p.hp / p.max_hp) * 100))
        self.hp_bar["value"] = hp_pct
        self.hp_text.config(text=f"{p.hp}/{p.max_hp}")

        # Hunger
        self.hunger_label.config(text=f"Hunger: {p.hunger_status}")

        # Equipment
        weap = p.equipped_weapon.describe() if p.equipped_weapon else "Bare Hands"
        arm = p.equipped_armor.describe() if p.equipped_armor else "None"
        self.equip_label.config(text=f"Weapon: {weap}\nArmor: {arm}")

        # Inventory
        cur_selection = self.inv_listbox.curselection()
        self.inv_listbox.delete(0, tk.END)
        for item in p.inventory:
            suffix = ""
            if item == p.equipped_weapon:
                suffix = " [Wielded]"
            elif item == p.equipped_armor:
                suffix = " [Worn]"
            self.inv_listbox.insert(tk.END, f" {item.char}  {item.name}{suffix}")

        if cur_selection and cur_selection[0] < self.inv_listbox.size():
            self.inv_listbox.select_set(cur_selection[0])

    def update_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        recent = self.engine.messages[-6:]
        for msg in recent:
            self.log_text.insert(tk.END, f"• {msg}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def check_game_over(self):
        if self.engine.won:
            messagebox.showinfo("Ascended!", "CONGRATULATIONS!\nYou conquered GitMaze and ascended!")
        elif self.engine.game_over:
            messagebox.showinfo("Game Over", "You have perished in GitMaze!\nPropose a map tweak via a Git PR!")


def start_gui(levels_dir: str = "levels", start_level: str = "level_01"):
    root = tk.Tk()
    app = GitMazeGUI(root, levels_dir=levels_dir, start_level=start_level)
    root.mainloop()


if __name__ == "__main__":
    start_gui()
