"""Interactive Map Editor for GitMaze."""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Dict, List, Optional, Tuple, Set
import yaml

from .validator import MapValidator, ValidationError
from .map_loader import MapLoader, MapData, Tile


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
}

PALETTE = [
    # Category, Char, Name, Color
    ("Terrain", "#", "Wall (#)", "#4182c4"),
    ("Terrain", ".", "Floor (.)", "#3b4252"),
    ("Terrain", "+", "Closed Door (+)", "#e5c07b"),
    ("Terrain", "/", "Open Door (/)", "#e5c07b"),
    ("Terrain", " ", "Void / Rock ( )", "#161b22"),
    ("Spawns", "@", "Player Start (@)", "#ffffff"),
    ("Spawns", ">", "Stairs Down (>)", "#61afef"),
    ("Spawns", "<", "Stairs Up (<)", "#61afef"),
    ("Items", "$", "Gold ($)", "#e5c07b"),
    ("Items", "!", "Potion (!)", "#c678dd"),
    ("Items", "?", "Scroll (?)", "#56b6c2"),
    ("Items", ")", "Weapon () )", "#abb2bf"),
    ("Items", "[", "Armor ([)", "#98c379"),
    ("Items", "%", "Food (%)", "#98c379"),
    ("Monsters", "d", "Jackal (d)", "#d19a66"),
    ("Monsters", "k", "Kobold (k)", "#98c379"),
    ("Monsters", "g", "Goblin (g)", "#98c379"),
    ("Monsters", "o", "Orc (o)", "#e5c07b"),
    ("Monsters", "z", "Zombie (z)", "#56b6c2"),
    ("Monsters", "D", "Dragon (D)", "#e06c75"),
]

CHAR_COLORS = {char: col for _, char, _, col in PALETTE}


class MapEditor:
    def __init__(self, root: tk.Tk, initial_file: Optional[str] = None):
        self.root = root
        self.root.title("GitMaze Map Editor")
        self.root.geometry("1200x760")
        self.root.minsize(950, 650)
        self.root.configure(bg=THEME["bg"])

        self.font_family = "Consolas" if os.name == "nt" else "Monospace"
        self.current_file = initial_file

        # Map Dimensions & Grid
        self.width = 79
        self.height = 20
        self.cell_size = 20
        self.grid: List[List[str]] = [[" " for _ in range(self.width)] for _ in range(self.height)]

        # Editor State
        self.current_tool = "pencil"  # 'pencil', 'room', 'fill', 'eraser'
        self.current_brush = "#"
        self.drag_start: Optional[Tuple[int, int]] = None
        self.hover_pos: Optional[Tuple[int, int]] = None

        # Metadata
        self.meta_id = tk.StringVar(value="new_level")
        self.meta_name = tk.StringVar(value="New Chamber")
        self.meta_depth = tk.IntVar(value=1)
        self.meta_author = tk.StringVar(value="contributor")
        self.meta_desc = tk.StringVar(value="A custom chamber created with GitMaze Editor.")
        self.meta_next = tk.StringVar(value="")
        self.meta_prev = tk.StringVar(value="")

        self._init_styles()
        self._build_ui()
        self._bind_events()

        if initial_file and os.path.exists(initial_file):
            self.load_file(initial_file)
        else:
            self.create_default_room()

        self.redraw()

    def _init_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=THEME["panel_bg"], foreground=THEME["text_main"])
        style.configure("TFrame", background=THEME["panel_bg"])
        style.configure("TLabel", background=THEME["panel_bg"], foreground=THEME["text_main"], font=(self.font_family, 9))
        style.configure("Header.TLabel", font=(self.font_family, 10, "bold"), foreground=THEME["accent_blue"])
        style.configure("Tool.TButton", font=(self.font_family, 9), padding=(4, 2))

    def _build_ui(self):
        # 1. Top Menubar / Toolbar
        top_bar = ttk.Frame(self.root, padding=6)
        top_bar.pack(fill=tk.X, side=tk.TOP)

        ttk.Label(top_bar, text=" 🗺 GitMaze Editor ", font=(self.font_family, 13, "bold"), foreground=THEME["accent_blue"]).pack(side=tk.LEFT)

        btn_new = ttk.Button(top_bar, text="New", style="Tool.TButton", command=self.action_new)
        btn_new.pack(side=tk.LEFT, padx=3)

        btn_open = ttk.Button(top_bar, text="Open...", style="Tool.TButton", command=self.action_open)
        btn_open.pack(side=tk.LEFT, padx=3)

        btn_save = ttk.Button(top_bar, text="Save", style="Tool.TButton", command=self.action_save)
        btn_save.pack(side=tk.LEFT, padx=3)

        btn_saveas = ttk.Button(top_bar, text="Save As...", style="Tool.TButton", command=self.action_save_as)
        btn_saveas.pack(side=tk.LEFT, padx=3)

        btn_resize_top = ttk.Button(top_bar, text="Resize Floor...", style="Tool.TButton", command=self.action_resize)
        btn_resize_top.pack(side=tk.LEFT, padx=3)

        # Zoom Controls
        ttk.Separator(top_bar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        btn_zoom_out = ttk.Button(top_bar, text="🔍 -", width=3, style="Tool.TButton", command=self.zoom_out)
        btn_zoom_out.pack(side=tk.LEFT, padx=1)
        self.lbl_zoom = ttk.Label(top_bar, text="100%", width=5, font=(self.font_family, 8))
        self.lbl_zoom.pack(side=tk.LEFT, padx=2)
        btn_zoom_in = ttk.Button(top_bar, text="🔍 +", width=3, style="Tool.TButton", command=self.zoom_in)
        btn_zoom_in.pack(side=tk.LEFT, padx=1)

        # Right side actions: Validate & Test Play
        btn_play = ttk.Button(top_bar, text="▶ Test Play Map", style="Tool.TButton", command=self.action_test_play)
        btn_play.pack(side=tk.RIGHT, padx=4)

        btn_val = ttk.Button(top_bar, text="✓ Validate Map", style="Tool.TButton", command=self.action_validate)
        btn_val.pack(side=tk.RIGHT, padx=4)

        self.lbl_status = ttk.Label(top_bar, text="Ready", font=(self.font_family, 9), foreground=THEME["accent_yellow"])
        self.lbl_status.pack(side=tk.RIGHT, padx=10)

        # Main workspace: Left tools + Center Canvas + Right Metadata
        workspace = tk.Frame(self.root, bg=THEME["bg"])
        workspace.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)

        # 2. Left Tool & Palette Sidebar
        left_panel = ttk.Frame(workspace, width=210, padding=6)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 6))
        left_panel.pack_propagate(False)

        # Tool selector
        ttk.Label(left_panel, text="TOOLS", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))
        tool_frame = ttk.Frame(left_panel)
        tool_frame.pack(fill=tk.X, pady=(0, 8))

        self.btn_pencil = tk.Button(tool_frame, text="Pencil", bg="#238636", fg="#fff", command=lambda: self.set_tool("pencil"))
        self.btn_pencil.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        self.btn_room = tk.Button(tool_frame, text="Room", bg="#21262d", fg="#fff", command=lambda: self.set_tool("room"))
        self.btn_room.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        self.btn_fill = tk.Button(tool_frame, text="Fill", bg="#21262d", fg="#fff", command=lambda: self.set_tool("fill"))
        self.btn_fill.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        self.btn_eraser = tk.Button(tool_frame, text="Eraser", bg="#21262d", fg="#fff", command=lambda: self.set_tool("eraser"))
        self.btn_eraser.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

        # Brush Palette
        ttk.Label(left_panel, text="PALETTE / GLYPHS", style="Header.TLabel").pack(anchor=tk.W, pady=(6, 4))

        palette_canvas = tk.Canvas(left_panel, bg=THEME["panel_bg"], bd=0, highlightthickness=0)
        palette_scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=palette_canvas.yview)
        scrollable_frame = ttk.Frame(palette_canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: palette_canvas.configure(scrollregion=palette_canvas.bbox("all"))
        )
        palette_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        palette_canvas.configure(yscrollcommand=palette_scrollbar.set)

        palette_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        palette_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.brush_buttons = {}
        last_cat = ""
        for cat, char, name, color in PALETTE:
            if cat != last_cat:
                ttk.Label(scrollable_frame, text=cat.upper(), font=(self.font_family, 8, "bold"), foreground=THEME["accent_blue"]).pack(anchor=tk.W, pady=(4, 1))
                last_cat = cat

            btn = tk.Button(
                scrollable_frame,
                text=f" {char}  {name} ",
                bg="#1c2128" if char != self.current_brush else "#388bfd",
                fg=color,
                font=(self.font_family, 9, "bold"),
                anchor="w",
                relief="flat",
                bd=1,
                padx=4,
                pady=2,
                command=lambda c=char: self.set_brush(c),
            )
            btn.pack(fill=tk.X, pady=1)
            self.brush_buttons[char] = btn

        # 3. Center Canvas with Scrollbars
        canvas_container = tk.Frame(workspace, bg=THEME["canvas_bg"], relief=tk.SOLID, bd=1)
        canvas_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.h_scroll = tk.Scrollbar(canvas_container, orient=tk.HORIZONTAL)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.v_scroll = tk.Scrollbar(canvas_container, orient=tk.VERTICAL)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas = tk.Canvas(
            canvas_container,
            bg=THEME["canvas_bg"],
            highlightthickness=0,
            cursor="crosshair",
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set,
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        # 4. Right Metadata & Diagnostics Panel
        right_panel = ttk.Frame(workspace, width=280, padding=8)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))
        right_panel.pack_propagate(False)

        ttk.Label(right_panel, text="LEVEL METADATA", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 6))

        def add_entry(label_text, var):
            ttk.Label(right_panel, text=label_text).pack(anchor=tk.W)
            ent = ttk.Entry(right_panel, textvariable=var)
            ent.pack(fill=tk.X, pady=(0, 4))
            return ent

        add_entry("Level ID (e.g. level_04):", self.meta_id)
        add_entry("Display Name:", self.meta_name)
        add_entry("Dungeon Depth:", self.meta_depth)
        add_entry("Author GitHub Handle:", self.meta_author)
        add_entry("Next Level ID (via >):", self.meta_next)
        add_entry("Prev Level ID (via <):", self.meta_prev)

        ttk.Label(right_panel, text="Description:").pack(anchor=tk.W)
        self.txt_desc = tk.Text(right_panel, height=3, bg="#161b22", fg=THEME["text_main"], font=(self.font_family, 9), relief=tk.SOLID, bd=1)
        self.txt_desc.insert("1.0", self.meta_desc.get())
        self.txt_desc.pack(fill=tk.X, pady=(0, 6))

        # Size settings
        size_frame = ttk.Frame(right_panel)
        size_frame.pack(fill=tk.X, pady=4)
        ttk.Label(size_frame, text="Dimensions:").pack(side=tk.LEFT)
        self.lbl_dims = ttk.Label(size_frame, text=f"{self.width} x {self.height}", foreground=THEME["accent_yellow"])
        self.lbl_dims.pack(side=tk.LEFT, padx=6)
        btn_resize = ttk.Button(size_frame, text="Resize...", style="Tool.TButton", command=self.action_resize)
        btn_resize.pack(side=tk.RIGHT)

        ttk.Separator(right_panel, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)

        # Diagnostics / Validation Box
        ttk.Label(right_panel, text="MAP VALIDATION", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 4))
        self.diag_box = tk.Text(right_panel, height=8, bg="#161b22", fg=THEME["text_main"], font=(self.font_family, 8), state=tk.DISABLED, wrap=tk.WORD)
        self.diag_box.pack(fill=tk.BOTH, expand=True)

        # Bottom info bar
        self.info_lbl = ttk.Label(self.root, text="Hover: (x: 0, y: 0)  |  Tool: Pencil  |  Brush: #", font=(self.font_family, 9), background=THEME["panel_bg"])
        self.info_lbl.pack(fill=tk.X, side=tk.BOTTOM, padx=6, pady=2)

    def _bind_events(self):
        self.canvas.bind("<Button-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<Motion>", self.on_canvas_motion)
        self.canvas.bind("<MouseWheel>", self.on_mousewheel)  # Windows / macOS
        self.canvas.bind("<Button-4>", self.on_mousewheel)    # Linux scroll up
        self.canvas.bind("<Button-5>", self.on_mousewheel)    # Linux scroll down
        self.root.bind("<Control-s>", lambda e: self.action_save())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-equal>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())

    def set_tool(self, tool_name: str):
        self.current_tool = tool_name
        self.btn_pencil.config(bg="#238636" if tool_name == "pencil" else "#21262d")
        self.btn_room.config(bg="#238636" if tool_name == "room" else "#21262d")
        self.btn_fill.config(bg="#238636" if tool_name == "fill" else "#21262d")
        self.btn_eraser.config(bg="#238636" if tool_name == "eraser" else "#21262d")
        self.update_info_bar()

    def set_brush(self, char: str):
        self.current_brush = char
        for c, btn in self.brush_buttons.items():
            btn.config(bg="#388bfd" if c == char else "#1c2128")
        if self.current_tool == "eraser":
            self.set_tool("pencil")
        self.update_info_bar()

    def update_info_bar(self):
        hx = self.hover_pos[0] if self.hover_pos else 0
        hy = self.hover_pos[1] if self.hover_pos else 0
        ch = self.grid[hy][hx] if (0 <= hy < self.height and 0 <= hx < self.width) else " "
        self.info_lbl.config(
            text=f"Cursor: ({hx}, {hy}) '{ch}'  |  Tool: {self.current_tool.capitalize()}  |  Brush: '{self.current_brush}'"
        )

    def create_default_room(self):
        """Fill grid with border walls and a room with player start and stairs down."""
        self.grid = [[" " for _ in range(self.width)] for _ in range(self.height)]
        # Outer boundary
        for x in range(self.width):
            self.grid[0][x] = "#"
            self.grid[self.height - 1][x] = "#"
        for y in range(self.height):
            self.grid[y][0] = "#"
            self.grid[y][self.width - 1] = "#"

        # Initial Room
        rx, ry, rw, rh = 5, 4, 25, 10
        for y in range(ry, ry + rh):
            for x in range(rx, rx + rw):
                if y == ry or y == ry + rh - 1 or x == rx or x == rx + rw - 1:
                    self.grid[y][x] = "#"
                else:
                    self.grid[y][x] = "."

        # Door, player start, stairs down
        self.grid[ry + rh - 1][rx + rw // 2] = "+"
        self.grid[ry + 2][rx + 3] = "@"
        self.grid[ry + 2][rx + rw - 4] = ">"

    def get_canvas_cell(self, event) -> Tuple[int, int]:
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        x = int(cx // self.cell_size)
        y = int(cy // self.cell_size)
        return x, y

    def on_canvas_motion(self, event):
        x, y = self.get_canvas_cell(event)
        self.hover_pos = (x, y)
        self.update_info_bar()

    def on_canvas_press(self, event):
        x, y = self.get_canvas_cell(event)
        if not (0 <= x < self.width and 0 <= y < self.height):
            return

        self.drag_start = (x, y)
        if self.current_tool == "pencil":
            self.paint_cell(x, y, self.current_brush)
        elif self.current_tool == "eraser":
            self.paint_cell(x, y, " ")
        elif self.current_tool == "fill":
            self.flood_fill(x, y, self.current_brush)

    def on_canvas_drag(self, event):
        x, y = self.get_canvas_cell(event)
        if not (0 <= x < self.width and 0 <= y < self.height):
            return

        self.hover_pos = (x, y)
        self.update_info_bar()

        if self.current_tool == "pencil":
            self.paint_cell(x, y, self.current_brush)
        elif self.current_tool == "eraser":
            self.paint_cell(x, y, " ")
        elif self.current_tool == "room":
            self.redraw()
            # Draw preview rectangle
            if self.drag_start:
                sx, sy = self.drag_start
                x1, x2 = min(sx, x), max(sx, x)
                y1, y2 = min(sy, y), max(sy, y)
                cs = self.cell_size
                self.canvas.create_rectangle(
                    x1 * cs, y1 * cs, (x2 + 1) * cs, (y2 + 1) * cs,
                    outline="#58a6ff", width=2, dash=(4, 2)
                )

    def on_canvas_release(self, event):
        x, y = self.get_canvas_cell(event)
        if self.current_tool == "room" and self.drag_start:
            sx, sy = self.drag_start
            x1, x2 = max(0, min(sx, x)), min(self.width - 1, max(sx, x))
            y1, y2 = max(0, min(sy, y)), min(self.height - 1, max(sy, y))
            for cy in range(y1, y2 + 1):
                for cx in range(x1, x2 + 1):
                    if cy == y1 or cy == y2 or cx == x1 or cx == x2:
                        self.grid[cy][cx] = "#"
                    else:
                        self.grid[cy][cx] = "."
            self.redraw()
        self.drag_start = None

    def on_canvas_right_click(self, event):
        """Right click erases cell to space or floor."""
        x, y = self.get_canvas_cell(event)
        if 0 <= x < self.width and 0 <= y < self.height:
            # If was something else, clear to floor or void
            self.grid[y][x] = "." if self.grid[y][x] != "." else " "
            self.redraw()

    def paint_cell(self, x: int, y: int, char: str):
        # Unique constraints: only one '@' start per map
        if char == "@":
            for cy in range(self.height):
                for cx in range(self.width):
                    if self.grid[cy][cx] == "@":
                        self.grid[cy][cx] = "."

        self.grid[y][x] = char
        self.redraw()

    def flood_fill(self, start_x: int, start_y: int, new_char: str):
        target = self.grid[start_y][start_x]
        if target == new_char:
            return

        queue = [(start_x, start_y)]
        visited = set([(start_x, start_y)])

        while queue:
            cx, cy = queue.pop(0)
            self.grid[cy][cx] = new_char

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if (nx, ny) not in visited and self.grid[ny][nx] == target:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
        self.redraw()

    def redraw(self):
        self.canvas.delete("all")
        cs = self.cell_size
        total_w = self.width * cs
        total_h = self.height * cs
        self.canvas.config(scrollregion=(0, 0, total_w, total_h))

        f_size = max(9, cs - 6)
        font = (self.font_family, f_size, "bold")

        # Draw grid cells
        for y in range(self.height):
            for x in range(self.width):
                px = x * cs
                py = y * cs
                char = self.grid[y][x]

                if char in ("#", "-", "|"):
                    self.canvas.create_rectangle(px, py, px + cs, py + cs, fill="#1c2536", outline="#26344d")
                    self.canvas.create_text(px + cs // 2, py + cs // 2, text=char, fill="#4182c4", font=font)
                elif char == ".":
                    self.canvas.create_rectangle(px, py, px + cs, py + cs, fill="#131924", outline="#1c2536")
                    self.canvas.create_text(px + cs // 2, py + cs // 2, text=".", fill="#48536b", font=font)
                elif char == " ":
                    self.canvas.create_rectangle(px, py, px + cs, py + cs, fill="#0a0c0e", outline="#11151c")
                else:
                    # Entity or special tile
                    self.canvas.create_rectangle(px, py, px + cs, py + cs, fill="#131924", outline="#1c2536")
                    col = CHAR_COLORS.get(char, "#ffffff")
                    if char == "@":
                        self.canvas.create_oval(px + 2, py + 2, px + cs - 2, py + cs - 2, fill="#238636", outline="")
                    self.canvas.create_text(px + cs // 2, py + cs // 2, text=char, fill=col, font=font)

    def serialize_map(self) -> str:
        frontmatter = {
            "id": self.meta_id.get().strip() or "custom_level",
            "name": self.meta_name.get().strip() or "Unnamed Chamber",
            "depth": self.meta_depth.get(),
            "author": self.meta_author.get().strip() or "contributor",
            "description": self.txt_desc.get("1.0", tk.END).strip(),
            "next_level": self.meta_next.get().strip() or None,
            "prev_level": self.meta_prev.get().strip() or None,
        }

        yaml_str = yaml.dump(frontmatter, sort_keys=False).strip()
        lines = ["".join(row).rstrip() for row in self.grid]
        grid_str = "\n".join(lines)

        return f"---\n{yaml_str}\n---\n{grid_str}\n"

    def action_validate(self) -> bool:
        content = self.serialize_map()
        issues = MapValidator.validate_string(content, file_path=self.current_file or "memory.map")

        self.diag_box.config(state=tk.NORMAL)
        self.diag_box.delete("1.0", tk.END)

        errors = [i for i in issues if i.severity == "ERROR"]
        warnings = [i for i in issues if i.severity == "WARNING"]

        if not issues:
            self.diag_box.insert(tk.END, "✓ Map is VALID and ready for Git PR!\n\nAll reachability, spawns, and geometry checks passed.")
            self.lbl_status.config(text="Map: Valid (0 errors)", foreground=THEME["accent_green"])
            self.diag_box.config(state=tk.DISABLED)
            return True
        else:
            self.diag_box.insert(tk.END, f"Found {len(errors)} error(s), {len(warnings)} warning(s):\n\n")
            for err in errors:
                self.diag_box.insert(tk.END, f"✗ {err.message}\n")
            for w in warnings:
                self.diag_box.insert(tk.END, f"! {w.message}\n")

            self.lbl_status.config(text=f"Map: Invalid ({len(errors)} errors)", foreground=THEME["accent_red"])
            self.diag_box.config(state=tk.DISABLED)
            return len(errors) == 0

    def action_new(self):
        if messagebox.askyesno("New Map", "Create a new blank map? Any unsaved changes will be lost."):
            self.current_file = None
            self.meta_id.set("new_level")
            self.meta_name.set("New Chamber")
            self.meta_depth.set(1)
            self.create_default_room()
            self.redraw()
            self.lbl_status.config(text="New Map Created", foreground=THEME["accent_yellow"])

    def action_open(self):
        init_dir = os.path.abspath("levels") if os.path.isdir("levels") else os.path.abspath(".")
        fpath = filedialog.askopenfilename(
            initialdir=init_dir,
            title="Open GitMaze Map",
            filetypes=[
                ("GitMaze Map Files", ("*.map", "*.txt")),
                ("GitMaze Maps (*.map)", "*.map"),
                ("Text Maps (*.txt)", "*.txt"),
                ("All Files", "*"),
            ]
        )
        if fpath:
            self.load_file(fpath)

    def load_file(self, file_path: str):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            map_data = MapLoader.load_from_string(content, file_path=file_path)

            self.current_file = file_path
            self.meta_id.set(map_data.id)
            self.meta_name.set(map_data.name)
            self.meta_depth.set(map_data.depth)
            self.meta_author.set(map_data.author)
            self.meta_next.set(map_data.next_level or "")
            self.meta_prev.set(map_data.prev_level or "")
            self.txt_desc.delete("1.0", tk.END)
            self.txt_desc.insert("1.0", map_data.description)

            # Rebuild grid
            self.width = map_data.width
            self.height = map_data.height
            self.grid = [[" " for _ in range(self.width)] for _ in range(self.height)]

            for y in range(self.height):
                for x in range(self.width):
                    self.grid[y][x] = map_data.grid[y][x].char

            # Overlay player start
            px, py = map_data.player_start
            if 0 <= px < self.width and 0 <= py < self.height:
                self.grid[py][px] = "@"

            # Overlay stairs
            if map_data.stairs_down:
                sx, sy = map_data.stairs_down
                self.grid[sy][sx] = ">"
            if map_data.stairs_up:
                ux, uy = map_data.stairs_up
                self.grid[uy][ux] = "<"

            # Overlay items
            for (ix, iy), item_list in map_data.items.items():
                if item_list and 0 <= ix < self.width and 0 <= iy < self.height:
                    self.grid[iy][ix] = item_list[-1].char

            # Overlay monsters
            for m in map_data.monsters:
                if 0 <= m.x < self.width and 0 <= m.y < self.height:
                    self.grid[m.y][m.x] = m.char

            self.lbl_dims.config(text=f"{self.width} x {self.height}")
            self.redraw()
            self.action_validate()
            self.lbl_status.config(text=f"Loaded {os.path.basename(file_path)}", foreground=THEME["accent_green"])
        except Exception as e:
            messagebox.showerror("Failed to load map", str(e))

    def action_save(self):
        if not self.current_file:
            self.action_save_as()
        else:
            self.save_to_file(self.current_file)

    def action_save_as(self):
        init_dir = os.path.abspath("levels") if os.path.isdir("levels") else os.path.abspath(".")
        default_name = f"{self.meta_id.get().strip() or 'custom_level'}.map"
        fpath = filedialog.asksaveasfilename(
            initialdir=init_dir,
            initialfile=default_name,
            title="Save GitMaze Map",
            defaultextension=".map",
            filetypes=[
                ("GitMaze Maps (*.map)", "*.map"),
                ("Text Maps (*.txt)", "*.txt"),
                ("All Files", "*"),
            ]
        )
        if fpath:
            self.current_file = fpath
            self.save_to_file(fpath)

    def save_to_file(self, fpath: str):
        try:
            content = self.serialize_map()
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            self.action_validate()
            self.lbl_status.config(text=f"Saved {os.path.basename(fpath)}", foreground=THEME["accent_green"])
            messagebox.showinfo("Saved", f"Map saved successfully to:\n{fpath}")
        except Exception as e:
            messagebox.showerror("Error Saving", str(e))

    def zoom_in(self):
        if self.cell_size < 40:
            self.cell_size += 2
            self.lbl_zoom.config(text=f"{int(self.cell_size / 20 * 100)}%")
            self.redraw()

    def zoom_out(self):
        if self.cell_size > 10:
            self.cell_size -= 2
            self.lbl_zoom.config(text=f"{int(self.cell_size / 20 * 100)}%")
            self.redraw()

    def on_mousewheel(self, event):
        # Ctrl + Wheel zooms
        if event.state & 0x0004 or event.state & 4:  # Control key pressed
            if event.delta > 0 or event.num == 4:
                self.zoom_in()
            else:
                self.zoom_out()

    def action_resize(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Resize Floor & Grid")
        dialog.geometry("340x260")
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Floor Dimensions (Tiles)", font=(self.font_family, 10, "bold"), foreground=THEME["accent_blue"]).pack(anchor=tk.W, padx=12, pady=(10, 6))

        inputs_frame = ttk.Frame(dialog)
        inputs_frame.pack(fill=tk.X, padx=12, pady=4)

        ttk.Label(inputs_frame, text="Width (10 - 120):").grid(row=0, column=0, sticky=tk.W, pady=4)
        w_ent = ttk.Entry(inputs_frame, width=8)
        w_ent.insert(0, str(self.width))
        w_ent.grid(row=0, column=1, padx=8, pady=4)

        ttk.Label(inputs_frame, text="Height (5 - 60):").grid(row=1, column=0, sticky=tk.W, pady=4)
        h_ent = ttk.Entry(inputs_frame, width=8)
        h_ent.insert(0, str(self.height))
        h_ent.grid(row=1, column=1, padx=8, pady=4)

        # Quick Presets
        ttk.Label(dialog, text="Quick Presets:").pack(anchor=tk.W, padx=12, pady=(8, 2))
        preset_frame = ttk.Frame(dialog)
        preset_frame.pack(fill=tk.X, padx=12, pady=2)

        def set_preset(w, h):
            w_ent.delete(0, tk.END)
            w_ent.insert(0, str(w))
            h_ent.delete(0, tk.END)
            h_ent.insert(0, str(h))

        ttk.Button(preset_frame, text="80x21 (NetHack)", style="Tool.TButton", command=lambda: set_preset(80, 21)).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="60x20 (Standard)", style="Tool.TButton", command=lambda: set_preset(60, 20)).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="40x15 (Compact)", style="Tool.TButton", command=lambda: set_preset(40, 15)).pack(side=tk.LEFT, padx=2)
        ttk.Button(preset_frame, text="100x30 (Large)", style="Tool.TButton", command=lambda: set_preset(100, 30)).pack(side=tk.LEFT, padx=2)

        def apply_resize():
            try:
                nw = int(w_ent.get())
                nh = int(h_ent.get())
                if not (10 <= nw <= 120 and 5 <= nh <= 60):
                    raise ValueError("Dimensions out of allowed bounds (10-120 x 5-60)")

                # Reallocate grid preserving existing content
                new_grid = [[" " for _ in range(nw)] for _ in range(nh)]
                for y in range(min(self.height, nh)):
                    for x in range(min(self.width, nw)):
                        new_grid[y][x] = self.grid[y][x]

                self.width = nw
                self.height = nh
                self.grid = new_grid
                self.lbl_dims.config(text=f"{self.width} x {self.height}")
                self.redraw()
                self.action_validate()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Invalid Size", str(e))

        btn_box = ttk.Frame(dialog)
        btn_box.pack(fill=tk.X, padx=12, pady=14)
        ttk.Button(btn_box, text="Apply Size", command=apply_resize).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_box, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=4)

    def action_test_play(self):
        """Save to temporary file and launch test play."""
        if not self.action_validate():
            if not messagebox.askyesno("Validation Warning", "The map has validation errors or warnings. Test play anyway?"):
                return

        # Save to current file or temporary map
        test_file = self.current_file or os.path.join("levels", f"_test_{self.meta_id.get()}.map")
        try:
            content = self.serialize_map()
            with open(test_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save test map: {e}")
            return

        level_id = self.meta_id.get().strip() or "test"
        # Launch GUI game window on this level
        game_win = tk.Toplevel(self.root)
        from .gui import GitMazeGUI
        GitMazeGUI(game_win, levels_dir=os.path.dirname(test_file), start_level=level_id)


def start_editor(file_path: Optional[str] = None):
    root = tk.Tk()
    app = MapEditor(root, initial_file=file_path)
    root.mainloop()


if __name__ == "__main__":
    initial = sys.argv[1] if len(sys.argv) > 1 else None
    start_editor(initial)
